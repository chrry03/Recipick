from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView # ★ 토큰 재발급용 임포트 추가
from . import views

app_name = 'users'

urlpatterns = [
    # 1. 화면 + 기능 (Hybrid)
    path('', views.login_view, name='login_root'),           # 기본 경로 -> 로그인
    path('login/', views.login_view, name='login'),          # 로그인 화면
    path('signup/', views.signup_view, name='signup'),       # 회원가입 화면
    #path('main/', views.main_view, name='main'),             # 메인 페이지 (html에서 root로 로드하도록 바꿈)
    path('mypage/', views.mypage_view, name='mypage'),       # 마이 페이지 (내 정보 조회/수정/탈퇴 통합)
    path('notification/', views.notification_view, name='notification'), # 알림 (★수정: notification -> notification_view)
    
    # 2. 단순 화면 렌더링
    path('nickname/', views.nickname_view, name='nickname'),       # 닉네임 설정 화면
    path('preference/', views.preference_view, name='preference'), # 취향 설정 화면

    # 3. 기능 전용 API
    path('check-nickname/', views.check_nickname_view, name='check_nickname'), # 닉네임 중복 확인
    path('check-email/', views.check_email_view, name='check_email'),          # [★ 추가] 이메일 중복 확인 API
    path('logout/', views.logout_view, name='logout'),                         # 로그아웃 (★추가됨)
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # 토큰 재발급 (★추가됨)

    # [참고] 'me/' 경로는 'mypage/'와 기능이 같으므로(mypage_view가 다 처리함) 굳이 따로 안 만들어도 됩니다!

    # 4. 소셜 로그인 (구글)
    path('google/login/', views.google_login_view, name='google_login'),           # 구글 로그인 페이지로 보내는 URL
    path('google/callback/', views.google_callback_view, name='google_callback'),  # 구글 인증 후 돌아오는 URL (Callback)

    path('naver/login/', views.naver_login_view, name='naver_login'),           # 네이버 로그인 페이지로 보내는 URL
    path('naver/callback/', views.naver_callback_view, name='naver_callback'),  # 네이버 인증 후 돌아오는 URL (Callback)
]