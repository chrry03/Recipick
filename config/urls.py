from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.http import HttpResponse # [추가] 임시 응답용

# [추가] 아직 안 만든 페이지들에러 방지용 임시 함수
def temp_view(request):
    return HttpResponse("준비 중인 페이지입니다.")

schema_view = get_schema_view(
    openapi.Info(
        title="Recipick API",
        default_version='v1',
        description="레시픽(Recipick) API",
        contact=openapi.Contact(email="contact@recipick.com"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. 식재료 앱 (우리가 만든 fridge 페이지는 여기 안에 있음)
    path('ingredients/', include('ingredients.urls')),
    
    # ================= [중요] 에러 해결 파트 =================
    # base_with_navbar.html에 있는 이름들을 임시로 다 등록해줘야 함
    
    # 1) 홈 화면 (name='home')
    path('', temp_view, name='home'), 
    
    # 2) 일지 화면 (name='log_list') - 탭바에 있어서 에러 날 예정이라 미리 추가
    path('logs/', temp_view, name='log_list'),
    
    # 3) 레시피 화면 (name='recipe_list')
    path('recipes/', temp_view, name='recipe_list'),
    
    # 4) 마이페이지 (name='mypage')
    path('mypage/', temp_view, name='mypage'),
    
    # (참고: name='my_fridge'는 ingredients/urls.py에 이미 있어서 에러 안 남)
    # ========================================================

    # Swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    # Users App
    path('', include('users.urls')),
    
    # Logs App
    path('logs/', include('logs.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)