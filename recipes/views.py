"""
Recipes Views (통합 개선 버전)

주요 개선사항:
1. Spoonacular + 한식 레시피 완전 통합
2. 추천 알고리즘 미세 조정
3. 소비기한 임박 처리 개선
4. 동점자 처리 로직
5. 에러 처리 강화
"""

"""
Recipes Views (통합 개선 버전)
"""
from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Prefetch

# DRF
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

# 모델 및 시리얼라이저
from recipes.models import Recipe, RecipeIngredient, FavoriteRecipe
from recipes.serializers import (
    RecipeListSerializer, RecipeDetailSerializer,
    FavoriteRecipeSerializer
)
from ingredients.models import UserIngredient

# [핵심] utils.py에서 함수 가져오기 (에러 방지 및 로직 분리)
# 이 부분이 없으면 '우유' 에러나 'API 402' 에러가 발생합니다.
from .utils import (
    search_recipes_from_db, 
    search_recipes_from_spoonacular, 
    calculate_final_recommendations
)

# ==================== ViewSets ==================== #

class RecipeViewSet(viewsets.ReadOnlyModelViewSet):
    """레시피 조회 ViewSet"""
    queryset = Recipe.objects.filter(is_active=True)
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RecipeDetailSerializer
        return RecipeListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 필터링
        source = self.request.query_params.get('source')
        if source:
            queryset = queryset.filter(source=source)
        
        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        return queryset.prefetch_related('recipe_ingredients__ingredient')
    
    # ViewSet 내 액션으로도 추천 기능을 제공하고 싶다면 아래처럼 연결
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def recommendations(self, request):
        return get_recipe_recommendations(request)


