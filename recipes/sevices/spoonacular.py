import requests
from django.conf import settings

class SpoonacularService:
    """Spoonacular API 연동 서비스"""
    
    BASE_URL = "https://api.spoonacular.com/recipes"
    
    def __init__(self):
        # settings.py에 SPOONACULAR_API_KEY가 있어야 합니다.
        self.api_key = getattr(settings, 'SPOONACULAR_API_KEY', None)
        if not self.api_key:
            print("⚠️ Spoonacular API Key가 설정되지 않았습니다.")

    def search_recipes_by_ingredients(self, ingredients, number=10):
        """
        보유 식재료로 레시피 검색
        :param ingredients: 식재료 이름 리스트 (예: ['tomato', 'egg'])
        :param number: 가져올 결과 개수
        """
        if not self.api_key: return []

        url = f"{self.BASE_URL}/findByIngredients"
        params = {
            'apiKey': self.api_key,
            'ingredients': ','.join(ingredients),
            'number': number,
            'ranking': 1, # 1: 보유 재료 최대화, 2: 부족 재료 최소화
            'ignorePantry': True
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Spoonacular 검색 실패: {e}")
            return []

    def get_recipe_information(self, recipe_id):
        """레시피 상세 정보 조회"""
        if not self.api_key: return None

        url = f"{self.BASE_URL}/{recipe_id}/information"
        params = {
            'apiKey': self.api_key,
            'includeNutrition': False
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ 레시피 상세 조회 실패: {e}")
            return None

    def save_recipe_to_db(self, recipe_id):
        """API 레시피 정보를 가져와 DB에 저장"""
        from recipes.models import Recipe, RecipeSource, DifficultyLevel
        
        # 이미 저장된 레시피인지 확인
        existing = Recipe.objects.filter(external_id=str(recipe_id), source=RecipeSource.SPOONACULAR).first()
        if existing:
            return existing

        # API 호출
        data = self.get_recipe_information(recipe_id)
        if not data:
            return None

        # DB 저장 (필요한 필드만 매핑)
        try:
            recipe = Recipe.objects.create(
                external_id=str(data.get('id')),
                source=RecipeSource.SPOONACULAR,
                title=data.get('title'),
                image_url=data.get('image'),
                ready_minutes=data.get('readyInMinutes'),
                servings=data.get('servings'),
                raw_data=data,
                instructions=self._parse_instructions(data.get('analyzedInstructions', []))
            )
            # 난이도 자동 계산
            recipe.difficulty = recipe.calculate_difficulty()
            recipe.save()
            return recipe
        except Exception as e:
            print(f"❌ 레시피 DB 저장 실패: {e}")
            return None

    def _parse_instructions(self, analyzed_instructions):
        """Spoonacular 조리 단계를 JSON으로 변환"""
        if not analyzed_instructions:
            return []
        
        steps = analyzed_instructions[0].get('steps', [])
        return [{'step': s['number'], 'description': s['step']} for s in steps]