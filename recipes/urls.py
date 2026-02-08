from django.urls import path
from . import views

app_name = 'recipes'

urlpatterns = [
    # 화면 페이지 (Template View)
    path('', views.recipe_list_view, name='list'),
    path('<int:recipe_id>/', views.recipe_detail_view, name='detail'),
    path('<int:recipe_id>/step/<int:step>/', views.cooking_mode_view, name='cooking_mode_step'),
    path('<int:recipe_id>/complete/', views.cooking_complete_view, name='cooking_complete'),
    
    # API 엔드포인트
    path('api/list/', views.recipe_list, name='api-list'),
    path('api/search/', views.search_recipes, name='api-search'),
    path('api/recommendations/', views.get_recipe_recommendations, name='api-recommendations'),
    path('api/<int:recipe_id>/', views.recipe_detail, name='api-detail'),
    path('api/<int:recipe_id>/favorite/', views.toggle_favorite, name='api-favorite'),
]
