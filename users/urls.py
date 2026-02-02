from django.urls import path
from . import views

app_name='users'

urlpatterns = [
    path('', views.login_view, name='login'),          # 로그인 화면
    path('login/', views.login_view, name='login'),          # 로그인 화면
    path('signup/', views.signup_view, name='signup'),       # 회원가입
    path('nickname/', views.nickname_view, name='nickname'), # 닉네임 설정
    path('mypage/', views.mypage_view, name='mypage'),       # 마이 페이지
    path('main/', views.main_view, name='main'),             # 메인 페이지
    path('check-nickname/', views.check_nickname_view, name='check_nickname'), # 닉네임 중복 확인
    path('me/', views.me_view, name='me'),                   # 닉네임 변경 (내 정보 수정)
]