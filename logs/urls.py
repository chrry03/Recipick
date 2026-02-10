from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'logs'

# =============================================================
# 1. API 라우터 설정 (데이터 통신용)
# =============================================================
# ViewSet을 사용하면 복잡한 URL들을(목록, 상세, 생성, 수정 등)
# 라우터가 알아서 한 방에 만들어줍니다.
router = DefaultRouter()

# 주소 규칙: /logs/api/ ...
# basename='log-api'는 나중에 reverse('logs:log-api-list') 처럼 쓸 때 필요합니다.
router.register(r'api', views.RecipeLogViewSet, basename='log-api')


# =============================================================
# 2. URL 패턴 정의
# =============================================================
urlpatterns = [
    # --- [A] 화면(HTML) 페이지 (프론트엔드 팀원이 만든 구조 유지) ---
    # 사용자가 브라우저로 접속하는 주소입니다.
    path('', views.log_list_view, name='list'),          # http://.../logs/
    path('create/', views.log_create_view, name='create'), # http://.../logs/create/
    path('<int:pk>/', views.log_detail_view, name='detail'), # http://.../logs/10/
    # (주의: views.py에서 함수 인자를 pk로 받았으므로 <int:pk>로 맞춰줍니다)

    # --- [B] 데이터(JSON) API (JS가 통신하는 주소) ---
    # 라우터가 만든 URL들을 여기에 포함시킵니다.
    path('', include(router.urls)), 
]