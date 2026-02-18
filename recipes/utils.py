from django.db.models import Q, Count
from .models import Recipe
import requests
from django.conf import settings

# =========================================================
# 1. DB 검색 (알러지 이름 필터링 추가)
# =========================================================
def search_recipes_from_db(user_ingredient_ids, user, exclude_allergies=True):
    """
    DB에서 레시피 검색 (한식 + 기존 저장된 레시피)
    """
    # 1. 사용자 재료 ID 정리 (우유 같은 문자열 에러 방지)
    valid_ids = []
    if user_ingredient_ids:
        for i in user_ingredient_ids:
            try:
                valid_ids.append(int(i))
            except (ValueError, TypeError):
                continue
    
    recipes = Recipe.objects.filter(is_active=True)
    
    # 2. 알러지/제한 식재료 제외 (여기가 문제였던 부분!)
    if exclude_allergies and user and hasattr(user, 'profile'):
        profile = user.profile
        banned_ingredients = []
        
        # 프로필에서 알러지 정보 가져오기
        if profile.allergies:
            banned_ingredients.extend(profile.allergies)
        
        if profile.banned_ingredients:
            banned_ingredients.extend(profile.banned_ingredients)
        
        if banned_ingredients:
            # 알러지 목록에 '숫자(ID)'와 '문자(이름)'이 섞여 있을 수 있음
            banned_ids = []
            banned_names = []
            
            for item in banned_ingredients:
                if isinstance(item, int):
                    banned_ids.append(item)
                elif isinstance(item, str):
                    if item.isdigit(): # "123" 같은 숫자형 문자
                        banned_ids.append(int(item))
                    else: # "우유", "땅콩" 같은 이름
                        banned_names.append(item)
            
            # ID로 제외
            if banned_ids:
                recipes = recipes.exclude(
                    recipe_ingredients__ingredient_id__in=banned_ids
                )
            
            # [핵심 수정] 이름(글자)으로 제외
            if banned_names:
                recipes = recipes.exclude(
                    recipe_ingredients__ingredient__name_ko__in=banned_names
                )
    
    # 3. 재료 매칭
    if valid_ids:
        recipes = recipes.filter(
            recipe_ingredients__ingredient_id__in=valid_ids
        ).annotate(
            matching_count=Count('recipe_ingredients', filter=Q(
                recipe_ingredients__ingredient_id__in=valid_ids
            ))
        ).order_by('-matching_count')
    
    return recipes.distinct().prefetch_related('recipe_ingredients__ingredient')[:50]


