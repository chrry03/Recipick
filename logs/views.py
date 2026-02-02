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
            'image': '/static/images/ex/pasta.png',
            'difficulty_stars': '★★★☆☆',
            'satisfaction_stars': '★★★★★',
        },
        {
            'id': 2,
            'day': 21,
            'time': '17:31',
            'recipe_name': '새송이 덮밥',
            'image': '/static/images/ex/mushroom,.png',
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

def log_detail(request, log_id):
    """일지 상세 페이지 뷰"""
    # 테스트용 더미 데이터
    log_data = {
        'id': log_id,
        'date': '1월 11일',
        'time': '10:20',
        'recipe_name': '로제 파스타',
        'recipe_image': '/static/images/ex/pasta.png',
        'difficulty': '★★★☆☆',
        'satisfaction': '★★★★★',
        'ingredients': '파스타면, 베이컨, 양파, 마늘, 토마토소스, 생크림, 올리브유, 소금, 후추, 페페론치노',
        'recipe_steps': [
            '물에 소금 넉넉히 넣고 면 삶기(8분)',
            '팬에 올리브유 두르고 마늘, 양파, 베이컨 순으로 볶기',
            '토마토소스 넣고 2분 끓인 뒤 생크림 넣고 잘 섞기',
            '면 넣고 센 불에서 빠르게 섞어 소금·후추로 간 맞추기',
        ],
        'memo': '맛있었음.',
    }
    
    context = {
        'log': log_data,
    }
    return render(request, 'logs/log_detail.html', context)
