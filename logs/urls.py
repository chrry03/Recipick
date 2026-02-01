# 각 앱의 urls.py: 런서버 하기 위한 urls.py 틀 작성!!!
from django.urls import path
from . import views

app_name = 'logs'

urlpatterns = [
    path('', views.log_list, name='list'),
    path('create/', views.log_create, name='create'),
    path('<int:log_id>/', views.log_detail, name='detail'),
]