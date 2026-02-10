from django.urls import path
from . import views

app_name = 'logs'

urlpatterns = [
    # 1. 목록 페이지 (http://127.0.0.1:8000/logs/)
    # name='list'로 설정했으므로 템플릿에서 {% url 'logs:list' %}로 부를 수 있음
    path('', views.log_list_view, name='list'),
    
    # 2. 작성 페이지 (http://127.0.0.1:8000/logs/create/)
    path('create/', views.log_create_view, name='create'),
    
    # 3. 상세 페이지 (http://127.0.0.1:8000/logs/10/)
    path('<int:pk>/', views.log_detail_view, name='detail'),
]