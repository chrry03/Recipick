from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.db.models import Q, Prefetch, Count
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import Recipe, RecipeIngredient
from ingredients.models import UserIngredient, IngredientMaster
from .serializers import RecipeListSerializer, RecipeDetailSerializer
from ingredients.utils.mapper import IngredientMapper


# ==================== 템플릿 뷰 (HTML 페이지) ==================== #

def recipe_list_view(request):
    """레시피 목록 페이지"""
    return render(request, 'recipes/recipe_list.html')


def recipe_detail_view(request, recipe_id):
    """레시피 상세 페이지"""
    recipe = get_object_or_404(Recipe, recipe_id=recipe_id)
    return render(request, 'recipes/recipe_detail.html', {
        'recipe': recipe
    })



def cooking_mode_view(request, recipe_id, step=1):
    """요리 모드 페이지 (단계별) - 테스트용 더미 데이터"""
    # 테스트용 더미 데이터
    test_recipe = {
        'recipe_id': recipe_id,
        'title': '로제 파스타',
        'image_url': '/static/images/ex/pasta.png',
        'instructions': [
            {"step": 1, "description": "물에 소금 넉넉히 넣고 면 삶기(8분)"},
            {"step": 2, "description": "팬에 올리브유 두르고 마늘, 양파, 베이컨 순으로 볶기"},
            {"step": 3, "description": "토마토소스 넣고 2분 끓인 뒤 생크림 넣고 잘 섞기"},
            {"step": 4, "description": "면 넣고 센 불에서 빠르게 섞어 소금·후추로 간 맞추기"},
        ]
    }
    
    instructions = test_recipe['instructions']
    total_steps = len(instructions)
    current_step_data = None
    if instructions and 1 <= step <= total_steps:
        current_step_data = instructions[step - 1]
    
    # 레시피 객체처럼 사용할 수 있도록 속성 추가
    class RecipeObj:
        def __init__(self, data):
            self.recipe_id = data['recipe_id']
            self.title = data['title']
            self.image_url = data.get('image_url')
    
    recipe_obj = RecipeObj(test_recipe)
    
    return render(request, 'recipes/cooking_mode.html', {
        'recipe': recipe_obj,
        'current_step': step,
        'total_steps': total_steps,
        'step_data': current_step_data,
        'instructions': instructions,
    })


