"""
Ingredients App Models
식재료 관련 모델 정의

이 파일은 사용자가 보유한 식재료와 식재료 마스터 데이터를 관리합니다.
- IngredientCategory: 식재료 카테고리 (대/소분류)
- IngredientMaster: 표준 식재료 목록
- UserIngredient: 사용자 냉장고 식재료
"""
from django.db import models
from django.core.validators import MinValueValidator
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
    """
    # Primary Key
    category_id = models.BigAutoField(
        primary_key=True,
        verbose_name='카테고리 ID'
    )
    
    # 자기 자신을 참조하는 ForeignKey (계층 구조)
    # null=True: 대분류는 부모가 없음
    # CASCADE: 부모 삭제 시 자식도 함께 삭제
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories',  # 부모.subcategories.all()로 자식 접근
        db_column='parent_id',
        verbose_name='상위 카테고리'
    )
    
    name = models.CharField(
        max_length=50,
        verbose_name='카테고리명'
    )

    class Meta:
        db_table = 'IngredientCategory'
        verbose_name = '식재료 카테고리'
        verbose_name_plural = '식재료 카테고리'
        indexes = [
            # parent로 자주 조회하므로 인덱스 추가 (성능 향상)
            models.Index(fields=['parent'], name='idx_category_parent'),
        ]

    def __str__(self):
        """Admin이나 shell에서 보기 좋게 표시"""
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    @property
    def is_parent(self):
        """대분류 여부 확인 (parent가 없으면 대분류)"""
        return self.parent is None

    @property
    def full_path(self):
        """전체 경로 반환 (대분류 > 소분류)"""
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class IngredientMaster(models.Model):
    """
    식재료 마스터 데이터
    
    서비스에서 제공하는 표준 식재료 목록
    사용자가 식재료를 등록할 때 이 목록에서 선택
    
    Fields:
        ingredient_id: 식재료 고유 ID (PK)
        category: 소속 카테고리
        name_ko: 한글 식재료명 (예: 토마토, 양파)
        aliases: 별칭/번역 JSON (예: ["tomato", "토메이토"])
        icon_url: 프론트엔드 표시용 아이콘 URL
    """
    # Primary Key
    ingredient_id = models.BigAutoField(
        primary_key=True,
        verbose_name='식재료 ID'
    )
    
    # 카테고리와의 관계
    # PROTECT: 식재료가 존재하는 카테고리는 삭제 불가
    category = models.ForeignKey(
        IngredientCategory,
        on_delete=models.PROTECT,
        related_name='ingredients',  # 카테고리.ingredients.all()로 식재료 목록 조회
        db_column='category_id',
        verbose_name='카테고리'
    )
    
    # 한글 식재료명
    # db_index=True: 검색이 빈번하므로 인덱스 추가
    name_ko = models.CharField(
        max_length=50,
        verbose_name='한글명',
        db_index=True
    )
    
    # 여러 이름을 배열로 저장 (검색 시 활용)
    # 예: ["토마토", "tomato", "토메이토"]
    aliases = models.JSONField(
        null=True,
        blank=True,
        verbose_name='별칭/번역',
        help_text='["토마토", "tomato"] 형식'
    )
    
    # 프론트엔드에서 귀여운 아이콘 표시용
    icon_url = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='아이콘 URL'
    )
    
    # 등록 시점 자동 저장
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='등록일시'
    )

    class Meta:
        db_table = 'IngredientMaster'
        verbose_name = '식재료 마스터'
        verbose_name_plural = '식재료 마스터'
        indexes = [
            # 자주 사용되는 필드에 인덱스 추가
            models.Index(fields=['category'], name='idx_ingredient_category'),
            models.Index(fields=['name_ko'], name='idx_ingredient_name'),
        ]

    def __str__(self):
        """Admin에서 '토마토 (채소)' 형태로 표시"""
        return f"{self.name_ko} ({self.category.name})"

    def get_all_names(self):
        """
        모든 이름 반환 (한글명 + 별칭)
        
        검색 시 유용: 사용자가 "tomato" 또는 "토마토"로 검색해도 찾을 수 있음
        
        Returns:
            list: ['토마토', 'tomato', '토메이토']
        """
        names = [self.name_ko]
        if self.aliases:
            names.extend(self.aliases)
        return names

    @classmethod
    def find_by_name(cls, name):
        """
        이름으로 식재료 찾기 (한글명 또는 별칭)
        
        Spoonacular API 등 외부 데이터와 매칭할 때 사용
        
        Args:
            name (str): 검색할 이름 (한글 또는 영문)
        
        Returns:
            IngredientMaster or None: 찾은 식재료 또는 None
        
        Example:
            ingredient = IngredientMaster.find_by_name('tomato')
            # '토마토' IngredientMaster 객체 반환
        """
        name_lower = name.lower().strip()
        
        # 1. 한글명으로 검색 (대소문자 구분 없음)
        try:
            return cls.objects.get(name_ko__iexact=name)
        except cls.DoesNotExist:
            pass
        
        # 2. aliases에서 검색
        ingredients = cls.objects.all()
        for ingredient in ingredients:
            if ingredient.aliases:
                # 대소문자 구분 없이 비교
                aliases_lower = [alias.lower() for alias in ingredient.aliases]
                if name_lower in aliases_lower:
                    return ingredient
        
        return None

    @classmethod
    def create_ingredient_mapping_for_api(cls):
        """
        API 응답의 재료명을 IngredientMaster와 매칭하는 딕셔너리 생성
        
        Spoonacular API에서 레시피를 가져올 때 사용
        API의 재료명(영문)을 우리 DB의 IngredientMaster와 매칭
        
        Returns:
            dict: {api_ingredient_name: IngredientMaster 객체}
        
        Example:
            mapping = IngredientMaster.create_ingredient_mapping_for_api()
            tomato = mapping.get('tomato')  # 토마토 IngredientMaster 반환
        """
        mapping = {}
        
        for ingredient in cls.objects.all():
            # 한글명을 key로 매핑
            mapping[ingredient.name_ko.lower()] = ingredient
            
            # 별칭도 key로 매핑
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
    # CASCADE: 사용자 삭제 시 보유 식재료도 함께 삭제
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # User 모델 (커스텀 User 대응)
        on_delete=models.CASCADE,
        related_name='ingredients',  # user.ingredients.all()로 보유 식재료 조회
        db_column='user_id',
        verbose_name='사용자'
    )
    
    # 식재료 마스터와의 관계
    # PROTECT: 누군가 이 재료를 보유 중이면 마스터 데이터 삭제 불가
    ingredient = models.ForeignKey(
        IngredientMaster,
        on_delete=models.PROTECT,
        related_name='user_ingredients',  # 역참조용
        db_column='ingredient_id',
        verbose_name='식재료'
    )
    
    # 유통기한 (선택 사항)
    # 입력한 경우에만 추천 점수 계산에 가중치 부여
    expire_at = models.DateField(
        null=True,
        blank=True,
        verbose_name='유통기한',
        help_text='입력 안하면 가중치 제외'
    )
    
    # 사용 완료 여부 (소프트 삭제 대신 사용)
    is_consumed = models.BooleanField(
        default=False,
        verbose_name='사용 완료 여부'
    )
    
    # 추가 시점 자동 저장
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
            # 자주 조회되는 필드에 인덱스 추가
            models.Index(fields=['user'], name='idx_user_ingredient_user'),
            models.Index(fields=['ingredient'], name='idx_user_ingredient_ing'),
            models.Index(fields=['expire_at'], name='idx_user_ingredient_expire'),
            # 복합 인덱스: 사용자의 미소비 식재료 조회 시 성능 향상
            models.Index(
                fields=['user', 'is_consumed'],
                name='idx_user_ingredient_active'
            ),
        ]
        # 같은 사용자가 같은 재료를 여러 번 등록 가능
        # (유통기한이 다른 경우가 있을 수 있음)

    def __str__(self):
        """
        Admin에서 보기 좋게 표시
        예: "✓ 홍길동 - 토마토" (소비 완료)
            "○ 홍길동 - 양파" (미소비)
        """
        status = "✓" if self.is_consumed else "○"
        return f"{status} {self.user.nickname} - {self.ingredient.name_ko}"

    @property
    def is_expiring_soon(self):
        """
        유통기한 임박 여부 (3일 이내)
        
        UI에서 '유통기한 임박' 뱃지 표시 시 사용
        
        Returns:
            bool: 3일 이내면 True
        """
        if not self.expire_at:
            return False
        from datetime import date, timedelta
        return self.expire_at <= date.today() + timedelta(days=3)

    @property
    def is_expired(self):
        """
        유통기한 만료 여부
        
        Returns:
            bool: 유통기한이 지났으면 True
        """
        if not self.expire_at:
            return False
        from datetime import date
        return self.expire_at < date.today()

    @property
    def days_until_expiry(self):
        """
        유통기한까지 남은 일수
        
        Returns:
            int or None: 남은 일수 (유통기한 미입력 시 None)
        
        Example:
            오늘이 1월 27일이고 유통기한이 1월 30일이면 → 3
            유통기한이 1월 25일이면 → -2 (2일 지남)
        """
        if not self.expire_at:
            return None
        from datetime import date
        delta = self.expire_at - date.today()
        return delta.days

    def get_urgency_score(self):
        """
        유통기한 긴급도 점수 계산
        
        추천 점수 계산 시 사용
        
        Returns:
            int: 긴급도 점수 (20~100)
        
        점수 기준:
            - D-day 0~2일: 100점 (매우 긴급)
            - D-day 3~5일: 70점 (긴급)
            - D-day 6~10일: 40점 (주의)
            - D-day 11일 이상: 20점 (여유)
            - D-day 음수(지남): 20점
            - 미입력: 20점
        
        Note:
            유통기한 지남과 미입력 모두 20점으로 처리
            단, get_expiry_status()로 UI에서 구분 가능
        """
        days = self.days_until_expiry
        
        # 유통기한 미입력 - 기본 점수 20점
        if days is None:
            return 20
        
        # 유통기한 지남 (음수) - 기본 점수 20점
        if days < 0:
            return 20
        
        # 긴급도 점수 계산
        if days <= 2:
            return 100  # 매우 긴급
        elif days <= 5:
            return 70   # 긴급
        elif days <= 10:
            return 40   # 주의
        else:
            return 20   # 여유

    def get_expiry_status(self):
        """
        유통기한 상태 반환 (UI 표시용)
        
        프론트엔드에서 뱃지 색상/아이콘 결정 시 사용
        
        Returns:
            str: 상태 코드
                - 'expired': 유통기한 지남 (빨강)
                - 'urgent': 매우 긴급 D-2 이내 (주황)
                - 'warning': 긴급 D-5 이내 (노랑)
                - 'caution': 주의 D-10 이내 (연노랑)
                - 'ok': 여유 (초록)
                - 'unknown': 미입력 (회색)
        """
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

    def mark_as_consumed(self):
        """
        식재료 사용 처리
        
        요리 완료 후 해당 식재료를 소비 처리할 때 사용
        
        Example:
            ingredient = UserIngredient.objects.get(id=1)
            ingredient.mark_as_consumed()
            # is_consumed = True로 변경됨
        """
        self.is_consumed = True
        # update_fields: 특정 필드만 업데이트 (성능 향상)
        self.save(update_fields=['is_consumed', 'updated_at'])