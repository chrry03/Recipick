"""
Recipes Views (한글 번역 + 단계별 표시 완전 통합 버전)

주요 기능:
1. Spoonacular + 한식 레시피 완전 통합
2. 한글 번역 자동 적용 (display_title, display_steps)
3. 추천 알고리즘 미세 조정
4. 소비기한 임박 처리 개선
5. 단계별 요리 모드 (한글 우선)
6. 에러 처리 강화
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
from .utils import (
    search_recipes_from_db, 
    search_recipes_from_spoonacular, 
    calculate_final_recommendations
)
from django.conf import settings


def _resolve_recipe(recipe_id):
    """
    recipe_id로 Recipe 조회. Spoonacular 레시피(음수 ID)는 external_id로 조회하거나 API에서 가져옴.
    """
    if recipe_id < 0:
        external_id = str(-recipe_id)
        recipe = Recipe.objects.filter(
            external_id=external_id,
            source='spoonacular'
        ).prefetch_related('recipe_ingredients__ingredient').first()
        if not recipe:
            api_key = getattr(settings, 'SPOONACULAR_API_KEY', '')
            if api_key:
                recipe = Recipe.fetch_from_spoonacular_by_id(external_id, api_key, None)
        return recipe
    try:
        return Recipe.objects.prefetch_related('recipe_ingredients__ingredient').get(recipe_id=recipe_id)
    except Recipe.DoesNotExist:
        return None


# ==================== ViewSets ==================== #

class RecipeViewSet(viewsets.ReadOnlyModelViewSet):
    """레시피 조회 ViewSet (한글 번역 우선)"""
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
        
        # ============ 한글 번역된 레시피 우선 정렬 (NEW!) ============
        queryset = queryset.order_by('-is_translated', '-created_at')
        
        return queryset.prefetch_related('recipe_ingredients__ingredient')
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def recommendations(self, request):
        return get_recipe_recommendations(request)


class FavoriteRecipeViewSet(viewsets.ModelViewSet):
    """찜한 레시피 관리 ViewSet"""
    serializer_class = FavoriteRecipeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # ========== [수정] recipe_ingredients를 prefetch하여 재료 정보 포함 ==========
        return FavoriteRecipe.objects.filter(
            user=self.request.user
        ).select_related('recipe').prefetch_related(
            'recipe__recipe_ingredients__ingredient'
        ).order_by('-created_at')
    
    def get_serializer_context(self):
        # ========== [추가] context에 request 포함 (재료 상태 계산용) ==========
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
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
    
    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """
        찜 토글 (추가/취소)
        
        POST /recipes/api/favorites/toggle/
        Body: {"recipe_id": 123}
        
        Returns:
            {
                "is_favorite": true/false,
                "recipe_id": 123,
                "message": "찜이 추가/취소되었습니다"
            }
        """
        recipe_id = request.data.get('recipe_id')
        
        if not recipe_id:
            return Response(
                {'error': 'recipe_id가 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Recipe 객체 찾기
            recipe = Recipe.objects.get(recipe_id=recipe_id)
        except Recipe.DoesNotExist:
            return Response(
                {'error': '존재하지 않는 레시피입니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 찜 상태 확인
        favorite = FavoriteRecipe.objects.filter(
            user=request.user, 
            recipe=recipe
        ).first()
        
        if favorite:
            # 찜 취소
            favorite.delete()
            return Response({
                'is_favorite': False,
                'recipe_id': recipe_id,
                'message': '찜이 취소되었습니다'
            })
        else:
            # 찜 추가
            favorite = FavoriteRecipe.objects.create(
                user=request.user, 
                recipe=recipe
            )
            serializer = self.get_serializer(favorite)
            return Response({
                'is_favorite': True,
                'recipe_id': recipe_id,
                'message': '찜이 추가되었습니다',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)


# ==================== API Views (Function Based) ==================== #

@api_view(['POST'])
@permission_classes([AllowAny])
def get_recipe_recommendations(request):
    """
    통합 레시피 추천 API (한글 번역 + utils.py 연동)
    
    주요 기능:
    1. 한글/영문 레시피 통합 검색
    2. Spoonacular API 활성화
    3. 한글 우선 반환
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 1. 로그인 여부에 따라 user 처리
    if request.user.is_authenticated:
        user = request.user
        user_ingredients = UserIngredient.objects.filter(
            user=user,
            is_consumed=False
        ).select_related('ingredient', 'ingredient__category')
        logger.info(f"✅ 사용자: {user.username}, 식재료: {user_ingredients.count()}개")
    else:
        user = None
        user_ingredients = UserIngredient.objects.none()
        logger.info("⚠️ 비로그인 사용자")

    # 2. 요청 파라미터 받기
    ingredient_ids = request.data.get('ingredient_ids', [])
    use_all = request.data.get('use_all', False)
    max_results = request.data.get('max_results', 100)  # 20 → 100으로 증가
    keyword = request.data.get('keyword', '').strip()
    
    # ========== [핵심] 내 재료만 필터 ==========
    only_owned_ingredients = request.data.get('only_owned_ingredients', False)
    
    logger.info(f"📥 요청: use_all={use_all}, keyword='{keyword}', ingredient_ids={ingredient_ids}, only_owned={only_owned_ingredients}")
    
    # ============ Spoonacular API 활성화 (수정!) ============
    include_spoonacular = request.data.get('include_spoonacular', True)

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
    
    logger.info(f"🥬 선택된 식재료: {selected_ingredients.count()}개")
    
    # 검색어도 없고 재료도 없으면 빈 결과 반환
    if not selected_ingredients.exists() and not keyword:
        logger.warning("❌ 식재료도 없고 검색어도 없음 → 빈 결과 반환")
        return Response({
            'message': '선택된 식재료 또는 검색어가 없습니다',
            'categories': {},
            'total_count': 0,
            'recipes': [] 
        })
    
    selected_ingredient_ids = list(
        selected_ingredients.values_list('ingredient_id', flat=True)
    )
    user_ingredients_dict = {
        ui.ingredient_id: ui for ui in selected_ingredients
    }
    
    logger.info(f"📋 식재료 ID 목록: {selected_ingredient_ids[:5]}...")  # 처음 5개만

    # ==========================================
    # [검색 모드] 키워드 기반 단순 검색 (추천/스코어 로직 없음)
    # - 제목(한글/영문)에 키워드 포함된 레시피만 반환
    # - 로그인/비로그인 동일: 찜 상태만 주입
    # ==========================================
    if keyword:
        logger.info(f"🔍 [검색 모드] 키워드='{keyword}'")

        # 키워드 매칭 레시피 DB 조회 (제목 한글/영문 모두 검색)
        keyword_qs = Recipe.objects.filter(
            Q(title__icontains=keyword) | Q(title_ko__icontains=keyword),
            is_active=True
        ).prefetch_related('recipe_ingredients__ingredient').order_by('-is_translated', '-created_at')

        keyword_recipes = list(keyword_qs)
        logger.info(f"🔍 [검색 모드] 키워드 매칭 레시피: {len(keyword_recipes)}개")

        if not keyword_recipes:
            return Response({
                'recipes': [],
                'total_count': 0,
                'search_mode': True,
                'message': f"'{keyword}'에 해당하는 레시피가 없습니다."
            })

        # 키워드 기반 단순 검색: 스코어/정렬 없이 결과만 반환 (재료 상태는 표시)
        recipes_data = []
        for recipe in keyword_recipes:
            try:
                status_info = recipe.get_ingredients_status_for_user(user_ingredients_dict)
            except Exception:
                status_info = {
                    'ingredients_status': {},
                    'has_expired': False,
                    'has_urgent': False,
                    'expired_ingredients': [],
                    'urgent_ingredients': [],
                }

            missing_count = sum(
                1 for s in status_info.get('ingredients_status', {}).values()
                if isinstance(s, dict) and not s.get('is_owned', False)
            )

            recipes_data.append({
                'recipe_id': recipe.recipe_id,
                'title': recipe.get_display_title(),
                'title_ko': recipe.title_ko,
                'title_en': recipe.title,
                'image_url': recipe.image_url,
                'ready_minutes': recipe.ready_minutes,
                'difficulty': recipe.difficulty,
                'difficulty_display': recipe.get_difficulty_display() if hasattr(recipe, 'get_difficulty_display') else recipe.difficulty,
                'total_score': None,
                'score_breakdown': {},
                'missing_ingredients_count': missing_count,
                'ingredients_status': {
                    'ingredients_status': status_info.get('ingredients_status', {}),
                    'has_expired': status_info.get('has_expired', False),
                    'has_urgent': status_info.get('has_urgent', False),
                },
                'expired_ingredients': status_info.get('expired_ingredients', []),
                'urgent_ingredients': status_info.get('urgent_ingredients', []),
                'is_favorited': False,
            })

        # 로그인 시 찜 상태만 주입
        if user:
            all_ids = [r['recipe_id'] for r in recipes_data]
            favorited_set = set(FavoriteRecipe.objects.filter(
                user=user,
                recipe_id__in=all_ids
            ).values_list('recipe_id', flat=True))
            for r in recipes_data:
                r['is_favorited'] = r['recipe_id'] in favorited_set

        # ========== [핵심 수정] 키워드 검색 모드에서도 "내 재료만" 필터 적용 ==========
        if only_owned_ingredients and user and selected_ingredient_ids:
            owned_set = set(selected_ingredient_ids)
            filtered_data = []
            for r in recipes_data:
                # ingredients_status에서 missing 재료가 있는지 확인
                status_map = r.get('ingredients_status', {}).get('ingredients_status', {})
                has_missing = any(
                    isinstance(s, dict) and not s.get('is_owned', False)
                    for k, s in status_map.items()
                    if k not in ('has_expired', 'has_urgent')
                )
                if not has_missing:
                    filtered_data.append(r)
            recipes_data = filtered_data
            logger.info(f"🔒 [검색 모드] '내 재료만' 적용 후: {len(recipes_data)}개")

        logger.info(f"✅ [검색 모드] 키워드 기반 {len(recipes_data)}개 반환")
        return Response({
            'recipes': recipes_data,
            'total_count': len(recipes_data),
            'search_mode': True
        })

    # ==========================================
    # [핵심 수정] "내 재료만" 모드: DB 전체 레시피에서 모든 재료를 보유한 레시피 탐색
    # ==========================================
    if only_owned_ingredients and user and selected_ingredient_ids:
        logger.info("=" * 50)
        logger.info("🔒 '내 재료만' 모드: DB 전체 레시피 탐색 시작")
        logger.info(f"🔒 보유 식재료 개수: {len(selected_ingredient_ids)}개")

        owned_set = set(selected_ingredient_ids)

        # DB의 모든 활성 레시피를 대상으로 검색 (상위 N개 제한 없음)
        all_db_recipes = Recipe.objects.filter(
            is_active=True
        ).prefetch_related('recipe_ingredients__ingredient')

        fully_owned_recipes = []
        for recipe in all_db_recipes:
            try:
                required_ingredients = recipe.recipe_ingredients.filter(is_optional=False)
                req_ids = set(
                    ri.ingredient_id for ri in required_ingredients
                    if ri.ingredient_id is not None
                )

                # 필수 재료가 없으면 전체 재료를 대상으로 확인
                if not req_ids:
                    req_ids = set(
                        ri.ingredient_id for ri in recipe.recipe_ingredients.all()
                        if ri.ingredient_id is not None
                    )

                # 레시피에 식재료 정보가 전혀 없으면 제외
                if not req_ids:
                    continue

                # 모든 필수 재료를 보유하고 있는지 확인
                if req_ids.issubset(owned_set):
                    fully_owned_recipes.append(recipe)

            except Exception as e:
                logger.error(f"  ❌ 필터링 에러 ({recipe.recipe_id}): {e}")
                continue

        logger.info(f"🔒 '내 재료만' 결과: {len(fully_owned_recipes)}개")
        logger.info("=" * 50)

        # 7. 사용자 스킬 레벨
        user_skill_level = 'INTERMEDIATE'
        if user:
            try:
                if hasattr(user, 'profile'):
                    user_skill_level = user.profile.cooking_level
            except:
                pass

        # 점수 임계값을 0으로 설정 → 모든 재료를 보유하면 무조건 표시
        result = calculate_final_recommendations(
            recipes=fully_owned_recipes[:max_results],
            user=user,
            user_ingredients_dict=user_ingredients_dict,
            user_skill_level=user_skill_level,
            min_score=0
        )

    else:
        # ==========================================
        # 4. DB 검색 (utils.py 함수 사용) - 일반 추천 모드 (검색어 없음)
        # ==========================================
        db_recipes_by_ing = []
        if selected_ingredient_ids:
            # utils.py 함수가 '우유' 같은 문자열 에러를 방지합니다.
            db_recipes_by_ing = list(
                search_recipes_from_db(selected_ingredient_ids, user)
            )
            logger.info(f"🗄️ DB 레시피 (식재료 기반): {len(db_recipes_by_ing)}개")

        # ※ 키워드가 있는 경우는 위의 [검색 모드] 블록에서 이미 return 처리됨.
        #   여기(추천 모드)에서는 keyword가 항상 빈 문자열이므로 별도 키워드 검색 불필요.

        # 결과 합치기
        combined_db = db_recipes_by_ing
        logger.info(f"📦 DB 레시피 합계: {len(combined_db)}개")

        # ==========================================
        # 5. Spoonacular 검색 (utils.py 함수 사용)
        # ==========================================
        spoon_recipes = []
        if include_spoonacular and selected_ingredients.exists():
            logger.info("🌐 Spoonacular 검색 시작...")
            # utils.py 함수가 402 에러를 방지하고 빈 리스트를 반환합니다.
            spoon_recipes = search_recipes_from_spoonacular(
                selected_ingredients,
                max_results=10
            )
            logger.info(f"🌐 Spoonacular 레시피: {len(spoon_recipes)}개")

        # 6. 통합 및 중복 제거
        all_recipes = list(combined_db) + spoon_recipes
        unique_recipes = {}

        for recipe in all_recipes:
            if recipe.external_id not in unique_recipes:
                unique_recipes[recipe.external_id] = recipe

        logger.info(f"🎯 중복 제거 후: {len(unique_recipes)}개")

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

        logger.info(f"🧮 점수 계산 시작: {len(final_list)}개")

        result = calculate_final_recommendations(
            recipes=final_list[:max_results],
            user=user,
            user_ingredients_dict=user_ingredients_dict,
            user_skill_level=user_skill_level
        )

    # ==================== [수정됨: 찜 상태 주입 (Dict/Object 호환)] ====================
    if user and user.is_authenticated:
        # 1. ID 추출 헬퍼 함수 (딕셔너리와 객체 모두 처리)
        def get_id_safe(item):
            if isinstance(item, dict):
                return item.get('recipe_id') or item.get('id')
            return getattr(item, 'recipe_id', None)

        all_recipe_ids = []
        
        # (A) 카테고리 구조일 경우
        if 'categories' in result:
            for cat_key in ['urgent_ready', 'ready', 'almost_ready']:
                if cat_key in result['categories']:
                    recipes = result['categories'][cat_key].get('recipes', [])
                    # 여기서 get_id_safe 사용
                    ids = [get_id_safe(r) for r in recipes]
                    all_recipe_ids.extend([i for i in ids if i is not None])
                    
        # (B) 리스트 구조일 경우
        if 'recipes' in result:
            ids = [get_id_safe(r) for r in result['recipes']]
            all_recipe_ids.extend([i for i in ids if i is not None])
            
        # 2. 사용자가 찜한 레시피 ID 조회
        favorited_ids = set(FavoriteRecipe.objects.filter(
            user=user,
            recipe_id__in=all_recipe_ids
        ).values_list('recipe_id', flat=True))
        
        # 3. 찜 상태 주입 헬퍼 함수 (딕셔너리와 객체 모두 처리)
        def inject_favorite_status(recipe_list):
            for recipe in recipe_list:
                rid = get_id_safe(recipe)
                is_fav = rid in favorited_ids
                
                if isinstance(recipe, dict):
                    recipe['is_favorited'] = is_fav  # 딕셔너리인 경우
                else:
                    # 객체인 경우 (동적 속성 추가)
                    setattr(recipe, 'is_favorited', is_fav)

        # (A) 카테고리 구조 주입
        if 'categories' in result:
            for cat_key in ['urgent_ready', 'ready', 'almost_ready']:
                if cat_key in result['categories']:
                    inject_favorite_status(result['categories'][cat_key].get('recipes', []))
                    
        # (B) 리스트 구조 주입
        if 'recipes' in result:
            inject_favorite_status(result['recipes'])
            
    # ====================================================================
    
    logger.info(f"✅ 최종 결과: {result.get('total_count', 0)}개")
    
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_recipe_detail(request, recipe_id):
    """레시피 상세 조회 API (한글 우선)"""
    try:
        recipe = Recipe.objects.prefetch_related(
            'recipe_ingredients__ingredient'
        ).get(recipe_id=recipe_id)
    except Recipe.DoesNotExist:
        return Response(
            {'error': '존재하지 않는 레시피입니다'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
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
    """레시피 상세 페이지 (한글 우선 표시)"""
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


def cooking_mode_view(request, recipe_id, step=None):
    """
    조리 모드 페이지 (한글 단계 우선 표시)
    
    주요 기능:
    1. display_steps() 사용 (한글 우선)
    2. 단계별 타이머 정보 포함
    3. 1-based index 처리
    
    Args:
        request: HTTP request
        recipe_id: 레시피 ID (음수면 Spoonacular external_id)
        step: 현재 단계 번호 (URL parameter, optional)
    """
    recipe = _resolve_recipe(recipe_id)
    if not recipe:
        return render(request, 'recipes/recipe_not_found.html', status=404)

    # ============ 한글 단계 우선 (수정!) ============
    # get_display_steps()는 이미 한글 instruction_ko 우선으로 반환합니다.
    instructions = recipe.get_display_steps()
    
    # 백업: steps 필드가 없으면 빈 리스트
    if not instructions:
        instructions = []
    
    total_steps = max(1, len(instructions))

    # ========== [수정] 현재 단계 (URL parameter 우선, 없으면 query parameter, 기본값 1) ==========
    if step is not None:
        # URL path parameter로 받은 경우 (/recipes/123/cooking/2/)
        current_step = step
    else:
        # Query parameter로 받은 경우 (/recipes/123/cooking/?step=2)
        try:
            current_step = max(1, min(int(request.GET.get('step', 1)), total_steps))
        except (TypeError, ValueError):
            current_step = 1
    
    # step 범위 검증
    current_step = max(1, min(current_step, total_steps))

    # 현재 단계 데이터
    step_data = None
    if instructions and 1 <= current_step <= len(instructions):
        step_data = instructions[current_step - 1]
        
        # step_data는 이미 dict 형태:
        # {
        #     'number': 1,
        #     'instruction': '한글 조리법',
        #     'timer_seconds': 60
        # }
        if isinstance(step_data, dict):
            step_data = dict(step_data)
            
            # step 번호가 없으면 순서대로 부여
            if 'step' not in step_data:
                step_data['step'] = current_step
            
            # instruction을 description으로 복사 (템플릿 호환)
            if 'instruction' in step_data and 'description' not in step_data:
                step_data['description'] = step_data['instruction']
        else:
            # dict가 아닌 경우 (비정상)
            step_data = {
                'step': current_step, 
                'description': str(step_data), 
                'image': None
            }

    context = {
        'recipe': recipe,
        'total_steps': total_steps,
        'current_step': current_step,
        'step_data': step_data,
    }
    return render(request, 'recipes/cooking_mode.html', context)


def cooking_complete_view(request, recipe_id):
    """조리 완료 페이지"""
    recipe = _resolve_recipe(recipe_id)
    if not recipe:
        return render(request, 'recipes/recipe_not_found.html', status=404)

    # 다 쓴 재료 체크하기: 레시피에 적힌 재료 목록 (모든 재료 포함)
    recipe_ingredients = recipe.recipe_ingredients.select_related(
        'ingredient'
    ).all()  # order_by 제거 - 모든 재료 표시
    
    ingredients = []
    for ri in recipe_ingredients:
        # ingredient가 None인 경우 안전 처리
        if ri.ingredient:
            ingredients.append({
                'id': ri.ingredient.ingredient_id, 
                'name': ri.ingredient.name_ko or ri.ingredient.name_en or ri.ingredient_name or '알 수 없는 재료'
            })
        elif ri.ingredient_name:
            # ingredient가 없지만 ingredient_name이 있는 경우
            ingredients.append({
                'id': None,  # ID가 없으므로 삭제 불가
                'name': ri.ingredient_name
            })

    user_ingredients = []
    owned_ingredient_ids = set()
    if request.user.is_authenticated:
        user_ingredients = UserIngredient.objects.filter(
            user=request.user,
            ingredient_id__in=[ing['id'] for ing in ingredients if ing['id']],
            is_consumed=False
        ).select_related('ingredient')
        owned_ingredient_ids = {ui.ingredient_id for ui in user_ingredients}

    # 체크리스트에는 보유 재료만 표시 (로그인한 경우)
    if request.user.is_authenticated:
        ingredients = [ing for ing in ingredients if ing['id'] and ing['id'] in owned_ingredient_ids]

    context = {
        'recipe': recipe,
        'ingredients': ingredients,
        'user_ingredients': user_ingredients,
    }
    return render(request, 'recipes/cooking_complete.html', context)