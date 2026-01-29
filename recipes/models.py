"""
Recipes App Models
레시피 관련 모델 정의

이 파일은 레시피, 찜 기능을 관리합니다.
- Recipe: 레시피 정보
- RecipeIngredient: 레시피에 필요한 식재료
- FavoriteRecipe: 사용자가 찜한 레시피
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings

# Create your models here.
# ==================== Enum 정의 ====================
class DifficultyLevel(models.TextChoices):
    EASY = 'EASY', '쉬움'
    NORMAL = 'NORMAL', '보통'
    DIFFICULT = 'DIFFICULT', '어려움'


class RecipeSource(models.TextChoices):
    SPOONACULAR = 'spoonacular', 'Spoonacular'
    KOREAN_FOOD = 'korean_food', '한식 DB'
    USER_CREATED = 'user_created', '사용자 생성'
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
        difficulty: 난이도 (자동 계산)
        servings: 인분
        raw_data: API 원본 데이터 (JSON)
        instructions: 조리 단계 (JSON)
        total_ingredients: 전체 재료 수 (IntegerField)
        required_ingredients: 필수 재료 수 (IntegerField)
        is_active: 활성 상태
    """
    # Primary Key
    recipe_id = models.BigAutoField(
        primary_key=True,
        verbose_name='레시피 ID'
    )
    
    # 외부 API ID
    external_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='외부 API ID',
        help_text='Spoonacular ID 등'
    )
    
    # 레시피 출처
    source = models.CharField(
        max_length=50,
        choices=RecipeSource.choices,
        verbose_name='출처'
    )
    
    # 레시피 제목 (검색용 인덱스)
    title = models.CharField(
        max_length=200,
        verbose_name='레시피 제목',
        db_index=True
    )
    
    image_url = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='썸네일 이미지'
    )
    
    # 예상 조리 시간
    ready_minutes = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name='예상 조리시간(분)'
    )
    
    # 난이도 (자동 계산)
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
    raw_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='API 원본 데이터'
    )
    
    # 조리 단계 (JSON 배열)
    instructions = models.JSONField(
        null=True,
        blank=True,
        verbose_name='조리 단계',
        help_text='[{"step": 1, "description": "..."}, ...] 형식'
    )
    
    # 활성 상태
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성 상태',
        help_text='추천 목록에 표시 여부'
    )
    
    # ========== 성능 최적화 캐싱 필드 (IntegerField) ==========
    total_ingredients = models.IntegerField(
        default=0,
        verbose_name='전체 재료 수',
        help_text='RecipeIngredient 저장 시 자동 업데이트'
    )
    
    required_ingredients = models.IntegerField(
        default=0,
        verbose_name='필수 재료 수',
        help_text='선택 재료 제외한 필수 재료 수'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='캐싱/등록 시점'
    )
    
    # 수정 시점 자동 갱신
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )

    class Meta:
        db_table = 'Recipe'
        verbose_name = '레시피'
        verbose_name_plural = '레시피'
        indexes = [
            models.Index(fields=['source'], name='idx_recipe_source'),
            models.Index(fields=['difficulty'], name='idx_recipe_difficulty'),
            models.Index(fields=['ready_minutes'], name='idx_recipe_time'),
            models.Index(fields=['title'], name='idx_recipe_title'),
            models.Index(fields=['external_id', 'source'], name='idx_recipe_external_source'),
            models.Index(fields=['is_active'], name='idx_recipe_active'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(ready_minutes__gte=0),
                name='chk_ready_minutes_positive'
            ),
            models.UniqueConstraint(
                fields=['external_id', 'source'],
                name='uq_external_id_source',
                condition=models.Q(external_id__isnull=False)
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_difficulty_display()})"

    @property
    def step_count(self):
        """조리 단계 수"""
        if not self.instructions:
            return 0
        return len(self.instructions)

    @property
    def total_ingredients_count(self):
        """필요한 식재료 개수 (캐싱값 사용)"""
        return self.total_ingredients

    @property
    def required_ingredients_count(self):
        """필수 식재료 개수 (캐싱값 사용)"""
        return self.required_ingredients

    def update_ingredient_counts(self):
        """재료 개수 캐싱 필드 업데이트"""
        self.total_ingredients = self.recipe_ingredients.count()
        self.required_ingredients = self.recipe_ingredients.filter(is_optional=False).count()
        self.save(update_fields=['total_ingredients', 'required_ingredients'])

    def calculate_difficulty(self):
        """단계 수와 조리 시간 기반 난이도 자동 계산"""
        step_count = self.step_count
        ready_time = self.ready_minutes or 30
        
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
        
        final_score = (step_score * 0.6) + (time_score * 0.4)
        
        if final_score <= 1.5:
            return DifficultyLevel.EASY
        elif final_score <= 2.4:
            return DifficultyLevel.NORMAL
        else:
            return DifficultyLevel.DIFFICULT

    def get_difficulty_score_for_user(self, user_skill_level):
        """사용자 실력에 따른 난이도 점수 계산"""
        difficulty_map = {
            DifficultyLevel.EASY: 1,
            DifficultyLevel.NORMAL: 2,
            DifficultyLevel.DIFFICULT: 3
        }
        skill_map = {
            'BEGINNER': 1,
            'INTERMEDIATE': 2,
            'EXPERT': 3
        }
        recipe_difficulty = difficulty_map.get(self.difficulty, 2)
        user_skill = skill_map.get(user_skill_level, 1)
        
        score = 100 - abs(user_skill - recipe_difficulty) * 30
        return max(0, score)

    def calculate_ingredient_matching_score(self, user_ingredient_ids):
        """재료 매칭 점수 계산 (60%)"""
        required_ingredients = self.recipe_ingredients.filter(is_optional=False)
        total_required = required_ingredients.count()
        
        if total_required == 0:
            return 100
        
        owned_count = required_ingredients.filter(
            ingredient_id__in=user_ingredient_ids
        ).count()
        
        missing_count = total_required - owned_count
        
        ratio_score = (owned_count / total_required) * 100
        
        if missing_count == 0:
            penalty_score = 100
        elif missing_count == 1:
            penalty_score = 85
        elif missing_count == 2:
            penalty_score = 70
        else:
            penalty_score = 50
        
        final_score = (ratio_score * 0.7) + (penalty_score * 0.3)
        return final_score

    def calculate_expiry_score(self, user_ingredients_dict):
        """유통기한 점수 계산 (25%)"""
        recipe_ingredients = self.recipe_ingredients.filter(is_optional=False)
        
        if not recipe_ingredients.exists():
            return 20
        
        total_score = 0
        count = 0
        
        for recipe_ing in recipe_ingredients:
            ingredient_id = recipe_ing.ingredient_id
            
            if ingredient_id in user_ingredients_dict:
                user_ing = user_ingredients_dict[ingredient_id]
                urgency_score = user_ing.get_urgency_score()
                total_score += urgency_score
            else:
                total_score += 20
            
            count += 1
        
        return total_score / count if count > 0 else 20

    def calculate_recommendation_score(self, user, user_ingredient_ids, 
                                       user_ingredients_dict, user_skill_level):
        """전체 추천 점수 계산"""
        ingredient_score = self.calculate_ingredient_matching_score(user_ingredient_ids)
        expiry_score = self.calculate_expiry_score(user_ingredients_dict)
        difficulty_score = self.get_difficulty_score_for_user(user_skill_level)
        
        # MVP에서는 개인화 점수 고정값 (일지 기능 제외)
        personalization_score = 50
        
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
        """추천 점수에 따른 카테고리 분류"""
        if total_score >= 90:
            return 'urgent_ready'
        elif total_score >= 75:
            return 'ready'
        elif total_score >= 60:
            return 'almost_ready'
        else:
            return 'not_ready'

    def get_ingredients_status_for_user(self, user_ingredients_dict):
        """사용자 보유 재료 상태 정보 반환 (UI용)"""
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
                
                if status == 'expired':
                    result['has_expired'] = True
                    result['expired_ingredients'].append(ingredient_name)
                elif status == 'urgent':
                    result['has_urgent'] = True
                    result['urgent_ingredients'].append(ingredient_name)
            else:
                result['ingredients_status'][ingredient_name] = 'missing'
                result['missing_ingredients'].append(ingredient_name)
        
        return result

    # ========== Spoonacular API 연동 ==========
    @classmethod
    def create_from_spoonacular(cls, api_data, ingredient_mapping=None):
        """Spoonacular API 응답에서 Recipe 객체 생성"""
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
        
        # instructions 파싱
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
        
        # RecipeIngredient 생성
        if ingredient_mapping and created:
            for api_ingredient in api_data.get('extendedIngredients', []):
                # nameClean이 가장 정확한 재료명
                ingredient_name = api_ingredient.get('nameClean') or api_ingredient.get('name', '').lower()
                
                ingredient_master = ingredient_mapping.get(ingredient_name)
                
                if ingredient_master:
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        ingredient=ingredient_master,
                        ingredient_name=api_ingredient.get('original', ingredient_name),
                        is_optional=False
                    )
            
            # 재료 개수 캐싱
            recipe.update_ingredient_counts()
        
        return recipe

    @classmethod
    def fetch_and_save_from_spoonacular(cls, recipe_id, api_key, ingredient_mapping=None):
        """Spoonacular API에서 레시피 가져와서 저장 (timeout 추가)"""
        import requests
        from requests.exceptions import Timeout, RequestException

        url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
        params = {
            'apiKey': api_key,
            'includeNutrition': False
        }
        
        try:
            # timeout=5로 서버 멈춤 방지
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            api_data = response.json()
            return cls.create_from_spoonacular(api_data, ingredient_mapping)
        
        except Timeout:
            print(f"❌ Spoonacular API 시간 초과 (ID: {recipe_id})")
            return None
        except RequestException as e:
            print(f"❌ Spoonacular API 요청 실패: {e}")
            return None

    @classmethod
    def get_recommendations_for_user(cls, user, limit=20, min_score=60):
        """사용자를 위한 추천 레시피 목록"""
        from ingredients.models import UserIngredient
        
        # 비로그인 사용자
        if user is None or not user.is_authenticated:
            recipes = cls.objects.filter(is_active=True)[:limit]
            return [{'recipe': recipe, 'scores': None, 'category': None} for recipe in recipes]
        
        # 로그인 사용자: 추천 로직 적용
        user_ingredients = UserIngredient.objects.filter(
            user=user,
            is_consumed=False
        ).select_related('ingredient')
        
        user_ingredient_ids = [ui.ingredient_id for ui in user_ingredients]
        user_ingredients_dict = {ui.ingredient_id: ui for ui in user_ingredients}
        
        user_profile = user.profile
        user_skill = user_profile.cooking_level
        allergies = user_profile.allergies or []
        banned = user_profile.banned_ingredients or []
        
        # 하드 필터
        recipes = cls.objects.filter(
            is_active=True
        ).exclude(
            recipe_ingredients__ingredient_id__in=allergies + banned
        ).prefetch_related(
            'recipe_ingredients__ingredient'
        ).distinct()
        
        # 추천 점수 계산
        recommendations = []
        
        for recipe in recipes:
            score_data = recipe.calculate_recommendation_score(
                user=user,
                user_ingredient_ids=user_ingredient_ids,
                user_ingredients_dict=user_ingredients_dict,
                user_skill_level=user_skill
            )
            
            if score_data['total_score'] >= min_score:
                ingredients_status = recipe.get_ingredients_status_for_user(
                    user_ingredients_dict
                )
                
                recommendations.append({
                    'recipe': recipe,
                    'scores': score_data,
                    'category': recipe.get_recommendation_category(
                        score_data['total_score']
                    ),
                    'ingredients_status': ingredients_status
                })
        
        # 정렬: 총점 → 유통기한 → 난이도 쉬운 순
        def get_difficulty_value(rec):
            difficulty_map = {
                'EASY': 1,
                'NORMAL': 2,
                'DIFFICULT': 3
            }
            return difficulty_map.get(rec['recipe'].difficulty, 2)
        
        recommendations.sort(
            key=lambda x: (
                -x['scores']['total_score'],
                -x['scores']['expiry_score'],
                get_difficulty_value(x)
            )
        )
        
        return recommendations[:limit]

    @classmethod
    def search_by_ingredients_spoonacular(cls, ingredient_names, api_key, 
                                          number=10, ranking=1):
        """Spoonacular API로 재료 기반 레시피 검색"""
        import requests
        from requests.exceptions import Timeout, RequestException
        
        url = "https://api.spoonacular.com/recipes/findByIngredients"
        params = {
            'apiKey': api_key,
            'ingredients': ','.join(ingredient_names),
            'number': number,
            'ranking': ranking,
            'ignorePantry': True
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            results = response.json()
            return [recipe['id'] for recipe in results]
        
        except (Timeout, RequestException) as e:
            print(f"❌ Spoonacular 재료 검색 실패: {e}")
            return []


class RecipeIngredient(models.Model):
    """레시피-식재료 연결 테이블"""
    
    recipe_ingredient_id = models.BigAutoField(
        primary_key=True,
        verbose_name='레시피 식재료 ID'
    )
    
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        db_column='recipe_id',
        verbose_name='레시피'
    )
    
    ingredient = models.ForeignKey(
        'ingredients.IngredientMaster',
        on_delete=models.PROTECT,
        related_name='recipe_ingredients',
        db_column='ingredient_id',
        verbose_name='식재료'
    )
    
    ingredient_name = models.CharField(
        max_length=100,
        verbose_name='식재료명(API 기준)',
        help_text='원본 API에서 사용하는 이름'
    )
    
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
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='uq_recipe_ingredient'
            ),
        ]

    def __str__(self):
        optional = "(선택)" if self.is_optional else ""
        return f"{self.recipe.title} - {self.ingredient.name_ko} {optional}"


class FavoriteRecipe(models.Model):
    """사용자 찜한 레시피"""
    
    favorite_id = models.BigAutoField(
        primary_key=True,
        verbose_name='찜 ID'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorite_recipes',
        db_column='user_id',
        verbose_name='사용자'
    )
    
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorited_by',
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
            models.Index(fields=['user', 'created_at'], name='idx_favorite_user_date'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='uq_user_recipe_favorite'
            ),
        ]

    def __str__(self):
        return f"{self.user.nickname} ♥ {self.recipe.title}"