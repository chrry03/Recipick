from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API 라우터 설정
router = DefaultRouter()
router.register('ingredients', views.IngredientViewSet, basename='ingredient')
router.register('categories', views.IngredientCategoryViewSet, basename='category')
router.register('user-ingredients', views.UserIngredientViewSet, basename='user-ingredient')

app_name = 'ingredients'

urlpatterns = [
    # 화면 페이지 (Template View)
    path('fridge/', views.my_fridge_view, name='my_fridge'),
    path('add/', views.add_ingredient_view, name='add_ingredient'),
    
    # API 라우터
    path('api/', include(router.urls)),
]