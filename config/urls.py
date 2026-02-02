from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

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
    path('admin/', admin.site.urls),
    
    # Swagger URLs
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # 앱별 URL (각각 한 번씩만 include)
    path('', include('users.urls')),                    # users 앱
    path('ingredients/', include('ingredients.urls')),  # ingredients 앱
    path('recipes/', include('recipes.urls')),          # recipes 앱
    path('logs/', include('logs.urls')),                # logs 앱
]

# 미디어 파일 서빙 (개발 환경)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)