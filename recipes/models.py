"""
Recipes App Models
레시피 관련 모델 정의

이 파일은 레시피, 찜, 요리 일지를 관리합니다.
- Recipe: 레시피 정보
- RecipeIngredient: 레시피에 필요한 식재료
- FavoriteRecipe: 사용자가 찜한 레시피
- RecipeLog: 요리 일지 (캘린더에 표시)
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

# Create your models here.
# ==================== Enum 정의 ====================
class DifficultyLevel(models.TextChoices):
    """
    난이도 선택지
    
    Django의 TextChoices를 사용하여 ENUM처럼 관리
    DB에는 'EASY' 저장, 표시는 '쉬움'
    """
    EASY = 'EASY', '쉬움'
    NORMAL = 'NORMAL', '보통'
    DIFFICULT = 'DIFFICULT', '어려움'


class RecipeSource(models.TextChoices):
    """
    레시피 출처
    
    어디서 가져온 레시피인지 구분
    """
    SPOONACULAR = 'spoonacular', 'Spoonacular'  # Spoonacular API
    KOREAN_FOOD = 'korean_food', '한식 DB'      # 식약처 한식 DB
    USER_CREATED = 'user_created', '사용자 생성'  # 사용자가 직접 등록
    OTHER = 'other', '기타'


# ==================== 모델 정의 ====================
class Recipe(models.Model):
    """
    레시피 정보
    
    외부 API(Spoonacular 등) 또는 사용자가 직접 생성한 레시피
    
    Fields:
        recipe_id: 레시피 고유 ID (PK)
        external_id: 외부 API의 레시피 ID (중복 방지용)
        source: 레시피 출처
        title: 레시피 제목
        image_url: 썸네일 이미지
        ready_minutes: 예상 조리 시간
        difficulty: 난이도 (자동 계산 또는 수동 설정)
        servings: 인분
        raw_data: API 원본 데이터 (JSON)
        instructions: 조리 단계 (JSON)
        total_ingredients: 전체 재료 수 (캐싱)
        required_ingredients: 필수 재료 수 (캐싱)
        is_active: 활성 상태 (추천 목록 표시 여부)
    """
    # Primary Key
    recipe_id = models.BigAutoField(
        primary_key=True,
        verbose_name='레시피 ID'
    )
    
    # 외부 API ID (Spoonacular 레시피 ID 등)
    # 같은 레시피를 중복 저장하지 않기 위함
    external_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='외부 API ID',
        help_text='Spoonacular ID 등'
    )
    
    # 레시피 출처
    # choices: Admin에서 드롭다운으로 표시
    source = models.CharField(
        max_length=50,
        choices=RecipeSource.choices,
        verbose_name='출처'
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name='레시피 제목'
    )
    
    image_url = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='썸네일 이미지'
    )
    
    # 예상 조리 시간 (분 단위)
    ready_minutes = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name='예상 조리시간(분)'
    )
    
    # 난이도 (단계 수와 조리 시간 기반 자동 계산 가능)
    difficulty = models.CharField(
        max_length=20,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.NORMAL,
        verbose_name='난이도'
    )
    
    # 인분 수
    servings = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        verbose_name='인분',
        default=1
    )
    
    # API 원본 데이터 (JSON)
    # 나중에 필요할 수 있는 데이터를 모두 보관
    raw_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='API 원본 데이터'
    )
    
    # 조리 단계 (JSON 배열)
    # 예: [{"step": 1, "description": "양파를 썬다"}, ...]
    instructions = models.JSONField(
        null=True,
        blank=True,
        verbose_name='조리 단계',
        help_text='[{"step": 1, "description": "..."}, ...] 형식'
    )
    
    # 생성 시점 자동 저장
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='캐싱/등록 시점'
    )
    
    # 수정 시점 자동 갱신
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )
    
    # ========== 성능 최적화를 위한 캐싱 필드 (선택사항) ==========
    # 전체 재료 수
    # RecipeIngredient 저장 시 자동 업데이트
    # 매번 count() 쿼리 날리지 않고 캐싱된 값 사용
    total_ingredients = models.IntegerField(
        default=0,
        verbose_name='전체 재료 수',
        help_text='RecipeIngredient 저장 시 자동 업데이트'
    )
    
    # 필수 재료 수 (선택 재료 제외)
    required_ingredients = models.IntegerField(
        default=0,
        verbose_name='필수 재료 수',
        help_text='선택 재료 제외한 필수 재료 수'
    )
    
    # 활성 상태 (추천 목록에 표시 여부)
    # 관리자가 특정 레시피를 비활성화할 수 있음
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성 상태',
        help_text='추천 목록에 표시 여부'
    )

    class Meta:
        db_table = 'Recipe'
        verbose_name = '레시피'
        verbose_name_plural = '레시피'
        indexes = [
            models.Index(fields=['source'], name='idx_recipe_source'),
            models.Index(fields=['difficulty'], name='idx_recipe_difficulty'),
            models.Index(fields=['ready_minutes'], name='idx_recipe_time'),
            # external_id + source 조합으로 검색 (중복 확인용)
            models.Index(fields=['external_id', 'source'], name='idx_recipe_external_source'),
            models.Index(fields=['is_active'], name='idx_recipe_active'),
        ]
        constraints = [
            # 조리 시간은 0 이상
            models.CheckConstraint(
                check=models.Q(ready_minutes__gte=0),
                name='chk_ready_minutes_positive'
            ),
            # 같은 출처에서 같은 external_id 중복 방지
            # 예: Spoonacular의 레시피 123은 한 번만 저장
            models.UniqueConstraint(
                fields=['external_id', 'source'],
                name='uq_external_id_source',
                condition=models.Q(external_id__isnull=False)
            ),
        ]

    def __str__(self):
        """Admin에서 '김치볶음밥 (쉬움)' 형태로 표시"""
        return f"{self.title} ({self.get_difficulty_display()})"

    @property
    def step_count(self):
        """
        조리 단계 수
        
        난이도 자동 계산에 사용
        
        Returns:
            int: instructions 배열의 길이
        """
        if not self.instructions:
            return 0
        return len(self.instructions)

    @property
    def total_ingredients_count(self):
        """
        필요한 식재료 개수
        
        캐싱 필드가 있으면 사용, 없으면 count() 쿼리
        
        Returns:
            int: 전체 재료 수
        """
        return self.total_ingredients if self.total_ingredients else self.recipe_ingredients.count()

    @property
    def required_ingredients_count(self):
        """
        필수 식재료 개수 (선택 재료 제외)
        
        Returns:
            int: 필수 재료 수
        """
        return self.required_ingredients if self.required_ingredients else self.recipe_ingredients.filter(is_optional=False).count()

    def update_ingredient_counts(self):
        """
        재료 개수 캐싱 필드 업데이트
        
        RecipeIngredient 추가/삭제 후 호출
        
        Example:
            recipe = Recipe.objects.get(id=1)
            RecipeIngredient.objects.create(recipe=recipe, ...)
            recipe.update_ingredient_counts()  # 캐싱 필드 업데이트
        """
        self.total_ingredients = self.recipe_ingredients.count()
        self.required_ingredients = self.recipe_ingredients.filter(is_optional=False).count()
        self.save(update_fields=['total_ingredients', 'required_ingredients'])

    def calculate_difficulty(self):
        """
        단계 수와 조리 시간 기반 난이도 자동 계산
        
        추천 로직 문서의 공식 사용:
        난이도 점수 = (단계 복잡도 × 0.6) + (조리 시간 점수 × 0.4)
        
        Returns:
            str: DifficultyLevel (EASY, NORMAL, DIFFICULT)
        
        점수 기준:
            단계 복잡도:
            - 1~3단계: 1점 (쉬움)
            - 4~6단계: 2점 (보통)
            - 7단계 이상: 3점 (어려움)
            
            조리 시간 점수:
            - 20분 이하: 1점 (쉬움)
            - 21~40분: 2점 (보통)
            - 41분 이상: 3점 (어려움)
            
            최종 난이도:
            - 1.0~1.5: EASY
            - 1.6~2.4: NORMAL
            - 2.5~3.0: DIFFICULT
        """
        step_count = self.step_count
        ready_time = self.ready_minutes or 30  # 기본값 30분
        
        # 단계 복잡도 (1~3점)
        if step_count <= 3:
            step_score = 1
        elif step_count <= 6:
            step_score = 2
        else:
            step_score = 3
        
        # 조리 시간 점수 (1~3점)
        if ready_time <= 20:
            time_score = 1
        elif ready_time <= 40:
            time_score = 2
        else:
            time_score = 3
        
        # 최종 점수 계산 (가중 평균)
        final_score = (step_score * 0.6) + (time_score * 0.4)
        
        # 난이도 매핑
        if final_score <= 1.5:
            return DifficultyLevel.EASY
        elif final_score <= 2.4:
            return DifficultyLevel.NORMAL
        else:
            return DifficultyLevel.DIFFICULT

    def get_difficulty_score_for_user(self, user_skill_level):
        """
        사용자 실력에 따른 난이도 점수 계산
        
        사용자 실력과 레시피 난이도가 비슷할수록 높은 점수
        (너무 쉬우면 지루하고, 너무 어려우면 포기함)
        
        Args:
            user_skill_level (str): 'BEGINNER', 'INTERMEDIATE', 'EXPERT'
        
        Returns:
            int: 난이도 점수 (0~100)
        
        공식:
            점수 = 100 - |사용자 실력 - 레시피 난이도| × 30
        
        Example:
            초보(1) + 쉬움(1) = 100 - 0 × 30 = 100점
            초보(1) + 보통(2) = 100 - 1 × 30 = 70점
            초보(1) + 어려움(3) = 100 - 2 × 30 = 40점
        """
        # 난이도를 숫자로 변환
        difficulty_map = {
            DifficultyLevel.EASY: 1,
            DifficultyLevel.NORMAL: 2,
            DifficultyLevel.DIFFICULT: 3
        }
        
        # 사용자 실력을 숫자로 변환
        skill_map = {
            'BEGINNER': 1,
            'INTERMEDIATE': 2,
            'EXPERT': 3
        }
        
        recipe_difficulty = difficulty_map.get(self.difficulty, 2)
        user_skill = skill_map.get(user_skill_level, 1)
        
        # 점수 계산
        score = 100 - abs(user_skill - recipe_difficulty) * 30
        return max(0, score)  # 최소 0점

    def calculate_ingredient_matching_score(self, user_ingredient_ids):
        """
        재료 매칭 점수 계산 (추천 점수의 60%)
        
        현재 보유한 식재료로 얼마나 만들 수 있는지 계산
        
        Args:
            user_ingredient_ids (list): 사용자 보유 식재료 ID 리스트
        
        Returns:
            float: 재료 매칭 점수 (0~100)
        
        공식:
            재료 매칭 점수 = (보유 재료 비율 × 70%) + (부족 재료 패널티 × 30%)
            
            보유 재료 비율 = (보유한 재료 수 / 레시피 전체 재료 수) × 100
            
            부족 재료 패널티:
            - 0개 부족: 100점
            - 1개 부족: 85점
            - 2개 부족: 70점
            - 3개 이상: 50점
        
        Example:
            레시피 필요 재료: [밥, 김치, 계란, 식용유, 참기름] (5개)
            보유 재료: [밥, 김치, 계란, 식용유] (4개)
            
            보유 비율 = 4/5 × 100 = 80점
            패널티 = 85점 (1개 부족)
            최종 = 80 × 0.7 + 85 × 0.3 = 81.5점
        """
        # 필수 재료만 계산 (선택 재료 제외)
        required_ingredients = self.recipe_ingredients.filter(is_optional=False)
        total_required = required_ingredients.count()
        
        if total_required == 0:
            return 100  # 재료가 없는 레시피
        
        # 보유한 재료 수 계산
        owned_count = required_ingredients.filter(
            ingredient_id__in=user_ingredient_ids
        ).count()
        
        # 부족한 재료 수
        missing_count = total_required - owned_count
        
        # 보유 재료 비율 점수
        ratio_score = (owned_count / total_required) * 100
        
        # 부족 재료 패널티 점수
        if missing_count == 0:
            penalty_score = 100
        elif missing_count == 1:
            penalty_score = 85
        elif missing_count == 2:
            penalty_score = 70
        else:
            penalty_score = 50
        
        # 최종 점수 계산 (가중 평균)
        final_score = (ratio_score * 0.7) + (penalty_score * 0.3)
        
        return final_score

    def calculate_expiry_score(self, user_ingredients_dict):
        """
        유통기한 점수 계산 (추천 점수의 25%)
        
        레시피에 사용되는 각 재료의 긴급도 평균
        
        Args:
            user_ingredients_dict (dict): {ingredient_id: UserIngredient 객체}
        
        Returns:
            float: 유통기한 점수 (20~100)
        
        특징:
            - 모든 재료 동등한 가중치 (주재료/부재료 구분 없음)
            - 유통기한 미입력 재료도 20점으로 포함
            - 유통기한 지남 재료도 20점으로 포함
            - 보유하지 않은 재료는 20점
        
        Example:
            레시피: [밥(미입력, 20점), 김치(D-3, 70점), 계란(D-5, 70점)]
            평균 점수 = (20 + 70 + 70) / 3 = 53.3점
        """
        recipe_ingredients = self.recipe_ingredients.filter(is_optional=False)
        
        if not recipe_ingredients.exists():
            return 20  # 필수 재료가 없는 경우 기본 점수
        
        total_score = 0
        count = 0
        
        for recipe_ing in recipe_ingredients:
            ingredient_id = recipe_ing.ingredient_id
            
            # 사용자가 보유한 재료인지 확인
            if ingredient_id in user_ingredients_dict:
                user_ing = user_ingredients_dict[ingredient_id]
                urgency_score = user_ing.get_urgency_score()
                total_score += urgency_score  # 항상 20~100 반환
            else:
                # 보유하지 않은 재료는 기본 점수
                total_score += 20
            
            count += 1
        
        # 모든 재료의 평균 점수
        return total_score / count if count > 0 else 20

    def calculate_recommendation_score(self, user, user_ingredient_ids, 
                                       user_ingredients_dict, user_skill_level):
        """
        전체 추천 점수 계산
        
        레시픽 추천 로직의 핵심 메서드
        
        Args:
            user: User 객체
            user_ingredient_ids (list): 사용자 보유 식재료 ID 리스트
            user_ingredients_dict (dict): {ingredient_id: UserIngredient}
            user_skill_level (str): 'BEGINNER', 'INTERMEDIATE', 'EXPERT'
        
        Returns:
            dict: {
                'total_score': 총점,
                'ingredient_score': 재료 매칭 점수,
                'expiry_score': 유통기한 점수,
                'difficulty_score': 난이도 점수,
                'personalization_score': 개인화 점수,
                'missing_ingredients_count': 부족한 재료 개수
            }
        
        공식:
            총 추천 점수 = 재료 매칭 점수 × 60%
                        + 유통기한 점수 × 25%
                        + 난이도 점수 × 10%
                        + 개인화 점수 × 5%
        
        유통기한 점수 특징:
            - 사용자가 유통기한을 입력한 재료만 가중치 계산에 포함
            - 유통기한 입력한 재료가 임박할수록 높은 점수
            - 모든 재료가 유통기한 미입력이면 기본 점수(20점) 적용
        """
        from recipes.models import RecipeLog
        
        # 1. 재료 매칭 점수 (60%)
        ingredient_score = self.calculate_ingredient_matching_score(user_ingredient_ids)
        
        # 2. 유통기한 점수 (25%)
        expiry_score = self.calculate_expiry_score(user_ingredients_dict)
        
        # 3. 난이도 점수 (10%)
        difficulty_score = self.get_difficulty_score_for_user(user_skill_level)
        
        # 4. 개인화 점수 (5%)
        personalization_score = RecipeLog.get_personalization_score(user, self)
        
        # 최종 점수 계산 (가중 평균)
        total_score = (
            ingredient_score * 0.60 +
            expiry_score * 0.25 +
            difficulty_score * 0.10 +
            personalization_score * 0.05
        )
        
        return {
            'total_score': round(total_score, 2),
            'ingredient_score': round(ingredient_score, 2),
            'expiry_score': round(expiry_score, 2),
            'difficulty_score': round(difficulty_score, 2),
            'personalization_score': round(personalization_score, 2),
            'missing_ingredients_count': self.recipe_ingredients.filter(
                is_optional=False
            ).exclude(
                ingredient_id__in=user_ingredient_ids
            ).count()
        }

    def get_recommendation_category(self, total_score):
        """
        추천 점수에 따른 카테고리 분류
        
        UI에서 레시피를 섹션별로 나눠서 표시할 때 사용
        
        Args:
            total_score (float): 총 추천 점수
        
        Returns:
            str: 카테고리 코드
                - 'urgent_ready': 90점 이상 (유통기한 임박)
                - 'ready': 75~89점 (지금 바로 가능)
                - 'almost_ready': 60~74점 (재료 1-2개만 있으면)
                - 'not_ready': 60점 미만 (추천 목록에서 제외)
        
        Example:
            if category == 'urgent_ready':
                print("🔥 지금 바로 만들어야 해요!")
            elif category == 'ready':
                print("✨ 지금 바로 만들 수 있어요")
        """
        if total_score >= 90:
            return 'urgent_ready'
        elif total_score >= 75:
            return 'ready'
        elif total_score >= 60:
            return 'almost_ready'
        else:
            return 'not_ready'

    def get_ingredients_status_for_user(self, user_ingredients_dict):
        """
        사용자 보유 재료 상태 정보 반환 (UI용)
        
        프론트엔드에서 뱃지 표시할 때 사용
        
        Args:
            user_ingredients_dict (dict): {ingredient_id: UserIngredient}
        
        Returns:
            dict: {
                'ingredients_status': {
                    ingredient_name: status_code
                },
                'has_expired': bool,
                'has_urgent': bool,
                'expired_ingredients': [재료명 리스트],
                'urgent_ingredients': [재료명 리스트],
                'missing_ingredients': [재료명 리스트]
            }
        
        Status codes:
            - 'expired': 유통기한 지남
            - 'urgent': 매우 긴급 (D-2 이내)
            - 'warning': 긴급 (D-5 이내)
            - 'caution': 주의 (D-10 이내)
            - 'ok': 여유 / 미입력
            - 'missing': 보유하지 않음
        
        Example:
            {
                'ingredients_status': {
                    'eggs': 'expired',
                    'salt': 'ok',
                    'onion': 'missing'
                },
                'has_expired': True,
                'has_urgent': False,
                'expired_ingredients': ['계란'],
                'urgent_ingredients': [],
                'missing_ingredients': ['양파']
            }
        """
        result = {
            'ingredients_status': {},
            'has_expired': False,
            'has_urgent': False,
            'expired_ingredients': [],
            'urgent_ingredients': [],
            'missing_ingredients': []
        }
        
        recipe_ingredients = self.recipe_ingredients.filter(is_optional=False)
        
        for recipe_ing in recipe_ingredients:
            ingredient_id = recipe_ing.ingredient_id
            ingredient_name = recipe_ing.ingredient.name_ko
            
            if ingredient_id in user_ingredients_dict:
                user_ing = user_ingredients_dict[ingredient_id]
                status = user_ing.get_expiry_status()
                
                result['ingredients_status'][ingredient_name] = status
                
                # 유통기한 지남
                if status == 'expired':
                    result['has_expired'] = True
                    result['expired_ingredients'].append(ingredient_name)
                
                # 매우 긴급
                elif status == 'urgent':
                    result['has_urgent'] = True
                    result['urgent_ingredients'].append(ingredient_name)
            else:
                # 보유하지 않은 재료
                result['ingredients_status'][ingredient_name] = 'missing'
                result['missing_ingredients'].append(ingredient_name)
        
        return result

    # ========== Spoonacular API 연동 메서드 ==========
    @classmethod
    def create_from_spoonacular(cls, api_data, ingredient_mapping=None):
        """
        Spoonacular API 응답에서 Recipe 객체 생성
        
        API 데이터를 파싱하여 우리 DB 형식으로 저장
        
        Args:
            api_data (dict): Spoonacular API 응답 JSON
            ingredient_mapping (dict): {api_ingredient_name: IngredientMaster}
        
        Returns:
            Recipe: 생성된 Recipe 객체
        
        API 데이터 구조 예시:
            {
                "id": 12345,
                "title": "Pasta Carbonara",
                "image": "https://...",
                "readyInMinutes": 30,
                "servings": 4,
                "extendedIngredients": [...],
                "analyzedInstructions": [...]
            }
        """
        # 중복 확인 (이미 있으면 가져오고, 없으면 생성)
        recipe, created = cls.objects.get_or_create(
            external_id=str(api_data.get('id')),
            source=RecipeSource.SPOONACULAR,
            defaults={
                'title': api_data.get('title', 'Unknown Recipe'),
                'image_url': api_data.get('image'),
                'ready_minutes': api_data.get('readyInMinutes'),
                'servings': api_data.get('servings', 1),
                'raw_data': api_data,
            }
        )
        
        # instructions 파싱 (조리 단계)
        instructions = []
        analyzed_instructions = api_data.get('analyzedInstructions', [])
        if analyzed_instructions:
            steps = analyzed_instructions[0].get('steps', [])
            for step in steps:
                instructions.append({
                    'step': step.get('number'),
                    'description': step.get('step')
                })
        recipe.instructions = instructions
        
        # 난이도 자동 계산
        recipe.difficulty = recipe.calculate_difficulty()
        recipe.save()
        
        # RecipeIngredient 생성 (ingredient_mapping이 제공된 경우)
        if ingredient_mapping and created:
            from recipes.models import RecipeIngredient
            
            for api_ingredient in api_data.get('extendedIngredients', []):
                ingredient_name = api_ingredient.get('name', '').lower()
                
                # 매핑된 IngredientMaster 찾기
                ingredient_master = ingredient_mapping.get(ingredient_name)
                
                if ingredient_master:
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        ingredient=ingredient_master,
                        ingredient_name=api_ingredient.get('original', ingredient_name),
                        is_optional=False
                    )
        
        return recipe

    @classmethod
    def fetch_and_save_from_spoonacular(cls, recipe_id, api_key, ingredient_mapping=None):
        """
        Spoonacular API에서 레시피 가져와서 저장
        
        API 호출 + 저장을 한 번에 처리
        
        Args:
            recipe_id (int): Spoonacular 레시피 ID
            api_key (str): Spoonacular API 키
            ingredient_mapping (dict): 재료 매핑 딕셔너리
        
        Returns:
            Recipe: 생성/업데이트된 Recipe 객체
        
        Example:
            recipe = Recipe.fetch_and_save_from_spoonacular(
                recipe_id=12345,
                api_key='your_api_key',
                ingredient_mapping=mapping
            )
        """
        import requests
        
        url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
        params = {
            'apiKey': api_key,
            'includeNutrition': False
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        api_data = response.json()
        return cls.create_from_spoonacular(api_data, ingredient_mapping)

    @classmethod
    def get_recommendations_for_user(cls, user, limit=20, min_score=60):
        """
        사용자를 위한 추천 레시피 목록 (점수 순 정렬)
        
        레시픽의 핵심 추천 기능
        사용자 보유 식재료, 알러지, 요리 실력을 고려하여 추천
        
        Args:
            user: User 객체
            limit (int): 반환할 최대 레시피 수
            min_score (int): 최소 추천 점수 (기본 60점)
        
        Returns:
            list: 추천 레시피 리스트 (점수 포함)
            [
                {
                    'recipe': Recipe 객체,
                    'scores': {점수 정보},
                    'category': 'urgent_ready' | 'ready' | 'almost_ready'
                },
                ...
            ]
        
        Example:
            recommendations = Recipe.get_recommendations_for_user(
                user=request.user,
                limit=20,
                min_score=60
            )
            
            for rec in recommendations:
                print(f"{rec['recipe'].title}: {rec['scores']['total_score']}점")
        """
        from ingredients.models import UserIngredient
        
        # 1. 사용자 보유 식재료 조회
        user_ingredients = UserIngredient.objects.filter(
            user=user,
            is_consumed=False  # 아직 사용하지 않은 식재료만
        ).select_related('ingredient')
        
        # ingredient_id 리스트 (재료 매칭용)
        user_ingredient_ids = [ui.ingredient_id for ui in user_ingredients]
        
        # ingredient_id: UserIngredient 딕셔너리 (유통기한 점수용)
        user_ingredients_dict = {ui.ingredient_id: ui for ui in user_ingredients}
        
        # 2. 사용자 프로필 정보
        user_profile = user.profile
        user_skill = user_profile.cooking_level  # 'BEGINNER', 'INTERMEDIATE', 'EXPERT'
        allergies = user_profile.allergies or []  # 알러지 재료 ID 리스트
        banned = user_profile.banned_ingredients or []  # 못먹는 재료 ID 리스트
        
        # 3. 하드 필터 적용 (알러지, 못먹는 재료 제외)
        recipes = cls.objects.filter(
            is_active=True  # 활성화된 레시피만
        ).exclude(
            # 알러지/못먹는 재료를 포함한 레시피는 제외
            recipe_ingredients__ingredient_id__in=allergies + banned
        ).prefetch_related(
            # 성능 최적화: 관련 데이터 미리 로드
            'recipe_ingredients__ingredient'
        ).distinct()
        
        # 4. 각 레시피의 추천 점수 계산
        recommendations = []
        
        for recipe in recipes:
            score_data = recipe.calculate_recommendation_score(
                user=user,
                user_ingredient_ids=user_ingredient_ids,
                user_ingredients_dict=user_ingredients_dict,
                user_skill_level=user_skill
            )
            
            # 최소 점수 이상만 포함
            if score_data['total_score'] >= min_score:
                # 재료 상태 정보 추가 (UI용)
                ingredients_status = recipe.get_ingredients_status_for_user(
                    user_ingredients_dict
                )
                
                recommendations.append({
                    'recipe': recipe,
                    'scores': score_data,
                    'category': recipe.get_recommendation_category(
                        score_data['total_score']
                    ),
                    'ingredients_status': ingredients_status  # UI용 상태 정보
                })
        
        # 5. 정렬
        # 1순위: 총점 (높은 순)
        # 2순위: 유통기한 점수 (높은 순 = 임박한 재료 포함)
        # 3순위: 난이도 쉬운 순 (EASY=1, NORMAL=2, DIFFICULT=3)
        def get_difficulty_value(rec):
            """난이도를 숫자로 변환 (쉬운 것이 작은 값)"""
            difficulty_map = {
                'EASY': 1,
                'NORMAL': 2,
                'DIFFICULT': 3
            }
            return difficulty_map.get(rec['recipe'].difficulty, 2)
        
        recommendations.sort(
            key=lambda x: (
                -x['scores']['total_score'],      # 총점 높은 순 (- 붙여서 내림차순)
                -x['scores']['expiry_score'],     # 유통기한 높은 순
                get_difficulty_value(x)            # 난이도 쉬운 순 (오름차순)
            )
        )
        
        return recommendations[:limit]

    @classmethod
    def search_by_ingredients_spoonacular(cls, ingredient_names, api_key, 
                                         number=10, ranking=1):
        """
        Spoonacular API로 재료 기반 레시피 검색
        
        보유 재료로 만들 수 있는 레시피를 Spoonacular에서 검색
        
        Args:
            ingredient_names (list): 식재료 이름 리스트 (영문)
            api_key (str): Spoonacular API 키
            number (int): 검색할 레시피 수
            ranking (int): 1=보유 재료 최대화, 2=부족 재료 최소화
        
        Returns:
            list: 검색된 레시피 ID 리스트
        
        Example:
            recipe_ids = Recipe.search_by_ingredients_spoonacular(
                ingredient_names=['chicken', 'rice', 'onion'],
                api_key='your_api_key',
                number=10
            )
            # [12345, 67890, ...]
        """
        import requests
        
        url = "https://api.spoonacular.com/recipes/findByIngredients"
        params = {
            'apiKey': api_key,
            'ingredients': ','.join(ingredient_names),
            'number': number,
            'ranking': ranking,
            'ignorePantry': True
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        results = response.json()
        return [recipe['id'] for recipe in results]


class RecipeIngredient(models.Model):
    """
    레시피-식재료 연결 테이블
    
    레시피에 필요한 식재료 목록
    
    Fields:
        recipe_ingredient_id: 레시피 식재료 고유 ID (PK)
        recipe: 어떤 레시피인지
        ingredient: 어떤 식재료인지 (IngredientMaster 참조)
        ingredient_name: API 원본 이름 (보존용)
        is_optional: 선택 재료 여부
    """
    # Primary Key
    recipe_ingredient_id = models.BigAutoField(
        primary_key=True,
        verbose_name='레시피 식재료 ID'
    )
    
    # CASCADE: 레시피 삭제 시 관련 식재료도 함께 삭제
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',  # recipe.recipe_ingredients.all()
        db_column='recipe_id',
        verbose_name='레시피'
    )
    
    # PROTECT: 레시피가 참조하는 식재료는 삭제 불가
    ingredient = models.ForeignKey(
        'ingredients.IngredientMaster',
        on_delete=models.PROTECT,
        related_name='recipe_ingredients',
        db_column='ingredient_id',
        verbose_name='식재료'
    )
    
    # API에서 가져온 원본 이름 보존
    # 예: API는 "cherry tomato", 우리는 "방울토마토"로 매칭
    ingredient_name = models.CharField(
        max_length=100,
        verbose_name='식재료명(API 기준)',
        help_text='원본 API에서 사용하는 이름'
    )
    
    # 선택 재료 여부 (있으면 좋지만 없어도 되는 재료)
    is_optional = models.BooleanField(
        default=False,
        verbose_name='선택 재료 여부'
    )

    class Meta:
        db_table = 'RecipeIngredient'
        verbose_name = '레시피 식재료'
        verbose_name_plural = '레시피 식재료'
        indexes = [
            models.Index(fields=['recipe'], name='idx_recipe_ing_recipe'),
            models.Index(fields=['ingredient'], name='idx_recipe_ing_ingredient'),
        ]
        constraints = [
            # 같은 레시피에 같은 재료 중복 방지
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='uq_recipe_ingredient'
            ),
        ]

    def __str__(self):
        """
        Admin에서 보기 좋게 표시
        예: "김치볶음밥 - 김치"
            "김치볶음밥 - 설탕 (선택)"
        """
        optional = "(선택)" if self.is_optional else ""
        return f"{self.recipe.title} - {self.ingredient.name_ko} {optional}"


class FavoriteRecipe(models.Model):
    """
    사용자 찜한 레시피
    
    사용자가 나중에 만들어보고 싶은 레시피 저장
    
    Fields:
        favorite_id: 찜 고유 ID (PK)
        user: 찜한 사용자
        recipe: 찜한 레시피
        created_at: 찜한 시점
    """
    # Primary Key
    favorite_id = models.BigAutoField(
        primary_key=True,
        verbose_name='찜 ID'
    )
    
    # CASCADE: 사용자 또는 레시피 삭제 시 찜도 함께 삭제
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorite_recipes',  # user.favorite_recipes.all()
        db_column='user_id',
        verbose_name='사용자'
    )
    
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorited_by',  # recipe.favorited_by.all()
        db_column='recipe_id',
        verbose_name='레시피'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='찜한 시점'
    )

    class Meta:
        db_table = 'FavoriteRecipe'
        verbose_name = '찜한 레시피'
        verbose_name_plural = '찜한 레시피'
        indexes = [
            models.Index(fields=['user'], name='idx_favorite_user'),
            models.Index(fields=['recipe'], name='idx_favorite_recipe'),
            # 사용자의 최근 찜한 레시피 조회 시 사용
            models.Index(fields=['user', 'created_at'], name='idx_favorite_user_date'),
        ]
        constraints = [
            # 같은 레시피를 여러 번 찜하는 것 방지
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='uq_user_recipe_favorite'
            ),
        ]

    def __str__(self):
        """Admin에서 '홍길동 ♥ 김치볶음밥' 형태로 표시"""
        return f"{self.user.nickname} ♥ {self.recipe.title}"