def cooking_complete_view(request, recipe_id):
    """요리 완료 페이지 - 테스트용 더미 데이터"""
    # 테스트용 더미 데이터
    test_recipe = {
        'recipe_id': recipe_id,
        'title': '로제 파스타',
        'image_url': '/static/images/ex/pasta.png',
    }
    
    # 테스트용 재료 데이터
    test_ingredients = [
        {'id': 1, 'name': '스파게티 면'},
        {'id': 2, 'name': '토마토소스'},
        {'id': 3, 'name': '생크림'},
        {'id': 4, 'name': '베이컨'},
        {'id': 5, 'name': '양파'},
        {'id': 6, 'name': '마늘'},
    ]
    
    # 레시피 객체처럼 사용할 수 있도록 속성 추가
    class RecipeObj:
        def __init__(self, data):
            self.recipe_id = data['recipe_id']
            self.title = data['title']
            self.image_url = data.get('image_url')
    
    recipe_obj = RecipeObj(test_recipe)
    
    return render(request, 'recipes/cooking_complete.html', {
        'recipe': recipe_obj,
        'ingredients': test_ingredients,
    })




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
    
    if use_all:
        selected_ingredients = user_ingredients
    elif ingredient_ids:
        selected_ingredients = user_ingredients.filter(user_ingredient_id__in=ingredient_ids)
    else:
        selected_ingredients = user_ingredients
    
    if not selected_ingredients.exists():
        return Response({
            'message': '선택된 식재료가 없습니다',
            'recipes': []
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 식재료 ID 리스트 & 딕셔너리
    selected_ingredient_ids = list(selected_ingredients.values_list('ingredient_id', flat=True))
    user_ingredients_dict = {ui.ingredient_id: ui for ui in selected_ingredients}
    
    # 1. DB 검색
    db_recipes = search_recipes_from_db(selected_ingredient_ids, user)
    
    # 2. Spoonacular 검색
    spoon_recipes = []
    if include_spoonacular:
        spoon_recipes = search_recipes_from_spoonacular(selected_ingredients, max_results=10)
    
    # 3. 통합 및 중복 제거
    all_recipes = list(db_recipes) + spoon_recipes
    unique_recipes = {}
    for recipe in all_recipes:
        if recipe.external_id not in unique_recipes:
            unique_recipes[recipe.external_id] = recipe
    
    # 4. 점수 계산
    scored_recipes = []
    # 사용자 스킬 레벨 가져오기 로직 (간소화)
    user_skill_level = getattr(user, 'skill_level', 'INTERMEDIATE')
    if hasattr(user, 'profile'):
        user_skill_level = getattr(user.profile, 'cooking_level', 'INTERMEDIATE')

    for recipe in unique_recipes.values():
        score_data = recipe.calculate_recommendation_score(
            user=user,
            user_ingredient_ids=selected_ingredient_ids,
            user_ingredients_dict=user_ingredients_dict,
            user_skill_level=user_skill_level
        )
        
        if score_data['total_score'] >= 60:
            scored_recipes.append({'recipe': recipe, 'score_data': score_data})
    
    # 5. 정렬 & 제한
    scored_recipes.sort(key=lambda x: x['score_data']['total_score'], reverse=True)
    scored_recipes = scored_recipes[:max_results]
    
    # 6. 카테고리 분류 및 데이터 구성
    categorized = {
        'urgent_ready': [],
        'ready': [],
        'almost_ready': [],
    }
    
    for item in scored_recipes:
        recipe = item['recipe']
        score_data = item['score_data']
        category = recipe.get_recommendation_category(score_data['total_score'])
        
        # 기본 데이터 변환
        recipe_data = RecipeListSerializer(recipe).data
        recipe_data['recommendation_score'] = score_data
        
        # [핵심] 재료 상태 정보 추가 (이게 있어야 JS가 김치, 양파를 보여줍니다)
        recipe_data['ingredients_status'] = recipe.get_ingredients_status_for_user(user_ingredients_dict)
        
        if category in categorized:
            categorized[category].append(recipe_data)
    
    return Response({
        'message': '레시피 추천 완료',
        'total_count': len(scored_recipes),
        'selected_ingredients_count': len(selected_ingredient_ids),
        'categories': {
            'urgent_ready': {
                'label': '지금 바로 만들 수 있어요! (유통기한 임박)',
                'count': len(categorized['urgent_ready']),
                'recipes': categorized['urgent_ready']
            },
            'ready': {
                'label': '지금 바로 만들 수 있어요!',
                'count': len(categorized['ready']),
                'recipes': categorized['ready']
            },
            'almost_ready': {
                'label': '재료 1~2개만 있으면 가능해요',
                'count': len(categorized['almost_ready']),
                'recipes': categorized['almost_ready']
            }
        }
    })


def search_recipes_from_db(ingredient_ids, user):
    """
    DB에서 레시피 검색
    - 한식 DB + 이전에 저장된 Spoonacular 레시피
    """
    # 사용자의 알러지/제한 식재료
    excluded_ingredients = []
    if hasattr(user, 'allergies') and user.allergies:
        excluded_ingredients.extend(user.allergies)
    if hasattr(user, 'dietary_restrictions') and user.dietary_restrictions:
        excluded_ingredients.extend(user.dietary_restrictions)
    if hasattr(user, 'profile'):
        if hasattr(user.profile, 'allergies') and user.profile.allergies:
            excluded_ingredients.extend(user.profile.allergies)
        if hasattr(user.profile, 'banned_ingredients') and user.profile.banned_ingredients:
            excluded_ingredients.extend(user.profile.banned_ingredients)
    
    # 기본 쿼리
    recipes = Recipe.objects.prefetch_related(
        Prefetch(
            'recipe_ingredients',
            queryset=RecipeIngredient.objects.select_related('ingredient')
        )
    ).filter(
        recipe_ingredients__ingredient_id__in=ingredient_ids
    ).distinct()
    
    # 알러지 식재료 제외
    if excluded_ingredients:
        recipes = recipes.exclude(
            recipe_ingredients__ingredient_id__in=excluded_ingredients
        )
    
    # 매칭 개수로 정렬 (보유 재료를 많이 사용하는 순)
    recipes = recipes.annotate(
        matching_count=Count('recipe_ingredients', filter=Q(
            recipe_ingredients__ingredient_id__in=ingredient_ids
        ))
    ).order_by('-matching_count')
    
    return recipes[:50]  # 최대 50개


def search_recipes_from_spoonacular(user_ingredients, max_results=10):
    """
    Spoonacular API에서 레시피 검색
    """
    try:
        from .services.spoonacular import SpoonacularService
        service = SpoonacularService()
    except (ValueError, ImportError) as e:
        # API 키가 없거나 서비스 로드 실패 시 빈 리스트 반환
        print(f"Spoonacular 서비스 로드 실패: {e}")
        return []
    
    # 식재료 이름을 영어로 변환
    ingredient_names = []
    
    for ui in user_ingredients:
        ing_name = ui.ingredient.name_ko
        
        # 한글 -> 영어 매핑
        eng_name = None
        for eng, kor in IngredientMapper.BASE_MAPPINGS.items():
            if kor == ing_name:
                eng_name = eng
                break
        
        if eng_name:
            ingredient_names.append(eng_name)
        else:
            # 매핑이 없으면 name_en 사용
            if ui.ingredient.name_en:
                ingredient_names.append(ui.ingredient.name_en)
    
    if not ingredient_names:
        return []
    
    # API 호출
    try:
        search_results = service.search_recipes_by_ingredients(
            ingredients=ingredient_names[:5],  # 최대 5개 재료
            number=max_results
        )
    except Exception as e:
        print(f"Spoonacular API 검색 실패: {e}")
        return []
    
    # 결과에서 레시피 ID 추출
    recipe_ids = [r['id'] for r in search_results]
    
    # 각 레시피를 DB에 저장하고 반환
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


@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def search_recipes(request):
    """
    레시피 검색 (키워드)
    
    GET /api/recipes/api/search/?q=김치볶음밥
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        return Response({
            'message': '검색어를 입력해주세요',
            'recipes': []
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # DB에서 검색 (title 필드 사용)
    recipes = Recipe.objects.filter(
        Q(title__icontains=query)  # ← name이 아닌 title
    ).prefetch_related(
        'recipe_ingredients__ingredient'
    )[:20]
    
    serializer = RecipeListSerializer(recipes, many=True)
    
    return Response({
        'message': '검색 완료',
        'count': recipes.count(),
        'recipes': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def recipe_list(request):
    """레시피 목록 조회 API"""
    recipes = Recipe.objects.all().prefetch_related(
        'recipe_ingredients__ingredient'
    )[:20]
    
    serializer = RecipeListSerializer(recipes, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def recipe_detail(request, recipe_id):
    """레시피 상세 조회 API"""
    recipe = get_object_or_404(
        Recipe.objects.prefetch_related('recipe_ingredients__ingredient'),
        recipe_id=recipe_id
    )
    
    serializer = RecipeDetailSerializer(recipe)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_favorite(request, recipe_id):
    """레시피 찜하기/취소 API"""
    recipe = get_object_or_404(Recipe, recipe_id=recipe_id)
    user = request.user
    
    # 찜 토글 로직 (추후 구현)
    # FavoriteRecipe 모델 필요
    
    return Response({
        'message': '찜하기 기능은 추후 구현 예정입니다'
    })