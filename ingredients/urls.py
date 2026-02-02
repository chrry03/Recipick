from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IngredientViewSet, IngredientCategoryViewSet, UserIngredientViewSet
from . import views


router = DefaultRouter()
router.register('ingredients', IngredientViewSet, basename='ingredient')
router.register('ingredients/categories', IngredientCategoryViewSet, basename='ingredient-category')
router.register('user-ingredients', UserIngredientViewSet, basename='user-ingredient')

urlpatterns = [
    # 1. 화면 페이지 (Template View)
    # 최종 URL: http://127.0.0.1:8000/ingredients/fridge/
    path('fridge/', views.my_fridge_view, name='my_fridge'),
    
    # 최종 URL: http://127.0.0.1:8000/ingredients/add/
    path('add/', views.add_ingredient_view, name='add_ingredient'),
    
    # 2. API 라우터 (API View)
    # 최종 URL: http://127.0.0.1:8000/ingredients/ingredients/ (REST API)
    path('', include(router.urls)), 
]