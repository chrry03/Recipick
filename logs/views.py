from django.shortcuts import render
from django.utils import timezone
import json

# Create your views here.

def log_create(request):
    """일지 작성 페이지 뷰"""
    return render(request, 'logs/log_create.html')

def log_list(request):
    """일지 목록 페이지 뷰"""
    # 현재 월 가져오기
    current_month = timezone.now().month
    
    # 테스트용 더미 데이터
    logs = [
        {
            'id': 1,
            'day': 11,
            'time': '10:20',
            'recipe_name': '로제 파스타',
            'image': 'https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=120&h=120&fit=crop',
            'difficulty_stars': '★★★☆☆',
            'satisfaction_stars': '★★★★★',
        },
        {
            'id': 2,
            'day': 21,
            'time': '17:31',
            'recipe_name': '새송이 덮밥',
            'image': 'https://images.unsplash.com/photo-1512058564366-18510be2db19?w=120&h=120&fit=crop',
            'difficulty_stars': '★★☆☆☆',
            'satisfaction_stars': '★★★★☆',
        },
        {
            'id': 3,
            'day': 22,
            'time': '15:18',
            'recipe_name': '김치 볶음밥',
            'image': None,
            'difficulty_stars': '★☆☆☆☆',
            'satisfaction_stars': '★★☆☆☆',
        },
    ]
    
    # 빈 상태 테스트를 원하면 아래 주석을 해제하세요
    # logs = []
    
    context = {
        'current_month': current_month,
        'logs': logs,
    }
    return render(request, 'logs/log_list.html', context)
