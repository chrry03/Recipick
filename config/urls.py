from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from users.views import main_view # 메인 뷰만 여기서 직접 임포트

# Swagger 설정
schema_view = get_schema_view(
    openapi.Info(
        title="레시픽 API",
        default_version='v1',
        description="레시픽 레시피 추천 시스템 API 문서",
        contact=openapi.Contact(email="contact@recipick.com"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls), # 어드민 페이지
    
    # 1. 사이트 대문 (http://127.0.0.1:8000/)
    path('', main_view, name='root'),

    # 2. 각 앱별 URL (규칙 통일)
    path('users/', include('users.urls')),              # users 앱
    path('ingredients/', include('ingredients.urls')),  # ingredients 앱
    path('recipes/', include('recipes.urls')),          # recipes 앱
    path('logs/', include('logs.urls')),                # logs 앱
    
    # Swagger URLs
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# 미디어 파일 서빙 (개발 환경)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)