from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    1. 유저 (기본 정보)
    - password, last_login, date_joined는 AbstractUser 상속으로 자동 생성됨 (코드에 안 보여도 DB엔 생김!)
    - Django의 AbstractUser를 상속받아 비밀번호, 인증 관리 기능을 그대로 사용
    """
    user_id = models.BigAutoField(primary_key=True)

    @property
    def id(self):
        return self.user_id

    nickname = models.CharField(max_length=50, null=False)
    # email field is already in AbstractUser, but we can enforce it to be unique
    email = models.EmailField(unique=True, null=False)

    # 이메일을 아이디로 사용 (로그인 시 사용자설정 아이디가 아니라, "이메일"과 패스워드를 입력)
    USERNAME_FIELD = 'email'
    # 슈퍼유저 생성 시 추가로 입력받을 필드
    REQUIRED_FIELDS = ['username', 'nickname']
    
    # password, last_login, date_joined는 AbstractUser에 이미 포함되어 있음

    class Meta:
        db_table = 'User' # DB 테이블명 지정

    def __str__(self):
        return self.nickname # 객체를 보여줄때 객체 자신의 닉네임(문자열)으로 보여줌
    
    # [★ 핵심 기능 추가] 저장할 때 자동으로 username 채워주기(username이 비어있으면)
    def save(self, *args, **kwargs):
        # 만약 username이 비어있다면?
        if not self.username:
            # 이메일을 username에 그대로 복사!
            self.username = self.email
        # 원래의 저장 기능 실행 (이거 안 쓰면 저장 안 됨)
        super().save(*args, **kwargs)
    # AbstractUser받아서 쓰면 무조건 생기는 필드인데 비어있으면 에러날수 있음. 근데 우리는 안받기 때문에 채워줘야함.
    # email값으로 채움. DB 저장 시: user.username = user.email (이렇게 똑같이 넣어버리기)
    # 이유: username 필드는 unique=True라서 비워두면 안 되기 때문.

class UserProfile(models.Model):
    """
    2. 유저 프로필 (추가 정보 - 1:1 관계)
    """
    class CookingLevel(models.TextChoices):
        BEGINNER = 'BEGINNER', '초보'           # DB저장값, 화면표시값
        INTERMEDIATE = 'INTERMEDIATE', '중급'
        EXPERT = 'EXPERT', '숙련'

    # 1:1 관계 설정: User가 삭제되면 프로필도 같이 삭제 (CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='profile')
    # User 테이블의 ID를 내 ID처럼 씀(예: 유저 5번의 프로필 ID도 5번)
    # related_name: 나중에 코드 짤 때 user.profile이라고만 치면 바로 이 프로필 정보를 가져올 수 있게 해주는 '별명'
    # 부모의 PK랑 연결하는 부분은 컬럼명을 "필드명+_id"로 하므로 결론적으로 user_id가 됨

    cooking_level = models.CharField(
        max_length=20,
        choices=CookingLevel.choices,
        default=CookingLevel.BEGINNER
    )
    # JSONField는 리스트나 딕셔너리를 그대로 저장 가능
    # [수정] null=True 제거, default=list 추가 -> 개발 편의성 향상
    allergies = models.JSONField(default=list, blank=True, verbose_name='알러지 목록')
    banned_ingredients = models.JSONField(default=list, blank=True, verbose_name='기피 재료 목록')
    # verbose_name은 관리자페이지에서 영어 막 banned_ingredients이렇게 말고 저렇게 보이도록 함.
    updated_at = models.DateTimeField(auto_now=True) # 수정될 때마다 자동 갱신

    class Meta:
        db_table = 'UserProfile' # DB 테이블명 지정

class SocialAccount(models.Model):
    """
    3. 소셜 계정 정보
    """
    class Provider(models.TextChoices):
        GOOGLE = 'GOOGLE', 'Google'
        KAKAO = 'KAKAO', 'Kakao'
        NAVER = 'NAVER', 'Naver'

    social_id = models.BigAutoField(primary_key=True)
    # 1:N 관계 설정: User가 삭제되면 프로필도 같이 삭제 (CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    # User 테이블의 ID를 내 ID처럼 씀(예: 유저 5번의 프로필 ID도 5번)
    # related_name: 나중에 코드 짤 때 user.social_accounts.all() 이라고 치면, 이 유저가 연동한 모든 소셜 계정 목록이 나옴
    # 부모의 PK랑 연결하는 부분은 컬럼명을 "필드명+_id"로 하므로 결론적으로 user_id가 됨


    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_uid = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True) # 생성 시 1회 자동 저장

    class Meta:
        db_table = 'SocialAccount'
        # 한 유저가 같은 소셜로 중복 가입 방지 (Unique Constraint)
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'provider_uid'], #"제공자(구글)"와 "UID(12345)"의 조합은 유일해야 한다는 뜻
                name='unique_social_account'
            )
        ]

#요약: 개발할 때 이렇게 씁니다
#내 요리 실력 확인: user.profile.cooking_level
#내 알러지 목록: user.profile.allergies (리스트로 바로 나옴)
#내가 연동한 소셜 계정들: user.social_accounts.all()