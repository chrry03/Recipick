from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.conf import settings

from .models import Recipe, FavoriteRecipe
from ingredients.models import UserIngredient, IngredientMaster
from .serializers import (
    RecipeListSerializer,
    RecipeDetailSerializer,
    FavoriteRecipeSerializer,
    RecipeSearchSerializer
)

# Create your views here.
class RecipeViewSet(viewsets.ReadOnlyModelViewSet):
    """레시피 조회 및 추천"""
    
    queryset = Recipe.objects.filter(is_active=True)
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RecipeDetailSerializer
        return RecipeListSerializer
    
    def get_queryset(self):
        """
        레시피 목록 조회
        
        Query Parameters:
        - sort: recommend(추천순, 기본), time(시간순)
        - min_score: 최소 추천 점수 (기본 60)
        - limit: 결과 개수 (기본 10)
        - filter: owned_only(보유 식재료만), favorited(찜한 레시피만)
        """
        queryset = super().get_queryset()
        
        # 필터링 옵션
        filter_type = self.request.query_params.get('filter')
        
        # 찜한 레시피만 보기
        if filter_type == 'favorited' and self.request.user.is_authenticated:
            favorited_recipe_ids = FavoriteRecipe.objects.filter(
                user=self.request.user
            ).values_list('recipe_id', flat=True)
            queryset = queryset.filter(recipe_id__in=favorited_recipe_ids)
        
        # 보유 식재료만으로 만들 수 있는 레시피
        if filter_type == 'owned_only' and self.request.user.is_authenticated:
            queryset = self._filter_by_owned_ingredients(queryset)
        
        # 정렬 방식
        sort_by = self.request.query_params.get('sort', 'recommend')
        
        if sort_by == 'recommend' and self.request.user.is_authenticated:
            # 추천순 정렬 (팀 모델 메서드 활용)
            return self._get_recommended_recipes(queryset)
        elif sort_by == 'time':
            queryset = queryset.order_by('ready_minutes')
        
        return queryset.prefetch_related('recipe_ingredients__ingredient')
    
    def _get_recommended_recipes(self, queryset):
        """
        추천 알고리즘 적용 (팀 모델 메서드 활용)
        """
        user = self.request.user
        min_score = float(self.request.query_params.get('min_score', 60))
        limit = int(self.request.query_params.get('limit', 20))
        
        # Recipe.get_recommendations_for_user() 메서드 활용
        recommendations = Recipe.get_recommendations_for_user(
            user=user,
            limit=limit * 2,  # 필터링 후 부족할 수 있으므로 여유있게
            min_score=min_score
        )
        
        # 추천 결과를 Recipe 객체 리스트로 변환하고 점수 정보 추가
        recipes = []
        for rec in recommendations[:limit]:
            recipe = rec['recipe']
            # 동적 속성 추가
            if rec['scores']:
                recipe.recommendation_score = rec['scores']['total_score']
                recipe.score_details = rec['scores']
                recipe.recommendation_category = rec['category']
                recipe.missing_ingredients_count = rec['scores']['missing_ingredients_count']
                if 'ingredients_status' in rec:
                    recipe.ingredients_status = rec['ingredients_status']
            recipes.append(recipe)
        
        return recipes
    
    def _filter_by_owned_ingredients(self, queryset):
        """
        보유 식재료만으로 만들 수 있는 레시피 필터링
        (부족한 재료가 0개인 레시피만)
        """
        user = self.request.user
        
        # 사용자 보유 식재료 가져오기
        user_ingredients = UserIngredient.objects.filter(
            user=user,
            is_consumed=False
        ).select_related('ingredient')
        
        if not user_ingredients.exists():
            return queryset.none()
        
        # 보유 식재료 ID 세트
        owned_ingredient_ids = set(ui.ingredient_id for ui in user_ingredients)
        
        # 필터링: 필수 재료가 모두 보유 목록에 있는 레시피만
        filtered_recipe_ids = []
        
        for recipe in queryset.prefetch_related('recipe_ingredients'):
            # 필수 재료만 확인
            required_ingredient_ids = set(
                recipe.recipe_ingredients.filter(is_optional=False)
                .values_list('ingredient_id', flat=True)
            )
            
            # 모든 필수 재료를 보유한 경우
            if required_ingredient_ids.issubset(owned_ingredient_ids):
                filtered_recipe_ids.append(recipe.recipe_id)
        
        return queryset.filter(recipe_id__in=filtered_recipe_ids)
    
    def retrieve(self, request, *args, **kwargs):
        """레시피 상세 조회 (추천 점수 포함)"""
        recipe = self.get_object()
        
        # 로그인 사용자에게는 추천 점수 계산
        if request.user.is_authenticated:
            user_ingredients = UserIngredient.objects.filter(
                user=request.user,
                is_consumed=False
            ).select_related('ingredient')
            
            user_ingredient_ids = [ui.ingredient_id for ui in user_ingredients]
            user_ingredients_dict = {ui.ingredient_id: ui for ui in user_ingredients}
            
            # User skill level
            if hasattr(request.user, 'profile'):
                user_skill = request.user.profile.cooking_level
            else:
                user_skill = 'BEGINNER'
            
            # 점수 계산
            score_data = recipe.calculate_recommendation_score(
                user=request.user,
                user_ingredient_ids=user_ingredient_ids,
                user_ingredients_dict=user_ingredients_dict,
                user_skill_level=user_skill
            )
            
            # 재료 상태 정보
            ingredients_status = recipe.get_ingredients_status_for_user(
                user_ingredients_dict
            )
            
            # 동적 속성 추가
            recipe.recommendation_score = score_data['total_score']
            recipe.score_details = score_data
            recipe.ingredients_status = ingredients_status
        
        serializer = self.get_serializer(recipe)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        레시피 검색 (Spoonacular API 활용)
        
        Query Parameters:
        - keyword: 검색어
        - ingredients: 재료 (콤마로 구분)
        - max_ready_time: 최대 조리 시간
        - difficulty: 난이도
        """
        # 파라미터 검증
        serializer = RecipeSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        
        # Spoonacular API 호출
        api_key = getattr(settings, 'SPOONACULAR_API_KEY', '')
        if not api_key:
            return Response(
                {'detail': 'Spoonacular API 키가 설정되지 않았습니다.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # 재료 기반 검색
        if params.get('ingredients'):
            ingredient_names = [name.strip() for name in params['ingredients'].split(',')]
            recipe_ids = Recipe.search_by_ingredients_spoonacular(
                ingredient_names=ingredient_names,
                api_key=api_key,
                number=params.get('limit', 10)
            )
            
            # IngredientMaster 매핑 생성
            ingredient_mapping = IngredientMaster.create_ingredient_mapping_for_api()
            
            # 각 레시피 정보 가져오기
            recipes = []
            for recipe_id in recipe_ids:
                recipe = Recipe.fetch_and_save_from_spoonacular(
                    recipe_id=recipe_id,
                    api_key=api_key,
                    ingredient_mapping=ingredient_mapping
                )
                if recipe:
                    recipes.append(recipe)
        
        # 키워드 검색
        elif params.get('keyword'):
            # DB에서 먼저 검색
            recipes = Recipe.objects.filter(
                Q(title__icontains=params['keyword']) |
                Q(recipe_ingredients__ingredient_name__icontains=params['keyword']),
                is_active=True
            ).distinct()
            
            # 난이도 필터
            if params.get('difficulty'):
                recipes = recipes.filter(difficulty=params['difficulty'])
            
            # 조리 시간 필터
            if params.get('max_ready_time'):
                recipes = recipes.filter(ready_minutes__lte=params['max_ready_time'])
            
            recipes = recipes[:params.get('limit', 10)]
        
        else:
            # 필터만 적용
            recipes = Recipe.objects.filter(is_active=True)
            
            if params.get('difficulty'):
                recipes = recipes.filter(difficulty=params['difficulty'])
            
            if params.get('max_ready_time'):
                recipes = recipes.filter(ready_minutes__lte=params['max_ready_time'])
            
            recipes = recipes[:params.get('limit', 10)]
        
        # 추천순 정렬 적용 (로그인 사용자)
        if request.user.is_authenticated and params.get('sort') == 'recommend':
            recipe_ids = [r.recipe_id for r in recipes]
            queryset = Recipe.objects.filter(recipe_id__in=recipe_ids)
            recommended = self._get_recommended_recipes(queryset)
            serializer = RecipeListSerializer(
                recommended,
                many=True,
                context={'request': request}
            )
        else:
            serializer = RecipeListSerializer(
                recipes,
                many=True,
                context={'request': request}
            )
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def favorite(self, request, pk=None):
        """
        레시피 찜하기/취소
        
        POST /recipes/{id}/favorite
        """
        if not request.user.is_authenticated:
            return Response(
                {'detail': '로그인이 필요합니다.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        recipe = self.get_object()
        
        favorite, created = FavoriteRecipe.objects.get_or_create(
            user=request.user,
            recipe=recipe
        )
        
        if not created:
            # 이미 찜한 경우 -> 취소
            favorite.delete()
            return Response({
                'is_favorited': False,
                'message': '찜이 취소되었습니다.'
            })
        
        return Response({
            'is_favorited': True,
            'message': '찜 목록에 추가되었습니다.'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def favorites(self, request):
        """
        찜한 레시피 목록 조회
        
        GET /recipes/favorites
        """
        if not request.user.is_authenticated:
            return Response(
                {'detail': '로그인이 필요합니다.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        favorites = FavoriteRecipe.objects.filter(
            user=request.user
        ).select_related('recipe')
        
        limit = int(request.query_params.get('limit', 10))
        favorites = favorites[:limit]
        
        serializer = FavoriteRecipeSerializer(favorites, many=True)
        return Response(serializer.data)