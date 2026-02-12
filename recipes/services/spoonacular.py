"""
Spoonacular API Service (번역 통합 버전)

주요 기능:
1. Spoonacular API에서 레시피 검색
2. 레시피 상세 정보 조회
3. 자동 한글 번역
4. DB 저장
"""
import requests
from django.conf import settings
from recipes.models import Recipe, RecipeIngredient
from ingredients.utils.mapper import IngredientMapper
from .translator import RecipeTranslator
import time


class SpoonacularService:
    """Spoonacular API 서비스 (번역 포함)"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'SPOONACULAR_API_KEY', '')
        self.base_url = 'https://api.spoonacular.com'
        self.translator = RecipeTranslator()
    
    def search_recipes(self, 
                      query=None,
                      cuisine=None,
                      diet=None,
                      intolerances=None,
                      ingredients=None,
                      number=10,
                      offset=0):
        """
        레시피 검색
        
        Args:
            query: 검색어
            cuisine: 요리 종류 (korean, italian, chinese 등)
            diet: 식단 유형 (vegetarian, vegan 등)
            intolerances: 알러지 (gluten, dairy 등)
            ingredients: 재료 목록
            number: 결과 개수
            offset: 페이지 오프셋
        
        Returns:
            레시피 목록
        """
        if not self.api_key:
            print("❌ SPOONACULAR_API_KEY가 설정되지 않았습니다.")
            return []
        
        url = f"{self.base_url}/recipes/complexSearch"
        
        params = {
            'apiKey': self.api_key,
            'number': number,
            'offset': offset,
            'addRecipeInformation': True,
            'fillIngredients': True
        }
        
        if query:
            params['query'] = query
        if cuisine:
            params['cuisine'] = cuisine
        if diet:
            params['diet'] = diet
        if intolerances:
            params['intolerances'] = intolerances
        if ingredients:
            if isinstance(ingredients, list):
                ingredients = ','.join(ingredients)
            params['includeIngredients'] = ingredients
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 402:
                print("❌ API 일일 사용량 초과 (402)")
                return []
            
            if response.status_code != 200:
                print(f"❌ API 오류: {response.status_code}")
                return []
            
            data = response.json()
            return data.get('results', [])
            
        except Exception as e:
            print(f"❌ 검색 실패: {str(e)}")
            return []
    
    def get_recipe_information(self, recipe_id):
        """
        레시피 상세 정보 조회
        
        Args:
            recipe_id: Spoonacular 레시피 ID
        
        Returns:
            레시피 상세 정보
        """
        url = f"{self.base_url}/recipes/{recipe_id}/information"
        
        params = {
            'apiKey': self.api_key,
            'includeNutrition': False
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                return None
            
            return response.json()
            
        except Exception as e:
            print(f"❌ 상세 조회 실패: {str(e)}")
            return None
    
    def save_recipe_to_db(self, recipe_data, translate=True):
        """
        레시피를 DB에 저장 (번역 포함)
        
        Args:
            recipe_data: Spoonacular API 응답 데이터
            translate: 한글 번역 여부 (기본 True)
        
        Returns:
            Recipe 객체
        """
        external_id = f"spoon_{recipe_data['id']}"
        
        # 중복 확인
        if Recipe.objects.filter(external_id=external_id).exists():
            print(f"⏭️  중복: {recipe_data.get('title')}")
            return None
        
        # 난이도 계산
        steps = recipe_data.get('analyzedInstructions', [])
        total_steps = sum(len(inst.get('steps', [])) for inst in steps)
        
        if total_steps <= 5:
            difficulty = 'EASY'
        elif total_steps <= 10:
            difficulty = 'NORMAL'
        else:
            difficulty = 'DIFFICULT'
        
        # 조리 단계 추출
        steps_data = []
        for instruction_group in steps:
            for step in instruction_group.get('steps', []):
                steps_data.append({
                    'step': step.get('number'),
                    'description': step.get('step'),
                    'image': None
                })
        
        # ============ 번역 (NEW!) ============
        title_ko = None
        is_translated = False
        
        if translate:
            print(f"🌐 번역 중: {recipe_data.get('title')}")
            try:
                translation = self.translator.translate_full_recipe({
                    'title': recipe_data.get('title'),
                    'instructions': steps_data  # ← 수정: steps_data를 직접 전달
                })
                
                title_ko = translation.get('title_ko')
                # [수정] translation['instructions']에 한글이 추가된 steps_data가 들어있음
                translated_steps = translation.get('instructions', steps_data)
                steps_data = translated_steps
                is_translated = True
                
                print(f"✅ 번역 완료: {title_ko}")
                
            except Exception as e:
                print(f"⚠️ 번역 실패: {str(e)}")
        
        # 레시피 생성 (Recipe 모델 필드에 맞게 수정)
        recipe = Recipe.objects.create(
            external_id=external_id,
            source='spoonacular',
            title=recipe_data.get('title'),
            title_ko=title_ko,
            instructions=steps_data,  # ← 수정: JSON 필드에 steps_data 저장
            is_translated=is_translated,
            image_url=recipe_data.get('image', ''),
            ready_minutes=recipe_data.get('readyInMinutes', 0),
            servings=recipe_data.get('servings', 4),
            difficulty=difficulty,
            raw_data=recipe_data,
            is_active=True
        )
        
        # 재료 저장
        self._save_recipe_ingredients(recipe, recipe_data)
        
        # [추가] 캐싱 필드 업데이트
        recipe.update_ingredient_counts()
        
        return recipe
    
    def _save_recipe_ingredients(self, recipe, recipe_data):
        """레시피 재료 저장 (RecipeIngredient 필드에 맞게 수정)"""
        # 이미 추가된 식재료 ID 추적 (중복 방지)
        added_ingredient_ids = set()
        
        for ingredient_data in recipe_data.get('extendedIngredients', []):
            # IngredientMapper로 매핑
            ing_name = ingredient_data.get('name', '')
            ing_master = IngredientMapper.find_ingredient(ing_name)
            
            if ing_master:
                # 중복 체크
                if ing_master.ingredient_id in added_ingredient_ids:
                    continue
                
                # get_or_create로 안전하게 생성
                RecipeIngredient.objects.get_or_create(
                    recipe=recipe,
                    ingredient=ing_master,
                    defaults={
                        'ingredient_name': ingredient_data.get('original', ing_name),
                        'is_optional': False
                    }
                )
                
                # 추가된 식재료 ID 기록
                added_ingredient_ids.add(ing_master.ingredient_id)
    
    def fetch_and_save_recipes(self, 
                               cuisine='korean',
                               limit=50,
                               translate=True,
                               delay=0.5):
        """
        레시피 일괄 수집 및 저장 (번역 포함)
        
        Args:
            cuisine: 요리 종류
            limit: 수집 개수
            translate: 번역 여부
            delay: API 호출 간격 (초)
        
        Returns:
            (수집된 개수, 중복 개수, 오류 개수)
        """
        collected = 0
        skipped = 0
        errors = 0
        
        print(f"🔍 {cuisine} 레시피 수집 시작 (최대 {limit}개)")
        
        for offset in range(0, limit, 10):
            # 검색
            results = self.search_recipes(
                cuisine=cuisine,
                number=min(10, limit - collected),
                offset=offset
            )
            
            if not results:
                break
            
            for recipe_data in results:
                try:
                    # 상세 정보 조회
                    detail = self.get_recipe_information(recipe_data['id'])
                    
                    if not detail:
                        errors += 1
                        continue
                    
                    # DB 저장 (번역 포함)
                    recipe = self.save_recipe_to_db(detail, translate=translate)
                    
                    if recipe:
                        collected += 1
                        display_title = recipe.get_display_title()
                        print(f"✅ [{collected}] {display_title}")
                    else:
                        skipped += 1
                    
                    # API 제한 방지
                    time.sleep(delay)
                    
                except Exception as e:
                    errors += 1
                    print(f"❌ 오류: {str(e)}")
                    continue
            
            # 페이지 단위 대기
            if collected < limit:
                time.sleep(2)
        
        print(f"\n✨ 완료! 수집: {collected}개 / 중복: {skipped}개 / 오류: {errors}개")
        
        return collected, skipped, errors


# ============ 편의 함수 ============

def search_and_save_recipes(cuisine='korean', limit=50, translate=True):
    """레시피 검색 및 저장 (편의 함수)"""
    service = SpoonacularService()
    return service.fetch_and_save_recipes(
        cuisine=cuisine,
        limit=limit,
        translate=translate
    )