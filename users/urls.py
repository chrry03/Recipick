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
    path('logout/', views.logout_view, name='logout'),                         # 로그아웃 (★추가됨)
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # 토큰 재발급 (★추가됨)

    # [참고] 'me/' 경로는 'mypage/'와 기능이 같으므로(mypage_view가 다 처리함) 굳이 따로 안 만들어도 됩니다!
]