# =========================================================
# 2. Spoonacular 검색 (안전한 버전)
# =========================================================
def search_recipes_from_spoonacular(user_ingredients, max_results=10):
    """
    Spoonacular API에서 레시피 검색 (402 에러 방어 포함 + 자동 번역)
    """
    api_key = getattr(settings, 'SPOONACULAR_API_KEY', '')
    if not api_key:
        return []

    # 식재료 이름을 영어로 변환 (영문명 있는 것만)
    ingredient_names = []
    for ui in user_ingredients:
        if ui.ingredient.name_en:
            ingredient_names.append(ui.ingredient.name_en)
    
    if not ingredient_names:
        return []

    # API 호출
    ingredients_str = ','.join(ingredient_names[:5])
    url = f'https://api.spoonacular.com/recipes/findByIngredients'
    
    params = {
        'apiKey': api_key,
        'ingredients': ingredients_str,
        'number': max_results,
        'ranking': 2,
        'ignorePantry': 'true'
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        
        # [402 에러 처리] 한도 초과 시 빈 리스트 반환
        if response.status_code == 402:
            print("❌ Spoonacular API 일일 사용량 초과 (402)")
            return []
            
        if response.status_code != 200:
            print(f"❌ Spoonacular API 오류: {response.status_code}")
            return []
            
        data = response.json()
        
        # ========== [추가] 번역 서비스 import ==========
        from recipes.services.translator import RecipeTranslator
        translator = RecipeTranslator()
        
        # 데이터를 Recipe 모델 형식의 임시 객체로 변환
        results = []
        for item in data:
            title_en = item.get('title', '')
            external_id = str(item.get('id'))
            
            # ========== [추가] DB에 이미 번역된 레시피가 있는지 확인 (캐싱) ==========
            cached_recipe = Recipe.objects.filter(
                external_id=external_id,
                source='spoonacular',
                is_translated=True
            ).first()
            
            if cached_recipe and cached_recipe.title_ko:
                # 캐시된 번역 사용 (DB 조회)
                title_ko = cached_recipe.title_ko
                # 로그 제거 (속도 향상)
            else:
                # 새로 번역
                title_ko = ''
                try:
                    if title_en:
                        title_ko = translator.translate_text(title_en)
                        # 로그 제거 (속도 향상)
                except Exception as e:
                    # 에러만 출력
                    print(f"   ⚠️ 번역 실패: {e}")
                    title_ko = title_en  # 번역 실패 시 원문 사용
            
            recipe = Recipe(
                title=title_en,  # 영문 제목
                title_ko=title_ko,  # 한글 제목
                image_url=item.get('image'),
                ready_minutes=0, 
                difficulty='NORMAL',
                external_id=external_id,
                is_translated=bool(title_ko and title_ko != title_en)
            )
            recipe.recipe_id = -item.get('id') 
            results.append(recipe)
            
        return results
        
    except Exception as e:
        print(f"⚠️ Spoonacular 연결 실패: {e}")
        return []


# =========================================================
# 3. 점수 계산 (원래 로직 유지)
# =========================================================
def calculate_final_recommendations(recipes, user, user_ingredients_dict, user_skill_level, min_score=55):
    """
    레시피 추천 점수 계산 및 정렬
    """
    user_ingredient_ids = list(user_ingredients_dict.keys())
    
    scored_recipes = []
    
    for recipe in recipes:
        try:
            score_data = recipe.calculate_recommendation_score(
                user=user,
                user_ingredient_ids=user_ingredient_ids,
                user_ingredients_dict=user_ingredients_dict,
                user_skill_level=user_skill_level
            )
        except AttributeError:
            score_data = {
                'total_score': 50, 'expiry_score': 0, 
                'difficulty_score': 0, 'personalization_score': 0, 
                'ingredient_score': 0, 'missing_ingredients_count': 0
            }

        # ============ 개선: min_score 파라미터 사용 (기본값 55) ============
        if score_data['total_score'] >= min_score:
            scored_recipes.append({
                'recipe': recipe,
                'score_data': score_data
            })
    
    # 정렬: 총점 → 유통기한 점수 → 난이도
    scored_recipes.sort(
        key=lambda x: (
            -x['score_data']['total_score'],
            -x['score_data']['expiry_score'],
            x['score_data']['difficulty_score'],  # 난이도는 낮을수록 좋음
            -x['score_data']['ingredient_score']
        )
    )
    
    categories = {
        'urgent_ready': {'label': '유통기한 임박 레시피', 'recipes': [], 'count': 0},
        'ready': {'label': '지금 바로 만들 수 있어요', 'recipes': [], 'count': 0},
        'almost_ready': {'label': '재료 1-2개만 있으면 가능해요', 'recipes': [], 'count': 0}
    }
    
    for item in scored_recipes:
        recipe = item['recipe']
        score_data = item['score_data']
        
        try:
            category = recipe.get_recommendation_category(score_data['total_score'])
            status_info = recipe.get_ingredients_status_for_user(user_ingredients_dict)
        except AttributeError:
            category = 'ready'
            status_info = {'has_expired': False, 'has_urgent': False, 'ingredients_status': {}, 'expired_ingredients': [], 'urgent_ingredients': []}

        if category in categories:
            # ========== [수정] 한글 제목 우선 표시 ==========
            recipe_data = {
                'recipe_id': recipe.recipe_id,
                'title': recipe.get_display_title(),  # ✅ 한글 우선
                'title_ko': recipe.title_ko,  # 추가: 한글 제목
                'title_en': recipe.title,  # 추가: 영문 제목
                'image_url': recipe.image_url,
                'ready_minutes': recipe.ready_minutes,
                'difficulty': recipe.difficulty,
                'difficulty_display': getattr(recipe, 'get_difficulty_display', lambda: recipe.difficulty)(),
                'total_score': score_data['total_score'],
                'score_breakdown': score_data,
                'missing_ingredients_count': score_data.get('missing_ingredients_count', 0),
                'ingredients_status': {
                    'ingredients_status': status_info.get('ingredients_status', {}), 
                    'has_expired': status_info.get('has_expired', False),
                    'has_urgent': status_info.get('has_urgent', False)
                },
                'expired_ingredients': status_info.get('expired_ingredients', []),
                'urgent_ingredients': status_info.get('urgent_ingredients', []),
                'is_favorited': False
            }
            
            categories[category]['recipes'].append(recipe_data)
            categories[category]['count'] += 1
    
    total_count = sum(cat['count'] for cat in categories.values())
    
    return {
        'categories': categories,
        'total_count': total_count
    }