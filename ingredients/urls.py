from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IngredientViewSet, IngredientCategoryViewSet, UserIngredientViewSet

router = DefaultRouter()
router.register('ingredients', IngredientViewSet, basename='ingredient')
router.register('ingredients/categories', IngredientCategoryViewSet, basename='ingredient-category')
router.register('user-ingredients', UserIngredientViewSet, basename='user-ingredient')

urlpatterns = router.urls