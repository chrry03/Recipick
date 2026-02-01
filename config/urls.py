"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings             # [추가] 설정 가져오기
from django.conf.urls.static import static   # [추가] 정적 파일 서빙 함수
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Recipick API",
        default_version='v1',
        description="레시픽(Recipick) - 식재료 기반 레시피 추천 서비스 API",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@recipick.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    
    # API Documentation (Swagger)
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    
    # API Endpoints
    path('api/', include('ingredients.urls')),
    path('api/', include('recipes.urls')),
<<<<<<< HEAD
    path('api/users/', include('users.urls')),
=======

    # Users App
    path('', include('users.urls')),
    
    # Logs App
    path('logs/', include('logs.urls')),
>>>>>>> b6536717c1069e5c01f2aba1d52b7dfb53660fdd
]



# 미디어 파일 서빙 설정 (개발 모드용): 개발 모드일 때만 미디어 파일 서빙 가능하도록 설정
# settings.py의 DEBUG=TRUE일때(개발중일때)만 내 컴퓨터의 media폴더의 이미지를 띄울 수 있게 함
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)