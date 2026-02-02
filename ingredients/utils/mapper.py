from ingredients.models import IngredientMaster, IngredientNameMapping


class IngredientMapper:
    """식재료 이름 매핑 유틸리티"""
    
    # 기본 매핑 데이터 (한글 <-> 영어)
    BASE_MAPPINGS = {
        # 채소류
        'onion': '양파',
        'onions': '양파',
        'green onion': '대파',
        'scallion': '대파',
        'scallions': '대파',
        'spring onion': '대파',
        'garlic': '마늘',
        'garlic clove': '마늘',
        'garlic cloves': '마늘',
        'ginger': '생강',
        'carrot': '당근',
        'carrots': '당근',
        'potato': '감자',
        'potatoes': '감자',
        'tomato': '토마토',
        'tomatoes': '토마토',
        'cucumber': '오이',
        'cucumbers': '오이',
        'cabbage': '양배추',
        'napa cabbage': '배추',
        'chinese cabbage': '배추',
        'lettuce': '상추',
        'spinach': '시금치',
        'mushroom': '버섯',
        'mushrooms': '버섯',
        'shiitake mushroom': '표고버섯',
        'shiitake': '표고버섯',
        'bell pepper': '파프리카',
        'red pepper': '빨간 파프리카',
        'green pepper': '피망',
        'chili': '고추',
        'hot pepper': '고추',
        'red chili': '홍고추',
        'green chili': '청양고추',
        'eggplant': '가지',
        'zucchini': '애호박',
        'squash': '호박',
        'pumpkin': '호박',
        'radish': '무',
        'daikon': '무',
        'korean radish': '무',
        'corn': '옥수수',
        'sweet corn': '옥수수',
        'broccoli': '브로콜리',
        'cauliflower': '콜리플라워',
        'bean sprouts': '숙주',
        'soybean sprouts': '콩나물',
        
        # 육류
        'beef': '소고기',
        'pork': '돼지고기',
        'chicken': '닭고기',
        'chicken breast': '닭가슴살',
        'chicken thigh': '닭다리',
        'ground beef': '다진 소고기',
        'ground pork': '다진 돼지고기',
        'pork belly': '삼겹살',
        'bacon': '베이컨',
        'sausage': '소시지',
        'ham': '햄',
        
        # 해산물
        'shrimp': '새우',
        'prawns': '새우',
        'squid': '오징어',
        'octopus': '문어',
        'clam': '조개',
        'clams': '조개',
        'mussel': '홍합',
        'mussels': '홍합',
        'crab': '게',
        'oyster': '굴',
        'oysters': '굴',
        'fish': '생선',
        'salmon': '연어',
        'tuna': '참치',
        'mackerel': '고등어',
        'anchovies': '멸치',
        'dried anchovies': '멸치',
        'sea urchin': '성게',
        'sea cucumber': '해삼',
        
        # 곡물/면류
        'rice': '쌀',
        'white rice': '백미',
        'brown rice': '현미',
        'flour': '밀가루',
        'wheat flour': '밀가루',
        'noodles': '국수',
        'pasta': '파스타',
        'spaghetti': '스파게티',
        'ramen': '라면',
        'instant noodles': '라면',
        'udon': '우동',
        'vermicelli': '당면',
        'glass noodles': '당면',
        
        # 두부/콩류
        'tofu': '두부',
        'firm tofu': '두부',
        'soft tofu': '순두부',
        'silken tofu': '순두부',
        'soybean': '콩',
        'soybeans': '콩',
        'black beans': '검은콩',
        'red beans': '팥',
        'kidney beans': '강낭콩',
        
        # 양념/소스류
        'soy sauce': '간장',
        'dark soy sauce': '진간장',
        'light soy sauce': '국간장',
        'gochujang': '고추장',
        'red pepper paste': '고추장',
        'gochugaru': '고춧가루',
        'red pepper flakes': '고춧가루',
        'red pepper powder': '고춧가루',
        'doenjang': '된장',
        'soybean paste': '된장',
        'sesame oil': '참기름',
        'vegetable oil': '식용유',
        'cooking oil': '식용유',
        'olive oil': '올리브유',
        'canola oil': '카놀라유',
        'salt': '소금',
        'sugar': '설탕',
        'white sugar': '설탕',
        'brown sugar': '흑설탕',
        'black pepper': '후추',
        'pepper': '후추',
        'ground pepper': '후추',
        'vinegar': '식초',
        'rice vinegar': '식초',
        'cooking wine': '청주',
        'sake': '청주',
        'rice wine': '청주',
        'mirin': '미림',
        'oyster sauce': '굴소스',
        'fish sauce': '액젓',
        'ketchup': '케첩',
        'tomato ketchup': '케첩',
        'mayonnaise': '마요네즈',
        'mustard': '겨자',
        'wasabi': '와사비',
        
        # 기타
        'egg': '달걀',
        'eggs': '달걀',
        'milk': '우유',
        'butter': '버터',
        'cheese': '치즈',
        'bread': '빵',
        'sesame seeds': '깨',
        'sesame': '깨',
        'seaweed': '김',
        'dried seaweed': '김',
        'nori': '김',
        'kelp': '다시마',
        'green tea': '녹차',
        'perilla leaves': '깻잎',
        'perilla oil': '들기름',
        'honey': '꿀',
        'starch': '전분',
        'cornstarch': '전분',
        'baking powder': '베이킹파우더',
        'baking soda': '베이킹소다',
        'yeast': '이스트',
    }
    
    @classmethod
    def find_ingredient(cls, name):
        """
        이름으로 식재료 찾기
        
        Args:
            name: 식재료 이름 (한글 또는 영어)
        
        Returns:
            IngredientMaster 객체 또는 None
        """
        if not name:
            return None
        
        name_lower = name.lower().strip()
        
        # 1. IngredientMaster에서 직접 검색 (name_ko, name_en)
        ingredient = IngredientMaster.find_by_name(name)
        if ingredient:
            return ingredient
        
        # 2. IngredientNameMapping 테이블에서 검색
        try:
            mapping = IngredientNameMapping.objects.select_related('ingredient').get(
                alternative_name__iexact=name
            )
            return mapping.ingredient
        except IngredientNameMapping.DoesNotExist:
            pass
        except IngredientNameMapping.MultipleObjectsReturned:
            # 여러 개 있으면 첫 번째 반환
            mapping = IngredientNameMapping.objects.select_related('ingredient').filter(
                alternative_name__iexact=name
            ).first()
            if mapping:
                return mapping.ingredient
        
        # 3. BASE_MAPPINGS에서 검색 (영어 -> 한글)
        if name_lower in cls.BASE_MAPPINGS:
            korean_name = cls.BASE_MAPPINGS[name_lower]
            ingredient = IngredientMaster.find_by_name(korean_name)
            if ingredient:
                return ingredient
        
        # 4. BASE_MAPPINGS 역방향 (한글 검색)
        for eng_name, kor_name in cls.BASE_MAPPINGS.items():
            if kor_name == name:
                ingredient = IngredientMaster.find_by_name(kor_name)
                if ingredient:
                    return ingredient
        
        # 5. 부분 일치 (정규화 후)
        normalized = cls.normalize_name(name)
        if normalized:
            ingredient = IngredientMaster.find_by_name(normalized)
            if ingredient:
                return ingredient
        
        return None
    
    @classmethod
    def normalize_name(cls, name):
        """
        식재료 이름 정규화
        
        Args:
            name: 원본 이름
        
        Returns:
            정규화된 이름
        """
        if not name:
            return ''
        
        import re
        
        # 기본 정리
        normalized = name.strip().lower()
        
        # 괄호 안 내용 제거
        normalized = re.sub(r'\([^)]*\)', '', normalized)
        normalized = re.sub(r'\[[^\]]*\]', '', normalized)
        
        # 숫자와 단위 제거
        normalized = re.sub(r'\d+\s*(g|ml|kg|개|큰술|작은술|컵|cup|tablespoon|teaspoon|tbsp|tsp)', '', normalized, flags=re.IGNORECASE)
        
        # 'chopped', 'diced' 등 조리 형태 제거
        cooking_terms = [
            'chopped', 'diced', 'minced', 'sliced', 'crushed', 
            'fresh', 'dried', 'frozen', 'canned', 'cooked',
            'raw', 'peeled', 'julienned', 'grated', 'shredded',
            'whole', 'halved', 'quartered', 'cubed'
        ]
        for term in cooking_terms:
            normalized = normalized.replace(term, '')
        
        # 한글 조리 형태 제거
        normalized = re.sub(r'(다진|채썬|썬|간|볶은|삶은|튀긴)', '', normalized)
        
        # 다중 공백 제거
        normalized = ' '.join(normalized.split())
        
        return normalized.strip()
    
    @classmethod
    def create_mapping(cls, ingredient, alternative_name, source='manual', confidence=1.0):
        """
        새로운 매핑 생성
        
        Args:
            ingredient: IngredientMaster 객체
            alternative_name: 대체 이름
            source: 출처 ('spoonacular', 'korean_db', 'user', 'manual')
            confidence: 신뢰도 (0.0 ~ 1.0)
        
        Returns:
            (mapping, created) 튜플
        """
        mapping, created = IngredientNameMapping.objects.get_or_create(
            ingredient=ingredient,
            alternative_name=alternative_name,
            defaults={
                'source': source,
                'confidence': confidence
            }
        )
        return mapping, created
    
    @classmethod
    def bulk_create_base_mappings(cls):
        """BASE_MAPPINGS를 DB에 일괄 저장"""
        created_count = 0
        skipped_count = 0
        
        for eng_name, kor_name in cls.BASE_MAPPINGS.items():
            # 한글 이름으로 Ingredient 찾기
            ingredient = IngredientMaster.find_by_name(kor_name)
            
            if ingredient:
                _, created = cls.create_mapping(
                    ingredient=ingredient,
                    alternative_name=eng_name,
                    source='manual',
                    confidence=1.0
                )
                if created:
                    created_count += 1
            else:
                skipped_count += 1
                print(f"⚠️  '{kor_name}' 식재료를 찾을 수 없어 '{eng_name}' 매핑을 건너뜁니다.")
        
        print(f"\n✓ 총 {created_count}개 매핑 생성 완료")
        if skipped_count > 0:
            print(f"⚠️  {skipped_count}개 매핑 건너뜀 (식재료 없음)")
        
        return created_count