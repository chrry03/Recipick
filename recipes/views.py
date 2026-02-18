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
    # [검색 모드] 키워드가 있을 때는 추천 로직을 완전히 우회하고 별도 처리
    # - 비로그인: 키워드 매칭 레시피를 점수 필터 없이 전부 반환
    # - 로그인:   키워드 매칭 레시피만 대상으로 재료 점수 계산 후 정렬 (55점 필터 없음)
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

        # ── 비로그인: 점수 계산 없이 전체 반환 ──
        if not user:
            recipes_data = []
            for recipe in keyword_recipes:
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
                    'missing_ingredients_count': 0,
                    'ingredients_status': {'ingredients_status': {}},
                    'expired_ingredients': [],
                    'urgent_ingredients': [],
                    'is_favorited': False,
                })
            logger.info(f"✅ [검색 모드 / 비로그인] {len(recipes_data)}개 반환")
            return Response({
                'recipes': recipes_data,
                'total_count': len(recipes_data),
                'search_mode': True
            })

        # ── 로그인: 재료 점수 계산 후 정렬 (55점 필터 없음) ──
        # 사용자 스킬 레벨
        _skill_level = 'INTERMEDIATE'
        try:
            if hasattr(user, 'profile'):
                _skill_level = user.profile.cooking_level
        except Exception:
            pass

        scored_search = []
        for recipe in keyword_recipes:
            try:
                score_data = recipe.calculate_recommendation_score(
                    user=user,
                    user_ingredient_ids=selected_ingredient_ids,
                    user_ingredients_dict=user_ingredients_dict,
                    user_skill_level=_skill_level,
                )
            except Exception:
                score_data = {
                    'total_score': 0,
                    'ingredient_score': 0,
                    'expiry_score': 0,
                    'difficulty_score': 0,
                    'personalization_score': 0,
                    'missing_ingredients_count': 0,
                }

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

            scored_search.append({
                'recipe_id': recipe.recipe_id,
                'title': recipe.get_display_title(),
                'title_ko': recipe.title_ko,
                'title_en': recipe.title,
                'image_url': recipe.image_url,
                'ready_minutes': recipe.ready_minutes,
                'difficulty': recipe.difficulty,
                'difficulty_display': recipe.get_difficulty_display() if hasattr(recipe, 'get_difficulty_display') else recipe.difficulty,
                'total_score': score_data['total_score'],
                'score_breakdown': score_data,
                'missing_ingredients_count': score_data.get('missing_ingredients_count', 0),
                'ingredients_status': {
                    'ingredients_status': status_info.get('ingredients_status', {}),
                    'has_expired': status_info.get('has_expired', False),
                    'has_urgent': status_info.get('has_urgent', False),
                },
                'expired_ingredients': status_info.get('expired_ingredients', []),
                'urgent_ingredients': status_info.get('urgent_ingredients', []),
                'is_favorited': False,
            })

        # 정렬: 재료 매칭 점수 높은 순 → 유통기한 점수 → 난이도
        # (55점 필터 없음 - 검색 결과는 모두 노출)
        scored_search.sort(key=lambda x: (
            -x['score_breakdown'].get('ingredient_score', 0),
            -x['score_breakdown'].get('expiry_score', 0),
            x['score_breakdown'].get('difficulty_score', 0),
        ))

        # 찜 상태 주입
        all_search_ids = [r['recipe_id'] for r in scored_search]
        favorited_set = set(FavoriteRecipe.objects.filter(
            user=user,
            recipe_id__in=all_search_ids
        ).values_list('recipe_id', flat=True))
        for r in scored_search:
            r['is_favorited'] = r['recipe_id'] in favorited_set

        logger.info(f"✅ [검색 모드 / 로그인] {len(scored_search)}개 반환")
        return Response({
            'recipes': scored_search,
            'total_count': len(scored_search),
            'search_mode': True
        })

    # ==========================================
    # 4. DB 검색 (utils.py 함수 사용) - 추천 모드 (검색어 없음)
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
    
    # ========== [수정] "내 재료만" 필터링 - calculate_final_recommendations 전에 적용 ==========
    if only_owned_ingredients and user and selected_ingredient_ids:
        logger.info("=" * 50)
        logger.info("🔒 '내 재료만' 필터 적용 시작")
        logger.info(f"🔒 보유 식재료 개수: {len(selected_ingredient_ids)}개")
        logger.info(f"🔒 보유 식재료 ID: {selected_ingredient_ids[:10]}..." if len(selected_ingredient_ids) > 10 else f"🔒 보유 식재료 ID: {selected_ingredient_ids}")
        
        owned_ingredient_ids = set(selected_ingredient_ids)
        filtered_recipes = []
        
        # Recipe 객체에서 필터링
        for idx, recipe in enumerate(final_list):
            try:
                # 필수 재료만 확인 (is_optional=False)
                required_ingredients = recipe.recipe_ingredients.filter(is_optional=False)
                required_ingredient_ids = set(
                    required_ingredients.values_list('ingredient_id', flat=True)
                )
                
                # None 제거
                required_ingredient_ids = {id for id in required_ingredient_ids if id is not None}
                
                if not required_ingredient_ids:
                    # 필수 재료가 없으면 모든 재료 확인
                    all_ingredients = recipe.recipe_ingredients.all()
                    required_ingredient_ids = set(
                        all_ingredients.values_list('ingredient_id', flat=True)
                    )
                    required_ingredient_ids = {id for id in required_ingredient_ids if id is not None}
                
                # 디버깅: 첫 5개만 상세 로그
                if idx < 5:
                    logger.info(f"  [{idx}] {recipe.get_display_title()[:30]}")
                    logger.info(f"       필수 재료: {required_ingredient_ids}")
                    logger.info(f"       보유 여부: {required_ingredient_ids.issubset(owned_ingredient_ids)}")
                
                # 모든 필수 재료를 보유하고 있는지 확인
                if required_ingredient_ids.issubset(owned_ingredient_ids):
                    filtered_recipes.append(recipe)
                    if idx < 5:
                        logger.info(f"       ✅ 포함")
                else:
                    missing = required_ingredient_ids - owned_ingredient_ids
                    if idx < 5:
                        logger.info(f"       ❌ 제외 (부족: {missing})")
            
            except Exception as e:
                logger.error(f"  ❌ [{idx}] 필터링 에러: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        logger.info(f"🔒 필터링 전: {len(final_list)}개")
        logger.info(f"🔒 필터링 후: {len(filtered_recipes)}개")
        logger.info("=" * 50)
        
        # 필터링된 레시피로 교체
        final_list = filtered_recipes
    
    # 이제 calculate_final_recommendations 호출
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
        recipe_id: 레시피 ID
        step: 현재 단계 번호 (URL parameter, optional)
    """
    try:
        recipe = Recipe.objects.get(recipe_id=recipe_id)
    except Recipe.DoesNotExist:
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
    try:
        recipe = Recipe.objects.prefetch_related(
            'recipe_ingredients__ingredient'
        ).get(recipe_id=recipe_id)
    except Recipe.DoesNotExist:
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