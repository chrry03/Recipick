from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'recipes'

# DRF Router (API용)
router = DefaultRouter()
router.register('recipes', views.RecipeViewSet, basename='recipe')
router.register('favorites', views.FavoriteRecipeViewSet, basename='favorite')

urlpatterns = [
    # ==================== 화면 페이지 (Template View) ==================== #
    path('', views.recipe_list_view, name='list'),
    path('<int:recipe_id>/', views.recipe_detail_view, name='detail'),
    
    # [수정] 요리 모드 URL (HTML에서 이 이름을 사용합니다)
    path('<int:recipe_id>/cooking/', views.cooking_mode_view, name='cooking_mode'),
    path('<int:recipe_id>/cooking/<int:step>/', views.cooking_mode_view, name='cooking_mode_step'),
    
    # 요리 완료 URL
    path('<int:recipe_id>/complete/', views.cooking_complete_view, name='cooking_complete'),
    
    # ==================== API 엔드포인트 ==================== #
    path('api/', include(router.urls)),
    
    # 추가 커스텀 API (JS에서 호출하는 주소)
    path('api/recommendations/', views.get_recipe_recommendations, name='api-recommendations'),
    path('api/<int:recipe_id>/detail/', views.get_recipe_detail, name='api-detail'),
]