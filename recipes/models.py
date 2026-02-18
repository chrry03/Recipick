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
        title_ko: 레시피 제목 (한글) - NEW!
        image_url: 썸네일 이미지
        ready_minutes: 예상 조리 시간
        difficulty: 난이도 (자동 계산)
        servings: 인분
        raw_data: API 원본 데이터 (JSON)
        instructions: 조리 단계 (JSON)
        is_translated: 번역 완료 여부 - NEW!
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
    
    # ============ 한글 제목 (NEW!) ============
    title_ko = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='레시피 제목 (한글)',
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
    # 형식: [{"step": 1, "description": "...", "description_ko": "한글"}, ...]
    instructions = models.JSONField(
        null=True,
        blank=True,
        verbose_name='조리 단계',
        help_text='[{"step": 1, "description": "...", "description_ko": "한글"}, ...] 형식'
    )
    
    # ============ 번역 완료 여부 (NEW!) ============
    is_translated = models.BooleanField(
        default=False,
        verbose_name='번역 완료 여부'
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
            models.Index(fields=['title_ko'], name='idx_recipe_title_ko'),  # NEW!
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
        return f"{self.get_display_title()} ({self.get_difficulty_display()})"

    # ============ 한글 우선 표시 메서드 (NEW!) ============
    def get_display_title(self):
        """한글 제목 우선, 없으면 원본"""
        return self.title_ko if self.title_ko else self.title
    
    def get_display_steps(self):
        """조리 단계 (한글 우선)
        
        Returns:
            [
                {
                    'step': 1,
                    'description': '한글 조리법',  # description_ko 우선
                    'image': '...'
                },
                ...
            ]
        """
        if not self.instructions:
            return []
        
        result = []
        for step_data in self.instructions:
            if isinstance(step_data, dict):
                # description_ko 우선, 없으면 description
                description = step_data.get('description_ko') or step_data.get('description', '')
                
                result.append({
                    'step': step_data.get('step'),
                    'description': description,
                    'image': step_data.get('image')
                })
            else:
                # dict가 아닌 경우 (비정상)
                result.append({
                    'step': len(result) + 1,
                    'description': str(step_data),
                    'image': None
                })
        
        return result

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

    def get_difficulty_display_custom(self):
        """난이도 한글 표시"""
        return dict(DifficultyLevel.choices).get(self.difficulty, '보통')

    def calculate_recommendation_score(self, user, user_ingredient_ids, user_ingredients_dict, user_skill_level):
        """
        레시피 추천 점수 계산 (자취생 친화적 개선 버전)
        
        총점 = 베이스라인(20) + 재료매칭(35%) + 소비기한(35%) + 난이도(15%) + 개인화(15%)
        
        개선사항:
        1. 베이스라인 20점 추가 (기본 점수 보장)
        2. 부족 재료 패널티 대폭 완화
        3. 보유율 계산 더 관대하게
        4. 개인화 점수 상향 (50→70)
        """
        from datetime import date
        
        # 1. 재료 매칭 점수 (35% - 기존 45%에서 하향)
        recipe_ingredients = self.recipe_ingredients.all()
        total_required = recipe_ingredients.count()
        
        if total_required == 0:
            return {
                'total_score': 20,  # 베이스라인만
                'ingredient_score': 0,
                'expiry_score': 0,
                'difficulty_score': 0,
                'personalization_score': 0,
                'missing_ingredients_count': 0
            }
        
        matched = sum(1 for ri in recipe_ingredients if ri.ingredient_id in user_ingredient_ids)
        missing = total_required - matched
        
        # 보유 비율
        match_ratio = (matched / total_required) * 100
        
        # ============ 개선 1: 보유율 기반 점수 (더 관대하게) ============
        if match_ratio >= 80:
            base_score = 100
        elif match_ratio >= 60:
            base_score = 95
        elif match_ratio >= 40:
            base_score = 85
        elif match_ratio >= 30:
            base_score = 75
        elif match_ratio >= 20:
            base_score = 70
        else:
            # 최소 60점 보장 (10% 보유해도 60점!)
            base_score = 60
        
        # ============ 개선 2: 부족 재료 패널티 완화 ============
        if missing == 0:
            missing_penalty = 100
        elif missing == 1:
            missing_penalty = 95  # 85→95
        elif missing == 2:
            missing_penalty = 90  # 70→90
        elif missing == 3:
            missing_penalty = 80  # 50→80
        elif missing == 4:
            missing_penalty = 70  # 50→70
        elif missing == 5:
            missing_penalty = 60  # 50→60
        else:
            # 6개 이상 부족해도 50점
            missing_penalty = 50
        
        # 재료 점수 = (보유비율 기반 × 0.6) + (부족패널티 × 0.4)
        # 기존: 0.7/0.3 → 0.6/0.4로 변경 (패널티 영향 증가)
        ingredient_score = (base_score * 0.6) + (missing_penalty * 0.4)
        
        # 2. 소비기한 점수 (35% - 기존 40%에서 소폭 하향)
        expiry_score = 0
        urgent_count = 0
        very_urgent_count = 0
        
        for ri in recipe_ingredients:
            if ri.ingredient_id in user_ingredients_dict:
                ui = user_ingredients_dict[ri.ingredient_id]
                if ui.expire_at:
                    days_left = (ui.expire_at - date.today()).days
                    
                    if days_left <= 2:
                        # 매우 긴급 (D-2 이하)
                        expiry_score += 120
                        urgent_count += 1
                        very_urgent_count += 1
                    elif days_left <= 5:
                        # 긴급 (D-3~5)
                        expiry_score += 80
                        urgent_count += 1
                    elif days_left <= 10:
                        # 주의 (D-6~10)
                        expiry_score += 50  # 45→50
                    else:
                        # 여유 (D-11 이상)
                        expiry_score += 30  # 20→30
                else:
                    # 소비기한 미입력 (더 관대하게)
                    expiry_score += 30  # 20→30
        
        if matched > 0:
            expiry_score = expiry_score / matched
            # 매우 긴급 재료 보너스
            if very_urgent_count > 0:
                expiry_score = min(130, expiry_score + (very_urgent_count * 5))
        else:
            # 보유 재료 0개여도 기본 점수
            expiry_score = 20
        
        # 3. 난이도 점수 (15% - 기존 10%에서 상향)
        difficulty_map = {'EASY': 1, 'NORMAL': 2, 'DIFFICULT': 3}
        skill_map = {'BEGINNER': 1, 'INTERMEDIATE': 2, 'ADVANCED': 3}
        
        recipe_diff = difficulty_map.get(self.difficulty, 2)
        user_skill = skill_map.get(user_skill_level, 2)
        
        diff_gap = abs(recipe_diff - user_skill)
        
        # ============ 개선 3: 난이도 패널티 완화 ============
        if diff_gap == 0:
            difficulty_score = 100
        elif diff_gap == 1:
            difficulty_score = 80  # 70→80
        else:
            difficulty_score = 60  # 40→60
        
        # 4. 개인화 점수 (15% - 기존 5%에서 대폭 상향!)
        # ============ 개선 4: 개인화 점수 상향 ============
        personalization_score = 70  # 50→70
        
        # 보너스 요소
        # TODO: 찜한 레시피 유사도, 자주 만드는 스타일 등 추가 가능
        # personalization_score += 10  (향후 확장)
        
        # ============ 개선 5: 총점 계산 (베이스라인 추가!) ============
        # 베이스라인 20점 + 가중치 합
        base_line = 20
        
        weighted_score = (
            ingredient_score * 0.45 +      # 45%
            expiry_score * 0.40 +          # 40%
            difficulty_score * 0.10 +      # 10%
            personalization_score * 0.05   # 5%
        )
        
        total_score = base_line + weighted_score
        
        # 최대 120점 제한 (임박 재료 보너스 고려)
        total_score = min(120, total_score)
        
        return {
            'total_score': round(total_score, 2),
            'ingredient_score': round(ingredient_score, 2),
            'expiry_score': round(expiry_score, 2),
            'difficulty_score': round(difficulty_score, 2),
            'personalization_score': round(personalization_score, 2),
            'missing_ingredients_count': missing,
            'urgent_ingredients_count': urgent_count,
            'base_line': base_line
        }
    
    def get_recommendation_category(self, total_score):
        """점수에 따른 카테고리 분류 (기준 완화)"""
        if total_score >= 85:  # 90→85
            return 'urgent_ready'
        elif total_score >= 70:  # 75→70
            return 'ready'
        elif total_score >= 55:  # 60→55
            return 'almost_ready'
        else:
            return None
    
    def get_ingredients_status_for_user(self, user_ingredients_dict):
        """사용자 보유 재료 상태 (식재료 이름으로 키 사용)"""
        from datetime import date
        
        result = {
            'has_expired': False,
            'has_urgent': False,
            'ingredients_status': {},
            'expired_ingredients': [],
            'urgent_ingredients': []
        }
        
        for ri in self.recipe_ingredients.all():
            ing_id = ri.ingredient_id
            
            # ============ 개선: ingredient가 None인 경우 안전 처리 ============
            if not ri.ingredient:
                # ingredient가 연결 안 된 경우 (드물지만 발생 가능)
                ing_name = ri.ingredient_name or f"식재료_{ing_id}"
            else:
                # 정상적으로 연결된 경우
                ing_name = ri.ingredient.name_ko or ri.ingredient.name_en or ri.ingredient_name or str(ing_id)
            
            if ing_id in user_ingredients_dict:
                ui = user_ingredients_dict[ing_id]
                status = {
                    'is_owned': True,
                    'expire_at': ui.expire_at.isoformat() if ui.expire_at else None,
                    'is_expired': False,
                    'is_urgent': False,
                    'days_left': None
                }
                
                if ui.expire_at:
                    days_left = (ui.expire_at - date.today()).days
                    status['days_left'] = days_left
                    
                    if days_left < 0:
                        status['is_expired'] = True
                        result['has_expired'] = True
                        result['expired_ingredients'].append(ing_name)
                    elif days_left <= 3:
                        status['is_urgent'] = True
                        result['has_urgent'] = True
                        result['urgent_ingredients'].append(ing_name)
                
                result['ingredients_status'][ing_name] = status
            else:
                result['ingredients_status'][ing_name] = {
                    'is_owned': False,
                    'expire_at': None,
                    'is_expired': False,
                    'is_urgent': False,
                    'days_left': None
                }
        
        return result

    @classmethod
    def create_from_spoonacular(cls, api_data, ingredient_mapping=None):
        """Spoonacular API 응답으로 Recipe 객체 생성"""
        from ingredients.models import IngredientMaster
        
        external_id = str(api_data.get('id', ''))
        title = api_data.get('title', 'Unknown Recipe')
        image = api_data.get('image', '')
        ready_minutes = api_data.get('readyInMinutes')
        servings = api_data.get('servings', 1)
        
        # 난이도 계산
        steps = api_data.get('analyzedInstructions', [])
        step_count = sum(len(inst.get('steps', [])) for inst in steps)
        
        if step_count <= 5:
            difficulty = 'EASY'
        elif step_count <= 10:
            difficulty = 'NORMAL'
        else:
            difficulty = 'DIFFICULT'
        
        # instructions JSON 생성
        instructions_list = []
        for instruction_group in steps:
            for step in instruction_group.get('steps', []):
                instructions_list.append({
                    'step': step.get('number'),
                    'description': step.get('step', ''),
                    'image': None
                })
        
        # Recipe 생성
        recipe = cls.objects.create(
            external_id=external_id,
            source='spoonacular',
            title=title,
            image_url=image,
            ready_minutes=ready_minutes,
            difficulty=difficulty,
            servings=servings,
            raw_data=api_data,
            instructions=instructions_list,
            is_active=True
        )
        
        # RecipeIngredient 생성
        extended_ingredients = api_data.get('extendedIngredients', [])
        
        for ing_data in extended_ingredients:
            ing_name = ing_data.get('name', '').lower().strip()
            
            # ingredient_mapping으로 IngredientMaster 찾기
            ing_master = None
            if ingredient_mapping and ing_name in ingredient_mapping:
                try:
                    ing_master = IngredientMaster.objects.get(
                        ingredient_id=ingredient_mapping[ing_name]
                    )
                except IngredientMaster.DoesNotExist:
                    pass
            
            # 찾지 못하면 이름으로 검색
            if not ing_master:
                ing_master = IngredientMaster.objects.filter(
                    name_en__icontains=ing_name
                ).first()
            
            # 그래도 없으면 기타 카테고리로 생성
            if not ing_master:
                from ingredients.models import IngredientCategory
                other_category = IngredientCategory.objects.filter(
                    name='기타'
                ).first()
                
                if not other_category:
                    other_category = IngredientCategory.objects.create(
                        name='기타',
                        icon='🍴'
                    )
                
                ing_master = IngredientMaster.objects.create(
                    category=other_category,
                    name_ko=ing_name.capitalize(),
                    name_en=ing_name
                )
            
            # RecipeIngredient 생성
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ing_master,
                ingredient_name=ing_data.get('original', ing_name),
                is_optional=False
            )
        
        # 캐싱 필드 업데이트
        recipe.total_ingredients = recipe.recipe_ingredients.count()
        recipe.required_ingredients = recipe.recipe_ingredients.filter(
            is_optional=False
        ).count()
        recipe.save()
        
        return recipe

    @classmethod
    def fetch_from_spoonacular_by_id(cls, recipe_id, api_key, ingredient_mapping=None):
        """Spoonacular API로 특정 레시피 ID 가져오기"""
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
    def get_recommendations_for_user(cls, user, limit=20, min_score=55):
        """사용자를 위한 추천 레시피 목록 (기준 점수 55점으로 완화)"""
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
        
        # 정렬: 총점 → 소비기한 → 난이도 쉬운 순
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
            return results
        
        except Timeout:
            print(f"❌ Spoonacular API 시간 초과")
            return []
        except RequestException as e:
            print(f"❌ Spoonacular 재료 검색 실패: {e}")
            return []
        
    def update_ingredient_counts(self, save=True):
        """
        RecipeIngredient 기준으로
        - 전체 재료 수
        - 필수 재료 수
        를 갱신한다.
        """
        qs = self.recipe_ingredients.all()

        self.total_ingredients = qs.count()
        self.required_ingredients = qs.filter(is_optional=False).count()

        if save:
            self.save(update_fields=[
                'total_ingredients',
                'required_ingredients'
            ])


class RecipeIngredient(models.Model):
    """레시피-식재료 연결 테이블
    
    ⚠️ 주의: 수량/단위 필드 없음!
    - 식재료 유무만 체크
    - 마지막에 소진 여부만 확인
    """
    
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
        max_length=255,
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
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='uq_user_recipe_favorite'
            ),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.recipe.get_display_title()}"