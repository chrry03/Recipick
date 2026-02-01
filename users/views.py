from django.shortcuts import render
import json

# Create your views here.

def notification(request):
    """알림 페이지 뷰"""
    # 테스트용 알림 데이터
    notifications = [
        {
            'id': 1,
            'ingredient_name': '당근',
            'message': '당근 유통기한이 얼마 남지 않았습니다.',
            'icon_url': 'data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'29\' height=\'29\' viewBox=\'0 0 29 29\'%3E%3Ctext x=\'0\' y=\'24\' font-size=\'24\'%3E🥕%3C/text%3E%3C/svg%3E'
        },
    ]
    
    # 알림이 없는 경우 테스트하려면 아래 주석을 해제하세요
    # notifications = []
    
    context = {
        'notifications': notifications,
    }
    return render(request, 'users/notification.html', context)

def main(request):
    """메인 페이지 뷰"""
    # 테스트용 추천 레시피 데이터
    recommended_recipes = [
        {
            'id': 1,
            'name': '간장 계란 밥',
            'difficulty': 1,
            'cookingTime': '10분',
            'image': 'https://images.unsplash.com/photo-1590301157890-4810ed352733?w=400'
        },
        {
            'id': 2,
            'name': '김치볶음밥',
            'difficulty': 2,
            'cookingTime': '15분',
            'image': 'https://images.unsplash.com/photo-1744870132190-5c02d3f8d9f9?w=400'
        },
        {
            'id': 3,
            'name': '로제 파스타',
            'difficulty': 3,
            'cookingTime': '25분',
            'image': 'https://images.unsplash.com/photo-1676300184847-4ee4030409c0?w=400'
        },
    ]
    
    # 테스트용 찜한 레시피 데이터
    favorite_recipes = [
        {
            'id': 1,
            'name': '김치말이국수',
            'image': 'https://images.unsplash.com/photo-1626803774007-f92c2c32cbe7?w=400',
            'isFavorite': True
        },
        {
            'id': 2,
            'name': '로제 파스타',
            'image': 'https://images.unsplash.com/photo-1676300184847-4ee4030409c0?w=400',
            'isFavorite': True
        },
    ]
    
    # 테스트용 식재료 데이터
    ingredients = [
        {
            'id': 1,
            'name': '당근',
            'daysLeft': 1,
            'image': 'https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?w=200'
        },
        {
            'id': 2,
            'name': '돼지고기',
            'daysLeft': 10,
            'image': 'https://images.unsplash.com/photo-1602470520998-f4a52199a3d6?w=200'
        },
        {
            'id': 3,
            'name': '버섯',
            'daysLeft': 11,
            'image': 'https://images.unsplash.com/photo-1478145046317-39f10e56b5e9?w=200'
        },
    ]
    
    # 테스트용 일지 데이터
    diary_entries = [
        {
            'id': 1,
            'title': '로제 파스타',
            'date': '26.01.11',
            'image': 'https://images.unsplash.com/photo-1676300184847-4ee4030409c0?w=400'
        },
        {
            'id': 2,
            'title': '새송이 덮밥',
            'date': '26.01.11',
            'image': 'https://images.unsplash.com/photo-1512058564366-18510be2db19?w=400'
        },
        {
            'id': 3,
            'title': '김치 볶음밥',
            'date': '26.01.11',
            'image': 'https://images.unsplash.com/photo-1744870132190-5c02d3f8d9f9?w=400'
        },
    ]
    
    # 빈 상태 테스트를 원하면 아래 주석을 해제하세요
    # favorite_recipes = []
    # ingredients = []
    # diary_entries = []
    
    context = {
        'recommended_recipes': json.dumps(recommended_recipes, ensure_ascii=False),
        'favorite_recipes': json.dumps(favorite_recipes, ensure_ascii=False),
        'ingredients': json.dumps(ingredients, ensure_ascii=False),
        'diary_entries': json.dumps(diary_entries, ensure_ascii=False),
    }
    return render(request, 'main.html', context)
