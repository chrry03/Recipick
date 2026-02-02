# ingredients/urls.py

from django.urls import path, include
# from rest_framework.routers import DefaultRouter  <-- 주석 처리 (#)
# from .views import IngredientViewSet, IngredientCategoryViewSet, UserIngredientViewSet <-- 주석 처리 (#)
from . import views

# router = DefaultRouter() <-- 주석 처리 (#)
# router.register('ingredients', IngredientViewSet, basename='ingredient') <-- 주석 처리 (#)
# router.register('ingredients/categories', IngredientCategoryViewSet, basename='ingredient-category') <-- 주석 처리 (#)
# router.register('user-ingredients', UserIngredientViewSet, basename='user-ingredient') <-- 주석 처리 (#)

app_name = 'ingredients'

urlpatterns = [
    # 1. 화면 페이지 (Template View)
    path('fridge/', views.my_fridge_view, name='my_fridge'),
    path('add/', views.add_ingredient_view, name='add_ingredient'),
    
    # 2. API 라우터 (API View)
    # path('', include(router.urls)), <-- 주석 처리 (#)
]