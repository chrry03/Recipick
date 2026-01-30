from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserProfile, SocialAccount

# 1. 유저 프로필을 유저 페이지 안에 껴넣기 (Inline)
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False # 프로필만 따로 삭제 못하게 함
    verbose_name_plural = '프로필 정보 (요리실력/알러지)'
    fk_name = 'user'

# 2. 소셜 계정 정보도 유저 페이지 안에 껴넣기 (Inline)
class SocialAccountInline(admin.TabularInline):
    model = SocialAccount
    extra = 0
    readonly_fields = ('provider', 'provider_uid', 'created_at')
    verbose_name_plural = '연동된 소셜 계정'

# 3. 커스텀 유저 Admin 정의
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    기존 Django UserAdmin 기능을 상속받아 비밀번호 관리 등은 유지하고
    프로필/소셜 정보를 추가로 보여줌
    """
    inlines = (UserProfileInline, SocialAccountInline)
    
    # 목록에서 보여줄 컬럼 (이메일이 아이디니까 앞에 배치)
    list_display = ('email', 'nickname', 'username', 'is_staff', 'date_joined')
    list_display_links = ('email', 'nickname') # 클릭하면 상세페이지로 이동
    
    # 상세 페이지 필드 설정 (nickname 추가)
    fieldsets = UserAdmin.fieldsets + (
        ('추가 정보', {'fields': ('nickname',)}),
    )
    
    # 검색 기능 (이메일, 닉네임으로 검색)
    search_fields = ('email', 'nickname', 'username')
    ordering = ('-date_joined',) # 최신 가입순 정렬

# (선택) 소셜 계정만 따로 리스트로 보고 싶을 때를 위해 등록
@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'created_at')
    list_filter = ('provider',)
    search_fields = ('user__email', 'user__nickname')