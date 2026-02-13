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
        
        # API 키 확인
        if self.api_key:
            print(f"✅ Spoonacular API 키 로드됨 (길이: {len(self.api_key)})")
        else:
            print("⚠️  Spoonacular API 키가 설정되지 않았습니다!")
            print("💡 settings.py에 SPOONACULAR_API_KEY를 추가하거나")
            print("💡 .env 파일에 SPOONACULAR_API_KEY=your_key를 추가하세요.")
    
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
            print("💡 .env 파일에 SPOONACULAR_API_KEY=your_key 를 추가하세요.")
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
            print(f"🌐 API 호출 중... (cuisine={cuisine}, offset={offset}, number={number})")
            response = requests.get(url, params=params, timeout=10)
            
            print(f"📡 응답 코드: {response.status_code}")
            
            if response.status_code == 402:
                print("❌ API 일일 사용량 초과 (402)")
                print("💡 내일 다시 시도하거나 유료 플랜을 구독하세요.")
                return []
            
            if response.status_code != 200:
                print(f"❌ API 오류: {response.status_code}")
                print(f"📄 응답 내용: {response.text[:200]}")
                return []
            
            data = response.json()
            results = data.get('results', [])
            total_results = data.get('totalResults', 0)
            
            print(f"✅ API 성공: {len(results)}개 레시피 반환 (전체: {total_results}개)")
            
            return results
            
        except Exception as e:
            print(f"❌ 검색 실패: {str(e)}")
            import traceback
            traceback.print_exc()
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
        """
        레시피 재료 저장 (자동 생성 포함 + 한글 번역 + 정규화 + 중복 방지)
        
        개선사항:
        1. 수량 표현 제거 ("5 pieces chicken" → "chicken")
        2. 한글 번역 (RecipeTranslator 사용)
        3. 번역된 이름으로도 중복 검사
        4. IngredientMapper + 전체 DB 검색
        5. Spoonacular 전용 카테고리 사용
        """
        # 이미 추가된 식재료 ID 추적 (중복 방지)
        added_ingredient_ids = set()
        created_count = 0
        
        # Spoonacular API 카테고리 ID 가져오기
        spoon_category_id = self._get_spoonacular_category_id()
        
        for ingredient_data in recipe_data.get('extendedIngredients', []):
            # 원본 이름
            ing_name_raw = ingredient_data.get('name', '')
            if not ing_name_raw:
                continue
            
            # ============ 1. 수량 표현 제거 ============
            ing_name_clean = self._clean_ingredient_name(ing_name_raw)
            
            # ============ 2. IngredientMapper로 영문명 매핑 시도 ============
            ing_master = IngredientMapper.find_ingredient(ing_name_clean)
            
            # ============ 3. 한글 번역 + 정리 ============
            if not ing_master:
                # [3-1] 번역
                ing_name_ko_raw = self._translate_ingredient_name(ing_name_clean)
                
                # [3-2] 번역 결과 정리 (핵심!)
                ing_name_ko = self._clean_translated_name(ing_name_ko_raw, ing_name_clean)
                
                # [4] 정리된 이름으로 검색 (중복 방지)
                if ing_name_ko and ing_name_ko != ing_name_clean:
                    # [4-1] IngredientMapper로 한글명 매핑
                    ing_master = IngredientMapper.find_ingredient(ing_name_ko)
                    
                    # [4-2] 전체 DB에서 한글명 검색
                    if not ing_master:
                        from ingredients.models import IngredientMaster
                        ing_master = IngredientMaster.objects.filter(
                            name_ko=ing_name_ko
                        ).first()
            
            # ============ 5. ingredients.json에 없으면 자동 생성 ============
            if not ing_master:
                # [5-1] 한글 번역 + 정리 (아직 안 했으면)
                if 'ing_name_ko' not in locals() or not ing_name_ko:
                    ing_name_ko_raw = self._translate_ingredient_name(ing_name_clean)
                    ing_name_ko = self._clean_translated_name(ing_name_ko_raw, ing_name_clean)
                
                print(f"   ➕ 식재료 자동 생성: {ing_name_raw} → {ing_name_ko}")
                
                try:
                    # Spoonacular 전용 카테고리에 생성
                    from ingredients.models import IngredientMaster, IngredientCategory
                    
                    # 카테고리 가져오기
                    category = IngredientCategory.objects.get(category_id=spoon_category_id)
                    
                    # [최종 중복 확인] 한글명 또는 영문명
                    existing = IngredientMaster.objects.filter(
                        name_ko=ing_name_ko
                    ).first() or IngredientMaster.objects.filter(
                        name_en__iexact=ing_name_clean
                    ).first()
                    
                    if existing:
                        ing_master = existing
                        print(f"     ✅ 기존 식재료 사용: {existing.name_ko} (ID: {existing.ingredient_id})")
                    else:
                        # 새로 생성
                        ing_master = IngredientMaster.objects.create(
                            category=category,
                            name_ko=ing_name_ko,
                            name_en=ing_name_clean,
                            aliases=[]
                        )
                        created_count += 1
                        print(f"     ✅ 생성 완료: {ing_name_ko} (ID: {ing_master.ingredient_id})")
                        
                except Exception as e:
                    print(f"   ❌ 생성 실패: {ing_name_clean} - {str(e)}")
                    continue
            
            if ing_master:
                # 중복 체크
                if ing_master.ingredient_id in added_ingredient_ids:
                    continue
                
                # get_or_create로 안전하게 생성
                RecipeIngredient.objects.get_or_create(
                    recipe=recipe,
                    ingredient=ing_master,
                    defaults={
                        'ingredient_name': ingredient_data.get('original', ing_name_raw),
                        'is_optional': False
                    }
                )
                
                # 추가된 식재료 ID 기록
                added_ingredient_ids.add(ing_master.ingredient_id)
        
        if created_count > 0:
            print(f"   ✨ 새 식재료 {created_count}개 자동 생성됨")
    
    def _get_spoonacular_category_id(self):
        """Spoonacular API 카테고리 ID 가져오기 (고정: 17번)"""
        from ingredients.models import IngredientCategory
        
        # Spoonacular API 카테고리 찾기 (pk=17)
        category = IngredientCategory.objects.filter(pk=17).first()
        
        if not category:
            # fixtures에 없으면 생성 (비상 대비)
            category, created = IngredientCategory.objects.get_or_create(
                name='Spoonacular API',
                defaults={
                    'icon': '🌐',
                    'parent': None,
                    'is_parent': False
                }
            )
            if created:
                print(f"   🆕 Spoonacular API 카테고리 생성 (ID: {category.category_id})")
        
        return category.category_id
    
    def _clean_ingredient_name(self, name):
        """
        식재료 이름 정규화 (수량 표현 제거)
        
        예시:
        - "5 pieces chicken breasts" → "chicken breasts"
        - "2 cups rice" → "rice"
        - "1 tablespoon soy sauce" → "soy sauce"
        """
        import re
        
        # 패턴: 숫자 + 단위 제거
        patterns = [
            r'^\d+(\.\d+)?\s*(piece|pieces|cup|cups|tablespoon|tablespoons|teaspoon|teaspoons|'
            r'tbsp|tsp|lb|lbs|oz|ounce|ounces|g|gram|grams|kg|kilogram|kilograms|'
            r'ml|milliliter|milliliters|l|liter|liters|can|cans|package|packages|'
            r'clove|cloves|bulb|bulbs|bunch|bunches|head|heads|slice|slices|'
            r'pound|pounds|stick|sticks|pinch|pinches|dash|dashes)\s+',
            r'^\d+(\.\d+)?\s+',  # 숫자만 있는 경우
            r'^\d+-\d+\s+',  # "2-3" 형태
            r'^\d+/\d+\s+',  # "1/2" 형태
        ]
        
        cleaned = name.strip()
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # 앞뒤 공백 제거
        cleaned = cleaned.strip()
        
        # 빈 문자열이면 원본 반환
        return cleaned if cleaned else name
    
    def _clean_translated_name(self, name_ko, name_en):
        """
        번역된 식재료 이름 정리
        
        문제:
        - "고추장 / 고추장" → "고추장"
        - "마늘 구근" → "마늘"
        - "밥그릇" → "쌀"
        - "쌀쌀한 플레이크" → "고춧가루"
        
        해결:
        1. "/" 기준 분리 후 중복 제거
        2. 불필요한 수식어 제거
        3. 의미 매핑
        """
        import re
        
        # [1] "/" 기준 분리 및 중복 제거
        if '/' in name_ko:
            parts = [p.strip() for p in name_ko.split('/')]
            # 중복 제거
            unique_parts = []
            for p in parts:
                if p and p not in unique_parts:
                    unique_parts.append(p)
            # 첫 번째 것만 사용
            name_ko = unique_parts[0] if unique_parts else name_ko
        
        # [2] 불필요한 수식어 제거
        cleanup_patterns = [
            (r'\s*구근$', ''),  # "마늘 구근" → "마늘"
            (r'\s*덩어리$', ''),  # "생강 덩어리" → "생강"
            (r'\s*뿌리$', ''),  # "무 뿌리" → "무"
            (r'\s*잎$', ''),  # "상추 잎" → "상추" (단, "깻잎"은 제외)
        ]
        
        for pattern, replacement in cleanup_patterns:
            name_ko = re.sub(pattern, replacement, name_ko)
        
        # [3] 의미 매핑 (번역 오류 수정)
        meaning_map = {
            '밥그릇': '쌀',  # "bowl rice" → "밥그릇"이 아니라 "쌀"
            '쌀쌀한 플레이크': '고춧가루',  # "chilly flakes" (chili flakes 오타)
            '고추 플레이크': '고춧가루',  # "chili flakes"
            '소금물 용액': '소금물',  # "brine solution"
            '발효새우': '새우젓',  # "fermented baby shrimps"
        }
        
        if name_ko in meaning_map:
            name_ko = meaning_map[name_ko]
        
        # [4] 영문 기반 추가 매핑
        if name_en:
            eng_map = {
                'rice': '쌀',
                'bowl rice': '쌀',
                'chili flakes': '고춧가루',
                'chilly flakes': '고춧가루',
                'red pepper flakes': '고춧가루',
                'garlic': '마늘',
                'garlic bulb': '마늘',
                'garlic clove': '마늘',
                'gochujang': '고추장',
                'korean gochujang': '고추장',
                'green onion': '대파',
                'green onions': '대파',
                'scallion': '대파',
                'napa cabbage': '배추',
                'chinese cabbage': '배추',
            }
            
            name_en_lower = name_en.lower().strip()
            if name_en_lower in eng_map:
                name_ko = eng_map[name_en_lower]
        
        return name_ko.strip()
    
    def _translate_ingredient_name(self, name):
        """
        식재료 이름 한글 번역
        
        RecipeTranslator를 사용하여 영문 식재료명을 한글로 번역
        """
        try:
            from .translator import RecipeTranslator
            
            translator = RecipeTranslator()
            
            # 번역 시도 (target='ko'는 이미 translator 초기화 시 설정됨)
            translated = translator.translate_text(name)
            
            # 번역 실패 시 원본 반환
            if not translated or translated == name:
                return name
            
            return translated
            
        except Exception as e:
            print(f"     ⚠️  번역 실패: {name} - {str(e)}")
            return name
    
    def fetch_and_save_recipes(self, 
                               cuisine='korean',
                               limit=50,
                               translate=True,
                               delay=0.5,
                               random_start=True):
        """
        레시피 일괄 수집 및 저장 (번역 포함)
        
        Args:
            cuisine: 요리 종류
            limit: 수집 개수
            translate: 번역 여부
            delay: API 호출 간격 (초)
            random_start: 랜덤 시작 위치 사용 여부 (기본 True)
        
        Returns:
            (수집된 개수, 중복 개수, 오류 개수)
        """
        import random
        
        collected = 0
        skipped = 0
        errors = 0
        
        # ============ 랜덤 시작 offset (NEW!) ============
        if random_start:
            # 다양한 cuisine 지원 (italian, chinese, japanese 등)
            # 0~500 사이의 랜덤 offset 사용
            start_offset = random.randint(0, 500)
            print(f"🔍 {cuisine} 레시피 수집 시작 (최대 {limit}개, 시작 위치: {start_offset})")
        else:
            start_offset = 0
            print(f"🔍 {cuisine} 레시피 수집 시작 (최대 {limit}개)")
        
        for offset in range(start_offset, start_offset + limit, 10):
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