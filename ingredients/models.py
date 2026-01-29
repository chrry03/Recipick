"""
Ingredients App Models
식재료 관련 모델 정의

이 파일은 사용자가 보유한 식재료와 식재료 마스터 데이터를 관리합니다.
- IngredientCategory: 식재료 카테고리 (대/소분류) -> 아이콘 관리 포함
- IngredientMaster: 표준 식재료 목록 -> 영문명(API용) 포함
- UserIngredient: 사용자 냉장고 식재료
"""
from django.db import models
from django.conf import settings

# Create your models here.
class IngredientCategory(models.Model):
    """
    식재료 카테고리 (대분류/소분류 계층 구조)
    
    자기 참조 ForeignKey를 사용하여 계층 구조 구현
    예: 채소(대분류) > 잎채소(소분류)
        육류(대분류) > 소고기(소분류)
    
    Fields:
        category_id: 카테고리 고유 ID (PK)
        parent: 상위 카테고리 (None이면 대분류)
        name: 카테고리명
        icon_url: 카테고리 대표 아이콘 (개별 식재료 대신 카테고리별로 관리)
    """
    # Primary Key
    category_id = models.BigAutoField(
        primary_key=True,
        verbose_name='카테고리 ID'
    )
    
    # 자기 자신을 참조하는 ForeignKey (계층 구조)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories',
        db_column='parent_id',
        verbose_name='상위 카테고리'
    )
    
    name = models.CharField(
        max_length=50,
        verbose_name='카테고리명'
    )

    # 카테고리 대표 아이콘
    icon_url = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='카테고리 아이콘 URL'
    )

    class Meta:
        db_table = 'IngredientCategory'
        verbose_name = '식재료 카테고리'
        verbose_name_plural = '식재료 카테고리'
        indexes = [
            models.Index(fields=['parent'], name='idx_category_parent'),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    @property
    def is_parent(self):
        """대분류 여부"""
        return self.parent is None

    @property
    def full_path(self):
        """전체 경로 반환 (대분류 > 소분류)"""
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    @property
    def display_icon(self):
        """표시할 아이콘 (자신 or 부모)"""
        if self.icon_url:
            return self.icon_url
        if self.parent and self.parent.icon_url:
            return self.parent.icon_url
        return None


class IngredientMaster(models.Model):
    """
    식재료 마스터 데이터
    
    서비스에서 제공하는 표준 식재료 목록
    사용자가 식재료를 등록할 때 이 목록에서 선택
    
    Fields:
        ingredient_id: 식재료 고유 ID (PK)
        category: 소속 카테고리
        name_ko: 한글 식재료명
        name_en: 영문 식재료명 (Spoonacular API 매핑용)
        aliases: 별칭/번역 JSON
    """
    # Primary Key
    ingredient_id = models.BigAutoField(
        primary_key=True,
        verbose_name='식재료 ID'
    )
    
    # 카테고리와의 관계
    category = models.ForeignKey(
        IngredientCategory,
        on_delete=models.PROTECT,
        related_name='ingredients',
        db_column='category_id',
        verbose_name='카테고리'
    )
    
    # 한글 식재료명
    name_ko = models.CharField(
        max_length=50,
        verbose_name='한글명',
        db_index=True
    )

    # Spoonacular API 매핑용 공식 영문명
    name_en = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='영문명',
        help_text='Spoonacular API 매핑용 공식 영문명'
    )
    
    # 여러 이름을 배열로 저장
    aliases = models.JSONField(
        null=True,
        blank=True,
        verbose_name='별칭/번역',
        help_text='["토마토", "tomato"] 형식'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='등록일시'
    )

    class Meta:
        db_table = 'IngredientMaster'
        verbose_name = '식재료 마스터'
        verbose_name_plural = '식재료 마스터'
        indexes = [
            models.Index(fields=['category'], name='idx_ingredient_category'),
            models.Index(fields=['name_ko'], name='idx_ingredient_name'),
            models.Index(fields=['name_en'], name='idx_ingredient_name_en'),
        ]

    def __str__(self):
        return f"{self.name_ko} ({self.category.name})"

    @property
    def icon(self):
        """카테고리의 아이콘 반환"""
        return self.category.display_icon

    def get_all_names(self):
        """
        모든 이름 반환 (한글명 + 영문명 + 별칭)
        
        검색 시 유용
        """
        names = [self.name_ko]
        if self.name_en:
            names.append(self.name_en)
        if self.aliases:
            names.extend(self.aliases)
        return names

    @classmethod
    def find_by_name(cls, name):
        """이름으로 식재료 찾기 (한글명, 영문명, 별칭)"""
        name_lower = name.lower().strip()
        
        # 1. 한글명/영문명으로 검색
        from django.db.models import Q
        try:
            return cls.objects.get(
                Q(name_ko__iexact=name) | Q(name_en__iexact=name)
            )
        except cls.DoesNotExist:
            pass
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(
                Q(name_ko__iexact=name) | Q(name_en__iexact=name)
            ).first()
        
        # 2. aliases에서 검색
        ingredients = cls.objects.all()
        for ingredient in ingredients:
            if ingredient.aliases:
                aliases_lower = [alias.lower() for alias in ingredient.aliases]
                if name_lower in aliases_lower:
                    return ingredient
        
        return None

    @classmethod
    def create_ingredient_mapping_for_api(cls):
        """API 응답의 재료명을 IngredientMaster와 매칭하는 딕셔너리 생성"""
        mapping = {}
        
        for ingredient in cls.objects.all():
            mapping[ingredient.name_ko.lower()] = ingredient
            
            if ingredient.name_en:
                mapping[ingredient.name_en.lower()] = ingredient

            if ingredient.aliases:
                for alias in ingredient.aliases:
                    mapping[alias.lower()] = ingredient
        
        return mapping


