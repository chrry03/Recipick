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
    path('my-fridge/', views.my_fridge_view, name='my_fridge'),
    path('add/', views.add_ingredient_view, name='add_ingredient'),
    
    # API 라우터
    path('api/', include(router.urls)),

    # 아래 3가지는 users앱의 취향설정 페이지에서 사용하기 위해 추가함.
    # fixtures의 식재료,카테고리 json 파일 데이터를 불러오고,
    # 식재료를 검색하기 위함임.
    # 1. 카테고리 목록 조회 (/ingredients/categories/)
    path('categories/', views.category_list_view, name='category_list'),
    # 2. 식재료 목록 조회 (/ingredients/?category_id=1)
    path('', views.ingredient_list_view, name='ingredient_list'),
    # 3. 검색 (/ingredients/search/?keyword=양파)
    path('search/', views.search_ingredient_view, name='search_ingredient'),
    # [추가] 커스텀 식재료 생성 API
    path('api/custom/', views.create_custom_ingredient, name='create_custom_ingredient'),
]