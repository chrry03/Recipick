from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# DRF Router 설정
router = DefaultRouter()
router.register('recipes', views.RecipeViewSet, basename='recipe')
router.register('favorites', views.FavoriteRecipeViewSet, basename='favorite')

app_name = 'recipes'

urlpatterns = [
    # ==================== 화면 페이지 (Template View) ==================== #
    path('', views.recipe_list_view, name='list'),
    path('<int:recipe_id>/', views.recipe_detail_view, name='detail'),
    path('<int:recipe_id>/cooking/', views.cooking_mode_view, name='cooking_mode'),
    path('<int:recipe_id>/complete/', views.cooking_complete_view, name='cooking_complete'),
    
    # ==================== API 엔드포인트 ==================== #
    # DRF Router URLs
    path('api/', include(router.urls)),
    
    # 추가 API 엔드포인트
    path('api/recommendations/', views.get_recipe_recommendations, name='api-recommendations'),
    path('api/<int:recipe_id>/detail/', views.get_recipe_detail, name='api-detail'),
]