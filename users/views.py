# users/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import ensure_csrf_cookie
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

User = get_user_model()

def signup_view(request):
    """회원가입 처리 API 및 페이지 렌더링"""
    if request.method == 'GET':
        return render(request, 'users/signup.html')
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            nickname = data.get('nickname')

            if User.objects.filter(email=email).exists():
                return JsonResponse({'message': '이미 가입된 이메일입니다.'}, status=400)

            # [해결 1] UserManager 에러 해결: username 인자를 명시적으로 전달합니다.
            # [해결 2] models.py에 정의된 PK 이름인 user_id를 사용해야 합니다.
            user = User.objects.create_user(
                username=email, # REQUIRED_FIELDS 대응
                email=email, 
                password=password, 
                nickname=nickname
            )

            # 성공 응답 데이터 구성
            response_data = {
                'message': '회원가입이 완료되었습니다.',
                'user': {
                    'id': user.user_id, # .id 대신 .user_id 사용
                    'email': user.email,
                    'nickname': user.nickname
                }
            }

            # 토큰 발급 로직 (라이브러리 설치 시 작동)
            if RefreshToken:
                refresh = RefreshToken.for_user(user)
                response_data['token'] = {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }

            return JsonResponse(response_data, status=201)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=500)
        
@ensure_csrf_cookie
def login_view(request):
    if request.method == 'GET':
        return render(request, 'users/login.html')
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')

            user = authenticate(request, email=email, password=password)

            if user is not None:
                refresh = RefreshToken.for_user(user)
                return JsonResponse({
                    'message': '로그인 성공',
                    'user': {
                        'id': user.id,
                        'nickname': user.nickname
                    },
                    'token': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    }
                }, status=200)
            else:
                return JsonResponse({'message': '이메일 또는 비밀번호가 틀렸습니다.'}, status=401)
        except Exception as e:
            # 에러 발생 시 로그를 확인하기 위해 아래처럼 수정
            print(f"Login Error: {e}") 
            return JsonResponse({'message': '서버 내부 오류가 발생했습니다.'}, status=500)

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated]) # 로그인이 되어 있어야만 실행됨
def me_view(request):
    """내 정보 조회 및 수정 API"""
    user = request.user
    
    # 1. 내 정보 조회 (GET) - 나중에 필요할 때 사용
    if request.method == 'GET':
        return Response({
            'email': user.email,
            'nickname': user.nickname,
            'id': user.id
        })
    
    # 2. 내 정보 수정 (PATCH) - 닉네임 변경 시 사용
    if request.method == 'PATCH':
        # 닉네임 변경 요청이 들어오면
        if 'nickname' in request.data:
            new_nickname = request.data['nickname']
            
            # 중복 검사 (내 닉네임과 같으면 패스, 다른데 이미 있으면 에러)
            if user.nickname != new_nickname and User.objects.filter(nickname=new_nickname).exists():
                return Response({'message': '이미 사용 중인 닉네임입니다.'}, status=400)
                
            user.nickname = new_nickname
            user.save()
            
        return Response({'message': '정보가 수정되었습니다.'}, status=200)
    
def check_nickname_view(request):
    """닉네임 중복 확인 API"""
    nickname = request.GET.get('nickname')
    if not nickname:
        return JsonResponse({'message': '닉네임을 입력해주세요.'}, status=400)
    
    exists = User.objects.filter(nickname=nickname).exists()
    return JsonResponse({'is_available': not exists})

def nickname_view(request): return render(request, 'users/nickname.html')
def mypage_view(request): return render(request, 'users/mypage.html')

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
