"""
Recipes Views (통합 개선 버전)

주요 개선사항:
1. Spoonacular + 한식 레시피 완전 통합
2. 추천 알고리즘 미세 조정
3. 소비기한 임박 처리 개선
4. 동점자 처리 로직
5. 에러 처리 강화
"""

from datetime import date, timedelta
from django.shortcuts import render
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
from ingredients.utils.mapper import IngredientMapper


# ==================== ViewSets ==================== #

class RecipeViewSet(viewsets.ReadOnlyModelViewSet):
    """레시피 조회"""
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
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def recommendations(self, request):
        """
        통합 레시피 추천 API
        
        Request Body:
        {
            "ingredient_ids": [1, 2, 3],  // 선택한 식재료 (선택)
            "use_all": true,  // 모든 보유 식재료 사용 (선택)
            "include_spoonacular": true,  // Spoonacular 포함 여부
            "max_results": 20  // 최대 결과 개수
        }
        """
        return get_recipe_recommendations(request)


class FavoriteRecipeViewSet(viewsets.ModelViewSet):
    """찜한 레시피 관리"""
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
            return Response(
                {'error': 'recipe_id가 필요합니다'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            recipe = Recipe.objects.get(recipe_id=recipe_id)
        except Recipe.DoesNotExist:
            return Response(
                {'error': '존재하지 않는 레시피입니다'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 중복 확인
        existing = FavoriteRecipe.objects.filter(
            user=request.user,
            recipe=recipe
        ).first()
        
        if existing:
            return Response(
                {'message': '이미 찜한 레시피입니다'},
                status=status.HTTP_200_OK
            )
        
        # 생성
        favorite = FavoriteRecipe.objects.create(
            user=request.user,
            recipe=recipe
        )
        
        serializer = self.get_serializer(favorite)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['delete'])
    def remove(self, request):
        """찜 취소"""
        recipe_id = request.data.get('recipe_id')
        
        if not recipe_id:
            return Response(
                {'error': 'recipe_id가 필요합니다'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        deleted_count = FavoriteRecipe.objects.filter(
            user=request.user,
            recipe_id=recipe_id
        ).delete()[0]
        
        if deleted_count > 0:
            return Response({'message': '찜이 취소되었습니다'})
        else:
            return Response(
                {'error': '찜한 레시피가 아닙니다'},
                status=status.HTTP_404_NOT_FOUND
            )


# ==================== 헬퍼 함수 ==================== #

def search_recipes_from_db(user_ingredient_ids, user, exclude_allergies=True):
    """
    DB에서 레시피 검색 (한식 + 기존 저장된 레시피)
    
    Args:
        user_ingredient_ids: 사용자 보유 식재료 ID 리스트
        user: 사용자 객체
        exclude_allergies: 알러지/제한 식재료 제외 여부
    
    Returns:
        Recipe QuerySet
    """
    recipes = Recipe.objects.filter(is_active=True)
    
    # 하드 필터: 알러지/제한 식재료 제외
    if exclude_allergies and hasattr(user, 'profile'):
        profile = user.profile
        banned_ingredients = []
        
        if profile.allergies:
            banned_ingredients.extend(profile.allergies)
        
        if profile.banned_ingredients:
            banned_ingredients.extend(profile.banned_ingredients)
        
        if banned_ingredients:
            recipes = recipes.exclude(
                recipe_ingredients__ingredient_id__in=banned_ingredients
            )
    
    # 재료 매칭
    if user_ingredient_ids:
        recipes = recipes.filter(
            recipe_ingredients__ingredient_id__in=user_ingredient_ids
        ).annotate(
            matching_count=Count('recipe_ingredients', filter=Q(
                recipe_ingredients__ingredient_id__in=user_ingredient_ids
            ))
        ).order_by('-matching_count')
    
    return recipes.distinct().prefetch_related('recipe_ingredients__ingredient')[:50]


def search_recipes_from_spoonacular(user_ingredients, max_results=10):
    """
    Spoonacular API에서 레시피 검색
    
    Args:
        user_ingredients: UserIngredient QuerySet
        max_results: 최대 결과 개수
    
    Returns:
        Recipe 리스트
    """
    try:
        from recipes.services.spoonacular import SpoonacularService
        service = SpoonacularService()
    except (ValueError, ImportError) as e:
        print(f"Spoonacular 서비스 로드 실패: {e}")
        return []
    
    # 식재료 이름을 영어로 변환
    ingredient_names = []
    
    for ui in user_ingredients:
        # 1. name_en 사용
        if ui.ingredient.name_en:
            ingredient_names.append(ui.ingredient.name_en)
        else:
            # 2. IngredientMapper로 매핑 찾기
            ing_name = ui.ingredient.name_ko
            
            for eng, kor in IngredientMapper.BASE_MAPPINGS.items():
                if kor == ing_name:
                    ingredient_names.append(eng)
                    break
    
    if not ingredient_names:
        return []
    
    # API 호출
    try:
        search_results = service.search_recipes_by_ingredients(
            ingredients=ingredient_names[:5],  # 최대 5개
            number=max_results
        )
    except Exception as e:
        print(f"Spoonacular API 검색 실패: {e}")
        return []
    
    # 레시피 ID 추출
    recipe_ids = [r['id'] for r in search_results]
    
    # 각 레시피를 DB에 저장
    recipes = []
    for recipe_id in recipe_ids:
        try:
            recipe = service.save_recipe_to_db(recipe_id)
            if recipe:
                recipes.append(recipe)
        except Exception as e:
            print(f'레시피 {recipe_id} 저장 실패: {e}')
            continue
    
    return recipes


def calculate_final_recommendations(recipes, user, user_ingredients_dict, user_skill_level):
    """
    레시피 추천 점수 계산 및 정렬
    
    Args:
        recipes: Recipe 리스트/QuerySet
        user: 사용자 객체
        user_ingredients_dict: {ingredient_id: UserIngredient} 딕셔너리
        user_skill_level: 사용자 요리 실력 레벨
    
    Returns:
        {
            'categories': {
                'urgent_ready': {...},
                'ready': {...},
                'almost_ready': {...}
            },
            'total_count': int
        }
    """
    user_ingredient_ids = list(user_ingredients_dict.keys())
    
    # 점수 계산
    scored_recipes = []
    
    for recipe in recipes:
        score_data = recipe.calculate_recommendation_score(
            user=user,
            user_ingredient_ids=user_ingredient_ids,
            user_ingredients_dict=user_ingredients_dict,
            user_skill_level=user_skill_level
        )
        
        # 최소 점수 필터 (60점 이상)
        if score_data['total_score'] >= 60:
            scored_recipes.append({
                'recipe': recipe,
                'score_data': score_data
            })
    
    # 정렬: 총점 → 유통기한 점수 → 난이도
    scored_recipes.sort(
        key=lambda x: (
            x['score_data']['total_score'],
            x['score_data']['expiry_score'],
            -x['score_data']['difficulty_score']  # 난이도 낮은 순
        ),
        reverse=True
    )
    
    # 카테고리별로 분류
    categories = {
        'urgent_ready': {'label': '유통기한 임박 레시피', 'recipes': [], 'count': 0},
        'ready': {'label': '지금 바로 만들 수 있어요', 'recipes': [], 'count': 0},
        'almost_ready': {'label': '재료 1-2개만 있으면 가능해요', 'recipes': [], 'count': 0}
    }
    
    for item in scored_recipes:
        recipe = item['recipe']
        score_data = item['score_data']
        category = recipe.get_recommendation_category(score_data['total_score'])
        
        # 식재료 상태 정보 추가
        status_info = recipe.get_ingredients_status_for_user(user_ingredients_dict)
        
        if category in categories:
            recipe_data = {
                'recipe_id': recipe.recipe_id,
                'title': recipe.title,
                'image_url': recipe.image_url,
                'source': recipe.source,
                'ready_minutes': recipe.ready_minutes,
                'servings': recipe.servings,
                'difficulty': recipe.difficulty,
                'difficulty_display': recipe.get_difficulty_display(),
                'total_score': score_data['total_score'],
                'score_breakdown': {
                    'ingredient': score_data['ingredient_score'],
                    'expiry': score_data['expiry_score'],
                    'difficulty': score_data['difficulty_score'],
                    'personalization': score_data['personalization_score']
                },
                'missing_ingredients_count': score_data['missing_ingredients_count'],
                'has_expired': status_info['has_expired'],
                'has_urgent': status_info['has_urgent'],
                'expired_ingredients': status_info['expired_ingredients'],
                'urgent_ingredients': status_info['urgent_ingredients']
            }
            
            categories[category]['recipes'].append(recipe_data)
            categories[category]['count'] += 1
    
    total_count = sum(cat['count'] for cat in categories.values())
    
    return {
        'categories': categories,
        'total_count': total_count
    }


# ==================== API 뷰 ==================== #

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_recipe_recommendations(request):
    """
    통합 레시피 추천 API
    """
    user = request.user
    
    # 요청 파라미터
    ingredient_ids = request.data.get('ingredient_ids', [])
    use_all = request.data.get('use_all', False)
    include_spoonacular = request.data.get('include_spoonacular', True)
    max_results = request.data.get('max_results', 20)
    
    # 사용자 보유 식재료 조회
    user_ingredients = UserIngredient.objects.filter(
        user=user,
        is_consumed=False
    ).select_related('ingredient', 'ingredient__category')
    
    # 선택된 식재료 필터링
    if use_all:
        selected_ingredients = user_ingredients
    elif ingredient_ids:
        selected_ingredients = user_ingredients.filter(
            user_ingredient_id__in=ingredient_ids
        )
    else:
        selected_ingredients = user_ingredients
    
    if not selected_ingredients.exists():
        return Response({
            'message': '선택된 식재료가 없습니다',
            'categories': {
                'urgent_ready': {'label': '유통기한 임박 레시피', 'recipes': [], 'count': 0},
                'ready': {'label': '지금 바로 만들 수 있어요', 'recipes': [], 'count': 0},
                'almost_ready': {'label': '재료 1-2개만 있으면 가능해요', 'recipes': [], 'count': 0}
            },
            'total_count': 0
        })
    
    # 식재료 ID 리스트 & 딕셔너리
    selected_ingredient_ids = list(selected_ingredients.values_list('ingredient_id', flat=True))
    user_ingredients_dict = {ui.ingredient_id: ui for ui in selected_ingredients}
    
    # 1. DB 검색 (한식 + 기존 레시피)
    db_recipes = search_recipes_from_db(selected_ingredient_ids, user)
    
    # 2. Spoonacular 검색
    spoon_recipes = []
    if include_spoonacular:
        spoon_recipes = search_recipes_from_spoonacular(
            selected_ingredients,
            max_results=10
        )
    
    # 3. 통합 및 중복 제거
    all_recipes = list(db_recipes) + spoon_recipes
    unique_recipes = {}
    
    for recipe in all_recipes:
        if recipe.external_id not in unique_recipes:
            unique_recipes[recipe.external_id] = recipe
    
    # 4. 사용자 스킬 레벨
    user_skill_level = 'INTERMEDIATE'  # 기본값
    if hasattr(user, 'profile') and user.profile:
        user_skill_level = user.profile.cooking_level
    
    # 5. 추천 점수 계산 및 정렬
    result = calculate_final_recommendations(
        recipes=list(unique_recipes.values())[:max_results],
        user=user,
        user_ingredients_dict=user_ingredients_dict,
        user_skill_level=user_skill_level
    )
    
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_recipe_detail(request, recipe_id):
    """레시피 상세 조회"""
    try:
        recipe = Recipe.objects.prefetch_related(
            'recipe_ingredients__ingredient'
        ).get(recipe_id=recipe_id)
    except Recipe.DoesNotExist:
        return Response(
            {'error': '존재하지 않는 레시피입니다'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # 사용자 보유 식재료 확인 (로그인 시)
    user_ingredient_ids = []
    if request.user.is_authenticated:
        user_ingredient_ids = list(
            UserIngredient.objects.filter(
                user=request.user,
                is_consumed=False
            ).values_list('ingredient_id', flat=True)
        )
    
    # 직렬화
    serializer = RecipeDetailSerializer(recipe, context={
        'user_ingredient_ids': user_ingredient_ids
    })
    
    return Response(serializer.data)


# ==================== 템플릿 뷰 ==================== #

@login_required
def recipe_list_view(request):
    """레시피 목록 페이지"""
    return render(request, 'recipes/recipe_list.html')


@login_required
def recipe_detail_view(request, recipe_id):
    """레시피 상세 페이지"""
    try:
        recipe = Recipe.objects.prefetch_related(
            'recipe_ingredients__ingredient'
        ).get(recipe_id=recipe_id)
    except Recipe.DoesNotExist:
        return render(request, 'recipes/recipe_not_found.html', status=404)
    
    # 사용자 보유 식재료
    user_ingredients = UserIngredient.objects.filter(
        user=request.user,
        is_consumed=False
    ).select_related('ingredient')
    
    user_ingredient_ids = [ui.ingredient_id for ui in user_ingredients]
    user_ingredients_dict = {ui.ingredient_id: ui for ui in user_ingredients}
    
    # 레시피 재료
    recipe_ingredients = recipe.recipe_ingredients.all()
    
    # 재료별 보유 상태
    for ri in recipe_ingredients:
        ri.is_owned = ri.ingredient_id in user_ingredient_ids
        
        if ri.is_owned:
            user_ing = user_ingredients_dict[ri.ingredient_id]
            ri.user_ingredient = user_ing
            ri.days_left = user_ing.days_until_expiry
        else:
            ri.user_ingredient = None
            ri.days_left = None
    
    # 찜 여부
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = FavoriteRecipe.objects.filter(
            user=request.user,
            recipe=recipe
        ).exists()
    
    context = {
        'recipe': recipe,
        'recipe_ingredients': recipe_ingredients,
        'is_favorited': is_favorited
    }
    
    return render(request, 'recipes/recipe_detail.html', context)


@login_required
def cooking_mode_view(request, recipe_id):
    """조리 모드 페이지 (단계별 UI)"""
    try:
        recipe = Recipe.objects.get(recipe_id=recipe_id)
    except Recipe.DoesNotExist:
        return render(request, 'recipes/recipe_not_found.html', status=404)
    
    context = {'recipe': recipe}
    return render(request, 'recipes/cooking_mode.html', context)


@login_required
def cooking_complete_view(request, recipe_id):
    """조리 완료 페이지"""
    try:
        recipe = Recipe.objects.prefetch_related(
            'recipe_ingredients__ingredient'
        ).get(recipe_id=recipe_id)
    except Recipe.DoesNotExist:
        return render(request, 'recipes/recipe_not_found.html', status=404)
    
    # 사용한 식재료 체크리스트
    user_ingredients = UserIngredient.objects.filter(
        user=request.user,
        ingredient_id__in=recipe.recipe_ingredients.values_list('ingredient_id', flat=True),
        is_consumed=False
    ).select_related('ingredient')
    
    context = {
        'recipe': recipe,
        'user_ingredients': user_ingredients
    }
    
    return render(request, 'recipes/cooking_complete.html', context)