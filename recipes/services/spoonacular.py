import requests
from django.conf import settings
from django.core.cache import cache
import json
import re


class SpoonacularService:
    """Spoonacular API 연동 서비스"""
    
    BASE_URL = 'https://api.spoonacular.com'
    
    def __init__(self):
        self.api_key = settings.SPOONACULAR_API_KEY
        if not self.api_key:
            raise ValueError("SPOONACULAR_API_KEY가 설정되지 않았습니다.")
    
    def search_recipes_by_ingredients(self, ingredients, number=10):
        """
        재료 기반 레시피 검색
        
        Args:
            ingredients: 재료 이름 리스트 (영어)
            number: 결과 개수
        
        Returns:
            레시피 목록
        """
        # 캐시 키 생성
        cache_key = f"spoon_search_{'_'.join(sorted(ingredients))}_{number}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            print(f"✓ 캐시에서 레시피 검색 결과 반환: {cache_key}")
            return cached_result
        
        # API 호출
        url = f"{self.BASE_URL}/recipes/findByIngredients"
        params = {
            'apiKey': self.api_key,
            'ingredients': ','.join(ingredients),
            'number': number,
            'ranking': 2,  # Maximize used ingredients
            'ignorePantry': True
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            results = response.json()
            
            # 캐시 저장 (30분)
            cache.set(cache_key, results, 60 * 30)
            
            print(f"✓ Spoonacular API: {len(results)}개 레시피 검색 성공")
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Spoonacular API 검색 실패: {e}")
            return []
    
    def get_recipe_information(self, recipe_id):
        """
        레시피 상세 정보 조회
        
        Args:
            recipe_id: Spoonacular 레시피 ID
        
        Returns:
            레시피 상세 정보
        """
        # 캐시 키
        cache_key = f"spoon_recipe_{recipe_id}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            print(f"✓ 캐시에서 레시피 상세 반환: {recipe_id}")
            return cached_result
        
        # API 호출
        url = f"{self.BASE_URL}/recipes/{recipe_id}/information"
        params = {
            'apiKey': self.api_key,
            'includeNutrition': True
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            # 캐시 저장 (1시간)
            cache.set(cache_key, result, 60 * 60)
            
            print(f"✓ Spoonacular API: 레시피 {recipe_id} 상세 조회 성공")
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Spoonacular API 상세 조회 실패: {e}")
            return None
    
    def save_recipe_to_db(self, recipe_id):
        """
        Spoonacular 레시피를 DB에 저장
        
        Args:
            recipe_id: Spoonacular 레시피 ID
        
        Returns:
            Recipe 객체 또는 None
        """
        from recipes.models import Recipe, RecipeIngredient
        from ingredients.models import IngredientMaster
        from ingredients.utils.mapper import IngredientMapper
        
        # 이미 DB에 있는지 확인
        try:
            existing_recipe = Recipe.objects.get(external_id=f"spoonacular_{recipe_id}")
            print(f"✓ 레시피 {recipe_id}는 이미 DB에 존재")
            return existing_recipe
        except Recipe.DoesNotExist:
            pass
        
        # API에서 상세 정보 가져오기
        recipe_data = self.get_recipe_information(recipe_id)
        if not recipe_data:
            return None
        
        # Recipe 객체 생성
        recipe = Recipe(
            external_id=f"spoonacular_{recipe_id}",
            title=recipe_data.get('title', 'Unknown Recipe'),  # ← name이 아닌 title
            image_url=recipe_data.get('image', ''),
            source='spoonacular',
            ready_minutes=recipe_data.get('readyInMinutes', 0),  # ← cooking_time이 아닌 ready_minutes
            servings=recipe_data.get('servings', 1),
        )
        
        # 난이도 자동 계산
        recipe.difficulty = self._estimate_difficulty(recipe_data)  # ← difficulty_level이 아닌 difficulty
        
        # 조리 단계 추출
        instructions = self._extract_instructions(recipe_data)
        recipe.instructions = instructions  # JSON 필드라서 자동 변환
        
        recipe.save()
        
        # 재료 매핑 및 저장
        for ingredient_data in recipe_data.get('extendedIngredients', []):
            ing_name = ingredient_data.get('name', '')
            
            # 식재료 매핑
            ingredient = IngredientMapper.find_ingredient(ing_name)
            
            if ingredient:
                RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredient=ingredient,
                    ingredient_name=ingredient_data.get('original', ing_name),
                    is_optional=False
                )
            else:
                print(f"⚠️  '{ing_name}' 식재료를 찾을 수 없음")
        
        # 재료 개수 업데이트
        recipe.update_ingredient_counts()
        
        print(f"✓ 레시피 {recipe_id} DB 저장 완료: {recipe.title}")
        return recipe
    
    def _clean_html(self, html_text):
        """HTML 태그 제거"""
        if not html_text:
            return ''
        # HTML 태그 제거
        clean_text = re.sub(r'<[^>]+>', '', html_text)
        # 엔티티 변환
        clean_text = clean_text.replace('&nbsp;', ' ')
        clean_text = clean_text.replace('&amp;', '&')
        return clean_text.strip()
    
    def _extract_instructions(self, recipe_data):
        """조리 단계 추출"""
        instructions = []
        
        # analyzedInstructions 사용
        analyzed = recipe_data.get('analyzedInstructions', [])
        if analyzed and len(analyzed) > 0:
            steps = analyzed[0].get('steps', [])
            for step in steps:
                instructions.append({
                    'step': step.get('number', 0),
                    'description': step.get('step', '')  # ← text가 아닌 description
                })
        else:
            # instructions 필드 사용 (HTML 형식)
            raw_instructions = recipe_data.get('instructions', '')
            if raw_instructions:
                clean_instructions = self._clean_html(raw_instructions)
                # 문장 단위로 분리
                sentences = clean_instructions.split('.')
                for i, sentence in enumerate(sentences, 1):
                    sentence = sentence.strip()
                    if sentence:
                        instructions.append({
                            'step': i,
                            'description': sentence
                        })
        
        return instructions
    
    def _estimate_difficulty(self, recipe_data):
        """난이도 추정 (DifficultyLevel enum 반환)"""
        from recipes.models import DifficultyLevel
        
        # 조리 시간과 재료 개수로 추정
        cooking_time = recipe_data.get('readyInMinutes', 0)
        ingredient_count = len(recipe_data.get('extendedIngredients', []))
        
        if cooking_time <= 20 and ingredient_count <= 5:
            return DifficultyLevel.EASY
        elif cooking_time <= 40 and ingredient_count <= 10:
            return DifficultyLevel.NORMAL
        else:
            return DifficultyLevel.DIFFICULT