class UserIngredient(models.Model):
    """
    사용자 보유 식재료
    
    사용자 냉장고에 있는 식재료 관리
    유통기한, 소비 여부 등을 추적
    
    Fields:
        user_ingredient_id: 사용자 식재료 고유 ID (PK)
        user: 소유자
        ingredient: 어떤 식재료인지 (IngredientMaster 참조)
        expire_at: 유통기한 (선택, 입력 시 추천 가중치에 반영)
        is_consumed: 사용 완료 여부
    """
    # Primary Key
    user_ingredient_id = models.BigAutoField(
        primary_key=True,
        verbose_name='사용자 식재료 ID'
    )
    
    # 사용자와의 관계
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ingredients',
        db_column='user_id',
        verbose_name='사용자'
    )
    
    # 식재료 마스터와의 관계
    ingredient = models.ForeignKey(
        IngredientMaster,
        on_delete=models.PROTECT,
        related_name='user_ingredients',
        db_column='ingredient_id',
        verbose_name='식재료'
    )
    
    # 유통기한 (선택 사항)
    expire_at = models.DateField(
        null=True,
        blank=True,
        verbose_name='유통기한',
        help_text='입력 안하면 가중치 제외'
    )
    
    # 사용 완료 여부
    is_consumed = models.BooleanField(
        default=False,
        verbose_name='사용 완료 여부'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='추가일시'
    )
    
    # 수정 시점 자동 갱신
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )

    class Meta:
        db_table = 'UserIngredient'
        verbose_name = '사용자 식재료'
        verbose_name_plural = '사용자 식재료'
        indexes = [
            models.Index(fields=['user'], name='idx_user_ingredient_user'),
            models.Index(fields=['ingredient'], name='idx_user_ingredient_ing'),
            models.Index(fields=['expire_at'], name='idx_user_ingredient_expire'),
            models.Index(
                fields=['user', 'is_consumed'],
                name='idx_user_ingredient_active'
            ),
        ]

    def __str__(self):
        status = "✓" if self.is_consumed else "○"
        return f"{status} {self.user.nickname} - {self.ingredient.name_ko}"

    @property
    def is_expiring_soon(self):
        """유통기한 임박 여부 (3일 이내)"""
        if not self.expire_at:
            return False
        from datetime import date, timedelta
        return self.expire_at <= date.today() + timedelta(days=3)

    @property
    def is_expired(self):
        """유통기한 만료 여부"""
        if not self.expire_at:
            return False
        from datetime import date
        return self.expire_at < date.today()

    @property
    def days_until_expiry(self):
        """유통기한까지 남은 일수"""
        if not self.expire_at:
            return None
        from datetime import date
        delta = self.expire_at - date.today()
        return delta.days

    def get_urgency_score(self):
        """유통기한 긴급도 점수 계산"""
        days = self.days_until_expiry
        
        if days is None or days < 0:
            return 20
        
        if days <= 2:
            return 100
        elif days <= 5:
            return 70
        elif days <= 10:
            return 40
        else:
            return 20

    def get_expiry_status(self):
        """유통기한 상태 반환 (UI 표시용)"""
        days = self.days_until_expiry
        
        if days is None:
            return 'unknown'
        if days < 0:
            return 'expired'
        if days <= 2:
            return 'urgent'
        if days <= 5:
            return 'warning'
        if days <= 10:
            return 'caution'
        return 'ok'

    @classmethod
    def get_expiring_soon_ingredients(cls, user, days_threshold=3):
        """유통기한 임박 식재료 조회 (알림용)"""
        from datetime import date, timedelta
        
        threshold_date = date.today() + timedelta(days=days_threshold)
        
        return cls.objects.filter(
            user=user,
            is_consumed=False,
            expire_at__isnull=False,
            expire_at__lte=threshold_date,
            expire_at__gte=date.today()
        ).select_related('ingredient').order_by('expire_at')

    @classmethod
    def get_expired_ingredients(cls, user):
        """유통기한 지난 식재료 조회"""
        from datetime import date
        
        return cls.objects.filter(
            user=user,
            is_consumed=False,
            expire_at__isnull=False,
            expire_at__lt=date.today()
        ).select_related('ingredient').order_by('expire_at')

    def get_notification_message(self):
        """알림 메시지 생성"""
        days = self.days_until_expiry
        ingredient_name = self.ingredient.name_ko
        
        if days is None:
            return ""
        
        if days < 0:
            return f"⚠️ {ingredient_name}의 유통기한이 지났습니다!"
        elif days == 0:
            return f"🔥 {ingredient_name}의 유통기한이 오늘까지입니다!"
        elif days <= 2:
            return f"🔥 {ingredient_name}의 유통기한이 {days}일 남았습니다!"
        elif days <= 5:
            return f"⚡ {ingredient_name}의 유통기한이 {days}일 남았습니다!"
        else:
            return f"ℹ️ {ingredient_name}의 유통기한이 {days}일 남았습니다!"

    def mark_as_consumed(self):
        """식재료 사용 처리"""
        self.is_consumed = True
        self.save(update_fields=['is_consumed', 'updated_at'])