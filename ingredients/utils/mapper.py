"""
식재료 이름 매핑 유틸리티 (최적화 버전)

주요 개선사항:
1. BASE_MAPPINGS 확장 (Spoonacular + 한식 DB 모두 커버)
2. 직접 추가 재료 처리 로직
3. 매핑 성능 최적화
4. 더 스마트한 정규화 알고리즘
"""

from ingredients.models import IngredientMaster, IngredientNameMapping


class IngredientMapper:
    """식재료 이름 매핑 유틸리티"""
    
    # ============================================================
    # 기본 매핑 데이터 (확장됨)
    # ============================================================
    BASE_MAPPINGS = {
        # ==================== 채소류 ====================
        'onion': '양파',
        'onions': '양파',
        'yellow onion': '양파',
        'white onion': '양파',
        'red onion': '적양파',
        'green onion': '대파',
        'scallion': '대파',
        'scallions': '대파',
        'spring onion': '대파',
        'spring onions': '대파',
        'leek': '대파',
        'garlic': '마늘',
        'garlic clove': '마늘',
        'garlic cloves': '마늘',
        'minced garlic': '다진마늘',
        'ginger': '생강',
        'fresh ginger': '생강',
        'minced ginger': '다진생강',
        'carrot': '당근',
        'carrots': '당근',
        'potato': '감자',
        'potatoes': '감자',
        'sweet potato': '고구마',
        'sweet potatoes': '고구마',
        'tomato': '토마토',
        'tomatoes': '토마토',
        'cherry tomato': '방울토마토',
        'cherry tomatoes': '방울토마토',
        'cucumber': '오이',
        'cucumbers': '오이',
        'cabbage': '양배추',
        'napa cabbage': '배추',
        'chinese cabbage': '배추',
        'bok choy': '청경채',
        'lettuce': '상추',
        'spinach': '시금치',
        'kale': '케일',
        'mushroom': '버섯',
        'mushrooms': '버섯',
        'shiitake mushroom': '표고버섯',
        'shiitake': '표고버섯',
        'enoki mushroom': '팽이버섯',
        'oyster mushroom': '느타리버섯',
        'button mushroom': '양송이버섯',
        'bell pepper': '파프리카',
        'red bell pepper': '빨간 파프리카',
        'yellow bell pepper': '노란 파프리카',
        'green bell pepper': '피망',
        'green pepper': '피망',
        'chili': '고추',
        'chili pepper': '고추',
        'hot pepper': '고추',
        'red chili': '홍고추',
        'green chili': '청고추',
        'jalapeño': '할라피뇨',
        'eggplant': '가지',
        'zucchini': '애호박',
        'squash': '호박',
        'pumpkin': '호박',
        'radish': '무',
        'daikon': '무',
        'korean radish': '무',
        'corn': '옥수수',
        'sweet corn': '옥수수',
        'corn kernels': '옥수수',
        'broccoli': '브로콜리',
        'cauliflower': '콜리플라워',
        'asparagus': '아스파라거스',
        'celery': '샐러리',
        'bean sprouts': '숙주',
        'soybean sprouts': '콩나물',
        'beansprouts': '콩나물',
        
        # ==================== 과일류 ====================
        'apple': '사과',
        'apples': '사과',
        'pear': '배',
        'pears': '배',
        'korean pear': '배',
        'banana': '바나나',
        'bananas': '바나나',
        'orange': '오렌지',
        'oranges': '오렌지',
        'lemon': '레몬',
        'lemons': '레몬',
        'lime': '라임',
        'limes': '라임',
        'strawberry': '딸기',
        'strawberries': '딸기',
        'grape': '포도',
        'grapes': '포도',
        'watermelon': '수박',
        'melon': '멜론',
        'peach': '복숭아',
        'peaches': '복숭아',
        'plum': '자두',
        'plums': '자두',
        'kiwi': '키위',
        'mango': '망고',
        'mangoes': '망고',
        'pineapple': '파인애플',
        'blueberry': '블루베리',
        'blueberries': '블루베리',
        'raspberry': '라즈베리',
        'raspberries': '라즈베리',
        
        # ==================== 육류 ====================
        'beef': '소고기',
        'ground beef': '다진 소고기',
        'beef steak': '스테이크',
        'sirloin': '등심',
        'ribeye': '갈비살',
        'brisket': '양지',
        'pork': '돼지고기',
        'ground pork': '다진 돼지고기',
        'pork belly': '삼겹살',
        'pork chop': '돼지갈비',
        'bacon': '베이컨',
        'ham': '햄',
        'sausage': '소시지',
        'sausages': '소시지',
        'chicken': '닭고기',
        'whole chicken': '닭',
        'chicken breast': '닭가슴살',
        'chicken breasts': '닭가슴살',
        'chicken thigh': '닭다리',
        'chicken thighs': '닭다리',
        'chicken drumstick': '닭북채',
        'chicken wings': '닭날개',
        'duck': '오리고기',
        'lamb': '양고기',
        'ground lamb': '다진 양고기',
        
        # ==================== 수산물 ====================
        'fish': '생선',
        'salmon': '연어',
        'tuna': '참치',
        'canned tuna': '통조림 참치',
        'mackerel': '고등어',
        'cod': '대구',
        'tilapia': '틸라피아',
        'sea bass': '농어',
        'halibut': '넙치',
        'shrimp': '새우',
        'prawns': '새우',
        'crab': '게',
        'crabmeat': '게살',
        'lobster': '랍스터',
        'squid': '오징어',
        'octopus': '문어',
        'clam': '조개',
        'clams': '조개',
        'mussel': '홍합',
        'mussels': '홍합',
        'oyster': '굴',
        'oysters': '굴',
        'scallop': '가리비',
        'scallops': '가리비',
        'anchovy': '멸치',
        'anchovies': '멸치',
        'dried anchovy': '멸치',
        'fish cake': '어묵',
        'surimi': '어묵',
        
        # ==================== 유제품·계란 ====================
        'milk': '우유',
        'whole milk': '우유',
        'skim milk': '저지방 우유',
        'cream': '생크림',
        'heavy cream': '생크림',
        'whipping cream': '생크림',
        'sour cream': '사워크림',
        'butter': '버터',
        'unsalted butter': '무염버터',
        'cheese': '치즈',
        'cheddar cheese': '체다치즈',
        'mozzarella cheese': '모짜렐라치즈',
        'parmesan cheese': '파마산치즈',
        'cream cheese': '크림치즈',
        'yogurt': '요거트',
        'greek yogurt': '그릭요거트',
        'egg': '계란',
        'eggs': '계란',
        'egg white': '계란 흰자',
        'egg whites': '계란 흰자',
        'egg yolk': '계란 노른자',
        'egg yolks': '계란 노른자',
        
        # ==================== 두부·콩 ====================
        'tofu': '두부',
        'soft tofu': '순두부',
        'firm tofu': '단단한 두부',
        'silken tofu': '연두부',
        'soybean': '콩',
        'soybeans': '콩',
        'black bean': '검은콩',
        'black beans': '검은콩',
        'kidney bean': '강낭콩',
        'kidney beans': '강낭콩',
        'chickpea': '병아리콩',
        'chickpeas': '병아리콩',
        'lentil': '렌틸콩',
        'lentils': '렌틸콩',
        'edamame': '풋콩',
        'peanut': '땅콩',
        'peanuts': '땅콩',
        
        # ==================== 곡물·면류 ====================
        'rice': '쌀',
        'white rice': '백미',
        'brown rice': '현미',
        'glutinous rice': '찹쌀',
        'flour': '밀가루',
        'all-purpose flour': '밀가루',
        'bread flour': '강력분',
        'cake flour': '박력분',
        'wheat flour': '밀가루',
        'pasta': '파스타',
        'spaghetti': '스파게티',
        'penne': '펜네',
        'fusilli': '푸실리',
        'linguine': '링귀네',
        'fettuccine': '페투치네',
        'noodle': '면',
        'noodles': '면',
        'ramen': '라면',
        'udon': '우동',
        'soba': '소바',
        'rice noodle': '쌀국수',
        'rice noodles': '쌀국수',
        'vermicelli': '당면',
        'glass noodle': '당면',
        'bread': '빵',
        'white bread': '식빵',
        'whole wheat bread': '통밀빵',
        'baguette': '바게트',
        'tortilla': '토르티야',
        'oat': '귀리',
        'oats': '귀리',
        'oatmeal': '오트밀',
        'quinoa': '퀴노아',
        'couscous': '쿠스쿠스',
        
        # ==================== 양념·조미료 ====================
        'salt': '소금',
        'sea salt': '천일염',
        'kosher salt': '코셔 소금',
        'sugar': '설탕',
        'white sugar': '백설탕',
        'brown sugar': '흑설탕',
        'honey': '꿀',
        'syrup': '시럽',
        'corn syrup': '물엿',
        'maple syrup': '메이플 시럽',
        'vinegar': '식초',
        'rice vinegar': '쌀식초',
        'apple cider vinegar': '사과식초',
        'balsamic vinegar': '발사믹 식초',
        'soy sauce': '간장',
        'light soy sauce': '국간장',
        'dark soy sauce': '진간장',
        'soybean paste': '된장',
        'doenjang': '된장',
        'red pepper paste': '고추장',
        'gochujang': '고추장',
        'ssamjang': '쌈장',
        'fish sauce': '액젓',
        'salted shrimp': '새우젓',
        'red pepper powder': '고춧가루',
        'red pepper flakes': '고춧가루',
        'gochugaru': '고춧가루',
        'black pepper': '후추',
        'pepper': '후추',
        'white pepper': '백후추',
        'sesame oil': '참기름',
        'perilla oil': '들기름',
        'cooking oil': '식용유',
        'vegetable oil': '식용유',
        'olive oil': '올리브유',
        'canola oil': '카놀라유',
        'coconut oil': '코코넛 오일',
        'mayonnaise': '마요네즈',
        'mayo': '마요네즈',
        'ketchup': '케첩',
        'tomato ketchup': '케첩',
        'mustard': '겨자',
        'worcestershire sauce': '우스터 소스',
        'oyster sauce': '굴소스',
        'barbecue sauce': '바비큐 소스',
        'bbq sauce': '바비큐 소스',
        'hot sauce': '핫소스',
        'chili sauce': '칠리소스',
        'sriracha': '스리라차',
        'tahini': '타히니',
        'pesto': '페스토',
        'tomato sauce': '토마토소스',
        'tomato paste': '토마토페이스트',
        'curry powder': '카레가루',
        'curry paste': '카레페이스트',
        'paprika': '파프리카 가루',
        'cumin': '커민',
        'coriander': '고수',
        'turmeric': '강황',
        'cinnamon': '계피',
        'nutmeg': '육두구',
        'basil': '바질',
        'oregano': '오레가노',
        'thyme': '타임',
        'rosemary': '로즈마리',
        'parsley': '파슬리',
        'cilantro': '고수',
        'bay leaf': '월계수잎',
        'bay leaves': '월계수잎',
        
        # ==================== 견과·씨앗 ====================
        'almond': '아몬드',
        'almonds': '아몬드',
        'walnut': '호두',
        'walnuts': '호두',
        'cashew': '캐슈넛',
        'cashews': '캐슈넛',
        'pecan': '피칸',
        'pecans': '피칸',
        'hazelnut': '헤이즐넛',
        'hazelnuts': '헤이즐넛',
        'macadamia': '마카다미아',
        'macadamias': '마카다미아',
        'pistachio': '피스타치오',
        'pistachios': '피스타치오',
        'pine nut': '잣',
        'pine nuts': '잣',
        'sesame seed': '참깨',
        'sesame seeds': '참깨',
        'sunflower seed': '해바라기씨',
        'sunflower seeds': '해바라기씨',
        'pumpkin seed': '호박씨',
        'pumpkin seeds': '호박씨',
        'chia seed': '치아씨드',
        'chia seeds': '치아씨드',
        'flax seed': '아마씨',
        'flax seeds': '아마씨',
        
        # ==================== 건조·가공식품 ====================
        'seaweed': '김',
        'dried seaweed': '김',
        'laver': '김',
        'nori': '김',
        'kelp': '다시마',
        'kombu': '다시마',
        'wakame': '미역',
        'dried shiitake': '표고버섯',
        'dried mushroom': '건표고버섯',
        'raisin': '건포도',
        'raisins': '건포도',
        'dried cranberry': '건크랜베리',
        'dried cranberries': '건크랜베리',
        'prune': '자두',
        'prunes': '자두',
        'date': '대추야자',
        'dates': '대추야자',
        'canned tomato': '토마토 통조림',
        'canned tomatoes': '토마토 통조림',
        'tomato can': '토마토 통조림',
        'coconut milk': '코코넛 밀크',
        'condensed milk': '연유',
        'evaporated milk': '에바밀크',
        'stock': '육수',
        'broth': '육수',
        'chicken stock': '닭육수',
        'beef stock': '소고기 육수',
        'vegetable stock': '채소 육수',
        'chicken broth': '닭육수',
        'beef broth': '소고기 육수',
        
        # ==================== 음료 ====================
        'water': '물',
        'ice': '얼음',
        'coffee': '커피',
        'tea': '차',
        'green tea': '녹차',
        'black tea': '홍차',
        'beer': '맥주',
        'wine': '와인',
        'red wine': '레드와인',
        'white wine': '화이트와인',
        'sake': '사케',
        'soju': '소주',
        'juice': '주스',
        'orange juice': '오렌지 주스',
        'lemon juice': '레몬 주스',
        'lime juice': '라임 주스',
        'apple juice': '사과 주스',
        'soda': '탄산음료',
        'sprite': '사이다',
        'coke': '콜라',
        'cola': '콜라',
    }
    
    # ============================================================
    # 매핑 메서드
    # ============================================================
    
    @classmethod
    def find_ingredient(cls, name):
        """
        식재료 이름으로 IngredientMaster 찾기
        
        검색 순서:
        1. IngredientMaster 직접 검색 (name_ko, name_en)
        2. IngredientNameMapping 테이블 검색
        3. BASE_MAPPINGS에서 검색
        4. 정규화 후 재검색
        
        Args:
            name: 식재료 이름 (한글/영어 모두 가능)
        
        Returns:
            IngredientMaster 객체 또는 None
        """
        if not name:
            return None
        
        name = name.strip()
        name_lower = name.lower()
        
        # 1. IngredientMaster에서 직접 검색
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
            # 여러 개 있으면 신뢰도가 가장 높은 것 선택
            mapping = IngredientNameMapping.objects.select_related('ingredient').filter(
                alternative_name__iexact=name
            ).order_by('-confidence').first()
            if mapping:
                return mapping.ingredient
        
        # 3. BASE_MAPPINGS에서 검색
        if name_lower in cls.BASE_MAPPINGS:
            korean_name = cls.BASE_MAPPINGS[name_lower]
            ingredient = IngredientMaster.find_by_name(korean_name)
            if ingredient:
                # 매핑 테이블에 자동 저장 (다음번엔 더 빠르게)
                cls.create_mapping(
                    ingredient=ingredient,
                    alternative_name=name,
                    source='auto',
                    confidence=1.0
                )
                return ingredient
        
        # 4. BASE_MAPPINGS 역방향 검색 (한글 입력 시)
        for eng_name, kor_name in cls.BASE_MAPPINGS.items():
            if kor_name == name:
                ingredient = IngredientMaster.find_by_name(kor_name)
                if ingredient:
                    return ingredient
        
        # 5. 정규화 후 재검색
        normalized = cls.normalize_name(name)
        if normalized and normalized != name_lower:
            return cls.find_ingredient(normalized)
        
        return None
    
    @classmethod
    def normalize_name(cls, name):
        """
        식재료 이름 정규화 (개선된 버전)
        
        제거 항목:
        - 괄호 안 내용
        - 수량/단위
        - 조리 상태 ('chopped', 'diced', '다진' 등)
        - 불필요한 수식어
        
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
        normalized = re.sub(r'\{[^}]*\}', '', normalized)
        
        # 숫자와 단위 제거 (더 포괄적)
        units = [
            'g', 'ml', 'kg', 'l', 'lb', 'oz', 'fl oz', 'tsp', 'tbsp', 
            '개', '큰술', '작은술', '컵', 'cup', 'tablespoon', 'teaspoon',
            'gram', 'grams', 'milliliter', 'milliliters', 'liter', 'liters',
            'pound', 'pounds', 'ounce', 'ounces'
        ]
        for unit in units:
            normalized = re.sub(rf'\d+\s*{unit}\b', '', normalized, flags=re.IGNORECASE)
        
        # 단독 숫자 제거
        normalized = re.sub(r'\b\d+\.?\d*\b', '', normalized)
        
        # 조리 형태 영어 (더 포괄적)
        cooking_terms_en = [
            'chopped', 'diced', 'minced', 'sliced', 'crushed', 'grated',
            'fresh', 'dried', 'frozen', 'canned', 'cooked', 'raw',
            'peeled', 'julienned', 'shredded', 'whole', 'halved',
            'quartered', 'cubed', 'ground', 'mashed', 'pureed',
            'roasted', 'toasted', 'blanched', 'steamed', 'boiled',
            'finely', 'roughly', 'thinly', 'thickly', 'large', 'small',
            'medium', 'baby', 'extra', 'super', 'premium', 'organic',
            'unsalted', 'salted', 'sweetened', 'unsweetened',
            'low-fat', 'non-fat', 'full-fat', 'reduced', 'light'
        ]
        for term in cooking_terms_en:
            normalized = re.sub(rf'\b{term}\b', '', normalized, flags=re.IGNORECASE)
        
        # 조리 형태 한글
        normalized = re.sub(r'(다진|채썬|썬|간|볶은|삶은|튀긴|구운|찐|데친|익힌)', '', normalized)
        normalized = re.sub(r'(신선한|냉동|냉장|통조림|건조|말린)', '', normalized)
        
        # 특수문자 제거 (하이픈, 언더스코어 등)
        normalized = re.sub(r'[-_/\\]', ' ', normalized)
        normalized = re.sub(r'[^\w\s가-힣]', '', normalized)
        
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
            source: 출처 ('spoonacular', 'korean_db', 'user', 'manual', 'auto')
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
        
        if not created and mapping.confidence < confidence:
            # 기존 매핑보다 신뢰도가 높으면 업데이트
            mapping.confidence = confidence
            mapping.source = source
            mapping.save()
        
        return mapping, created
    
    @classmethod
    def bulk_create_base_mappings(cls):
        """
        BASE_MAPPINGS를 IngredientNameMapping 테이블에 일괄 생성
        
        Returns:
            생성된 매핑 개수
        """
        created_count = 0
        
        for eng_name, kor_name in cls.BASE_MAPPINGS.items():
            # 한글명으로 식재료 찾기
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
        
        return created_count
    
    @classmethod
    def get_or_create_user_ingredient(cls, user_input_name, category_id=17):
        """
        사용자가 직접 추가한 식재료 처리
        
        1. 기존 매핑 찾기
        2. 없으면 "직접 추가" 카테고리에 새로 생성
        3. 매핑 테이블에 등록
        
        Args:
            user_input_name: 사용자가 입력한 식재료 이름
            category_id: 직접 추가 카테고리 ID (기본값: 17)
        
        Returns:
            IngredientMaster 객체
        """
        # 1. 기존 식재료 찾기
        ingredient = cls.find_ingredient(user_input_name)
        if ingredient:
            return ingredient
        
        # 2. 정규화된 이름으로 재검색
        normalized = cls.normalize_name(user_input_name)
        if normalized:
            ingredient = cls.find_ingredient(normalized)
            if ingredient:
                # 사용자 입력을 매핑에 추가
                cls.create_mapping(
                    ingredient=ingredient,
                    alternative_name=user_input_name,
                    source='user',
                    confidence=0.8
                )
                return ingredient
        
        # 3. 새로 생성 (직접 추가 카테고리)
        from ingredients.models import IngredientCategory
        
        try:
            category = IngredientCategory.objects.get(category_id=category_id)
        except IngredientCategory.DoesNotExist:
            # 직접 추가 카테고리가 없으면 생성
            category = IngredientCategory.objects.create(
                category_id=category_id,
                name='직접 추가',
                icon_url='➕'
            )
        
        # 한글/영어 판별
        import re
        is_korean = bool(re.search(r'[가-힣]', user_input_name))
        
        ingredient = IngredientMaster.objects.create(
            category=category,
            name_ko=user_input_name if is_korean else normalized or user_input_name,
            name_en=user_input_name if not is_korean else '',
            aliases=[user_input_name]
        )
        
        # 매핑 추가
        cls.create_mapping(
            ingredient=ingredient,
            alternative_name=user_input_name,
            source='user',
            confidence=1.0
        )
        
        return ingredient
    
    @classmethod
    def batch_find_ingredients(cls, names):
        """
        여러 식재료를 한 번에 찾기 (성능 최적화)
        
        Args:
            names: 식재료 이름 리스트
        
        Returns:
            딕셔너리 {name: IngredientMaster or None}
        """
        result = {}
        
        for name in names:
            result[name] = cls.find_ingredient(name)
        
        return result
    
    @classmethod
    def suggest_matches(cls, user_input, limit=5):
        """
        사용자 입력에 대한 추천 매칭 제공
        
        유사한 식재료 검색하여 반환
        
        Args:
            user_input: 사용자 입력
            limit: 최대 반환 개수
        
        Returns:
            IngredientMaster 리스트
        """
        from django.db.models import Q
        
        if not user_input:
            return []
        
        normalized = cls.normalize_name(user_input)
        
        # 부분 일치 검색
        ingredients = IngredientMaster.objects.filter(
            Q(name_ko__icontains=user_input) |
            Q(name_en__icontains=user_input) |
            Q(name_ko__icontains=normalized) |
            Q(name_en__icontains=normalized)
        ).select_related('category')[:limit]
        
        return list(ingredients)