class FavoriteRecipeViewSet(viewsets.ModelViewSet):
    """찜한 레시피 관리 ViewSet"""
    serializer_class = FavoriteRecipeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return FavoriteRecipe.objects.filter(
            user=self.request.user
        ).select_related('recipe').order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """레시피 찜하기"""
        recipe_id = request.data.get('recipe_id')
        
        if not recipe_id:
            return Response({'error': 'recipe_id가 필요합니다'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            recipe = Recipe.objects.get(recipe_id=recipe_id)
        except Recipe.DoesNotExist:
            return Response({'error': '존재하지 않는 레시피입니다'}, status=status.HTTP_404_NOT_FOUND)
        
        # 중복 확인
        existing = FavoriteRecipe.objects.filter(user=request.user, recipe=recipe).first()
        if existing:
            return Response({'message': '이미 찜한 레시피입니다'}, status=status.HTTP_200_OK)
        
        favorite = FavoriteRecipe.objects.create(user=request.user, recipe=recipe)
        serializer = self.get_serializer(favorite)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['delete'])
    def remove(self, request):
        """찜 취소"""
        recipe_id = request.data.get('recipe_id')
        if not recipe_id:
            return Response({'error': 'recipe_id가 필요합니다'}, status=status.HTTP_400_BAD_REQUEST)
        
        deleted_count = FavoriteRecipe.objects.filter(
            user=request.user,
            recipe_id=recipe_id
        ).delete()[0]
        
        if deleted_count > 0:
            return Response({'message': '찜이 취소되었습니다'})
        else:
            return Response({'error': '찜한 레시피가 아닙니다'}, status=status.HTTP_404_NOT_FOUND)


# ==================== API Views (Function Based) ==================== #

@api_view(['POST'])
@permission_classes([AllowAny])
def get_recipe_recommendations(request):
    """
    통합 레시피 추천 API (utils.py 연동 완료)
    """
    # 1. 로그인 여부에 따라 user 처리
    if request.user.is_authenticated:
        user = request.user
        user_ingredients = UserIngredient.objects.filter(
            user=user,
            is_consumed=False
        ).select_related('ingredient', 'ingredient__category')
    else:
        user = None
        user_ingredients = UserIngredient.objects.none()

    # 2. 요청 파라미터 받기
    ingredient_ids = request.data.get('ingredient_ids', [])
    use_all = request.data.get('use_all', False)
    max_results = request.data.get('max_results', 20)
    keyword = request.data.get('keyword', '').strip() 
    
    # API 사용 여부 (기본값 True)
    include_spoonacular = False
    #include_spoonacular = request.data.get('include_spoonacular', True)

    # 3. 식재료 필터링
    if use_all:
        selected_ingredients = user_ingredients
    elif ingredient_ids:
        # 안전한 ID 필터링 (문자열 제외)
        valid_ids = []
        for i in ingredient_ids:
            try:
                valid_ids.append(int(i))
            except (ValueError, TypeError):
                continue
        
        selected_ingredients = user_ingredients.filter(
            user_ingredient_id__in=valid_ids
        )
    else:
        selected_ingredients = user_ingredients
    
    # 검색어도 없고 재료도 없으면 빈 결과 반환
    if not selected_ingredients.exists() and not keyword:
        return Response({
            'message': '선택된 식재료 또는 검색어가 없습니다',
            'categories': {},
            'total_count': 0,
            'recipes': [] 
        })
    
    selected_ingredient_ids = list(selected_ingredients.values_list('ingredient_id', flat=True))
    user_ingredients_dict = {ui.ingredient_id: ui for ui in selected_ingredients}
    
    # ==========================================
    # 4. DB 검색 (utils.py 함수 사용)
    # ==========================================
    db_recipes_by_ing = []
    if selected_ingredient_ids:
        # utils.py 함수가 '우유' 같은 문자열 에러를 방지합니다.
        db_recipes_by_ing = list(search_recipes_from_db(selected_ingredient_ids, user))

    # 키워드 검색
    db_recipes_by_keyword = []
    if keyword:
        db_recipes_by_keyword = list(Recipe.objects.filter(title__icontains=keyword))

    # 결과 합치기
    combined_db = db_recipes_by_keyword + db_recipes_by_ing

    # ==========================================
    # 5. Spoonacular 검색 (utils.py 함수 사용)
    # ==========================================
    spoon_recipes = []
    if include_spoonacular and selected_ingredients.exists():
        # utils.py 함수가 402 에러를 방지하고 빈 리스트를 반환합니다.
        spoon_recipes = search_recipes_from_spoonacular(
            selected_ingredients,
            max_results=10
        )
    
    # 6. 통합 및 중복 제거
    all_recipes = list(combined_db) + spoon_recipes
    unique_recipes = {}
    
    for recipe in all_recipes:
        if recipe.external_id not in unique_recipes:
            unique_recipes[recipe.external_id] = recipe
    
    # 7. 사용자 스킬 레벨
    user_skill_level = 'INTERMEDIATE'
    if user:
        try:
            if hasattr(user, 'profile'):
                user_skill_level = user.profile.cooking_level
        except:
            pass
    
    # 8. 최종 결과 계산 (utils.py 함수 사용)
    final_list = list(unique_recipes.values())
    
    result = calculate_final_recommendations(
        recipes=final_list[:max_results],
        user=user,
        user_ingredients_dict=user_ingredients_dict,
        user_skill_level=user_skill_level
    )
    
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_recipe_detail(request, recipe_id):
    """레시피 상세 조회 API"""
    try:
        recipe = Recipe.objects.prefetch_related(
            'recipe_ingredients__ingredient'
        ).get(recipe_id=recipe_id)
    except Recipe.DoesNotExist:
        return Response({'error': '존재하지 않는 레시피입니다'}, status=status.HTTP_404_NOT_FOUND)
    
    user_ingredient_ids = []
    if request.user.is_authenticated:
        user_ingredient_ids = list(
            UserIngredient.objects.filter(
                user=request.user,
                is_consumed=False
            ).values_list('ingredient_id', flat=True)
        )
    
    serializer = RecipeDetailSerializer(recipe, context={
        'user_ingredient_ids': user_ingredient_ids
    })
    
    return Response(serializer.data)


# ==================== Template Views (HTML 렌더링) ==================== #

def recipe_list_view(request):
    """레시피 목록 페이지"""
    return render(request, 'recipes/recipe_list.html')


def recipe_detail_view(request, recipe_id):
    """레시피 상세 페이지"""
    try:
        recipe = Recipe.objects.prefetch_related(
            'recipe_ingredients__ingredient'
        ).get(recipe_id=recipe_id)
    except Recipe.DoesNotExist:
        return render(request, 'recipes/recipe_not_found.html', status=404)
    
    user_ingredients = []
    if request.user.is_authenticated:
        user_ingredients = UserIngredient.objects.filter(
            user=request.user, 
            is_consumed=False
        ).select_related('ingredient')
        
    user_ingredient_ids = [ui.ingredient_id for ui in user_ingredients]
    user_ingredients_dict = {ui.ingredient_id: ui for ui in user_ingredients}
    
    recipe_ingredients = recipe.recipe_ingredients.all()
    for ri in recipe_ingredients:
        ri.is_owned = ri.ingredient_id in user_ingredient_ids
        if ri.is_owned:
            user_ing = user_ingredients_dict[ri.ingredient_id]
            ri.user_ingredient = user_ing
            ri.days_left = user_ing.days_until_expiry
        else:
            ri.user_ingredient = None
            ri.days_left = None
    
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = FavoriteRecipe.objects.filter(user=request.user, recipe=recipe).exists()
    
    context = {'recipe': recipe, 'recipe_ingredients': recipe_ingredients, 'is_favorited': is_favorited}
    return render(request, 'recipes/recipe_detail.html', context)


def cooking_mode_view(request, recipe_id):
    """조리 모드 페이지"""
    try:
        recipe = Recipe.objects.get(recipe_id=recipe_id)
    except Recipe.DoesNotExist:
        return render(request, 'recipes/recipe_not_found.html', status=404)
    
    context = {'recipe': recipe}
    return render(request, 'recipes/cooking_mode.html', context)


def cooking_complete_view(request, recipe_id):
    """조리 완료 페이지"""
    try:
        recipe = Recipe.objects.prefetch_related('recipe_ingredients__ingredient').get(recipe_id=recipe_id)
    except Recipe.DoesNotExist:
        return render(request, 'recipes/recipe_not_found.html', status=404)
    
    user_ingredients = []
    if request.user.is_authenticated:
        user_ingredients = UserIngredient.objects.filter(
            user=request.user,
            ingredient_id__in=recipe.recipe_ingredients.values_list('ingredient_id', flat=True),
            is_consumed=False
        ).select_related('ingredient')
    
    context = {'recipe': recipe, 'user_ingredients': user_ingredients}
    return render(request, 'recipes/cooking_complete.html', context)