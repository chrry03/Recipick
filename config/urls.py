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

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/users/', include('users.urls')),
    path('api/ingredients/', include('ingredients.urls')),
    path('api/recipes/', include('recipes.urls')),
    path('api/logs/', include('logs.urls')),
]

# 미디어 파일 서빙 설정 (개발 모드용): 개발 모드일 때만 미디어 파일 서빙 가능하도록 설정
# settings.py의 DEBUG=TRUE일때(개발중일때)만 내 컴퓨터의 media폴더의 이미지를 띄울 수 있게 함
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)