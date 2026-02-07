from datetime import date
from django.shortcuts import render
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db.models import F

# DRF 관련 임포트
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

# ★ 다른 앱의 모델들 가져오기 (Real Data 사용)
from .models import User, SocialAccount
from .serializers import UserSerializer
# (주의: 아래 앱들의 models.py가 작성되어 있어야 에러가 안 납니다)
from recipes.models import Recipe, FavoriteRecipe
from ingredients.models import UserIngredient
from logs.models import RecipeLog

from itertools import chain

User = get_user_model()

# =============================================================
# 1. 회원가입 (화면 + 기능)
# =============================================================
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def signup_view(request):
    if request.method == 'GET':
        return render(request, 'users/signup.html')
    
    if request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = User.objects.create_user(
                    username=request.data['email'], #username을 email과 똑같이 설정해주는 코드 추가
                    email=request.data['email'],
                    password=request.data['password'],
                    nickname=request.data['nickname']
                )
                login(request, user) # 세션 로그인
                token = RefreshToken.for_user(user) # 토큰 발급
                return Response({
                    "message": "회원가입이 완료되었습니다.",
                    "user": UserSerializer(user).data,
                    "token": {
                        "access": str(token.access_token),
                        "refresh": str(token),
                    }
                }, status=201)
            except Exception as e:
                # 에러 확인을 위해 콘솔에 원인을 출력해두면 좋습니다.
                print(f"회원가입 에러: {e}")
                return Response({"message": "회원가입 중 오류가 발생했습니다."}, status=400)
            
        # 유효성 검사 실패 시 (이미 있는 이메일 등)
        return Response(serializer.errors, status=400)

# =============================================================
# 2. 로그인 (화면 + 기능)
# =============================================================
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def login_view(request):
    if request.method == 'GET':
        return render(request, 'users/login.html')

    if request.method == 'POST':
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(email=email, password=password)

        if user is not None:
            login(request, user)
            token = RefreshToken.for_user(user)
            return Response({
                "message": "로그인 성공",
                "user": UserSerializer(user).data,
                "token": {
                    "access": str(token.access_token),
                    "refresh": str(token),
                }
            }, status=200)
        else:
            return Response({"message": "이메일 또는 비밀번호가 틀렸습니다."}, status=401)

# =============================================================
# 3. 소셜 로그인 (기능)
# =============================================================
@api_view(['POST'])
@permission_classes([AllowAny])
def social_login_view(request, provider):
    # [To Do] 소셜 로그인 구현 시 로직 추가
    return Response({"message": "소셜 로그인 기능 준비 중입니다."}, status=200)

# =============================================================
# 4. 메인 화면 (★ Real DB 연동 완료)
# =============================================================
def main_view(request):
    user = request.user
    
    # 1. 오늘의 추천 메뉴 (일단 랜덤 or 최신순 6개)
    # [Logic] 추천 알고리즘이 적용된다면 여기에 로직 추가
    recommended_qs = Recipe.objects.filter(is_active=True).order_by('?')[:6]
    recommended_recipes = []
    for r in recommended_qs:
        recommended_recipes.append({
            'id': r.recipe_id,
            'name': r.title,
            'difficulty': r.difficulty, # EASY, NORMAL, DIFFICULT
            'cookingTime': f"{r.ready_minutes}분" if r.ready_minutes else "??분",
            'image': r.image_url
        })

    # 2. 찜한 레시피 (최신순 3개)
    favorite_recipes = []
    if user.is_authenticated:
        fav_qs = FavoriteRecipe.objects.filter(user=user).select_related('recipe').order_by('-created_at')[:3]
        for f in fav_qs:
            favorite_recipes.append({
                'id': f.recipe.recipe_id,
                'name': f.recipe.title,
                'image': f.recipe.image_url,
                'isFavorite': True
            })

    # 3. 내 식재료 (소비기한 임박한 순서 8개)
    ingredients = []
    if user.is_authenticated:
        # [Logic] is_consumed=False인 것만, expire_at 오름차순(급한거 먼저)
        ing_qs = UserIngredient.objects.filter(user=user, is_consumed=False).select_related('ingredient').order_by('expire_at')[:8]
        today = date.today()
        
        for item in ing_qs:
            # D-Day 계산
            d_day = None
            if item.expire_at:
                delta = (item.expire_at - today).days
                if delta < 0: d_day = f"D+{abs(delta)}" # 지남
                elif delta == 0: d_day = "D-Day"
                else: d_day = f"D-{delta}"
            
            # 이미지: IngredientCategory에 아이콘이 있다고 가정 (없으면 기본값)
            # models.py 구조상 ingredient -> category -> icon_url 접근 필요
            icon_url = '/static/images/default_ing.png'
            if item.ingredient.category and item.ingredient.category.icon_url:
                icon_url = item.ingredient.category.icon_url
                
            ingredients.append({
                'id': item.user_ingredient_id,
                'name': item.ingredient.name_ko,
                'daysLeft': d_day,
                'image': icon_url
            })

    # 4. 내 일지 (최신순 5개)
    diary_entries = []
    if user.is_authenticated:
        log_qs = RecipeLog.objects.filter(user=user).select_related('recipe').order_by('-cooked_at')[:5]
        for log in log_qs:
            # 일지 이미지가 있으면 쓰고, 없으면 레시피 썸네일 사용
            display_image = log.image.url if log.image else log.recipe.image_url
            
            diary_entries.append({
                'id': log.recipe_log_id,
                'title': log.recipe.title,
                'date': log.cooked_at.strftime('%y.%m.%d'), # 26.01.11 형식
                'image': display_image
            })

    # Context에 담기
    context = {
        'recommended_recipes': recommended_recipes,
        'favorite_recipes': favorite_recipes,
        'ingredients': ingredients,
        'diary_entries': diary_entries,
    }
    return render(request, 'main.html', context)

# =============================================================
# 5. 마이페이지 (화면 + 기능)
# =============================================================
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([AllowAny]) # 누구나 접근 가능
def mypage_view(request):
    # [GET] 화면 보여주기
    if request.method == 'GET':
        context = {}

        # ★ [수정] 튕겨내는 코드(redirect) 삭제!
        # 대신, 로그인한 경우에만 데이터를 챙겨줍니다.
        if request.user.is_authenticated:
            serializer = UserSerializer(request.user)
            context['user_data'] = serializer.data
        
        # 비로그인 상태면 context가 비어있는 채로 렌더링 됩니다.
        # (HTML 템플릿에서 {% if user.is_authenticated %} 로 화면을 다르게 그리면 됨)
        return render(request, 'users/mypage.html', context)
    
    # ---------------------------------------------------------
    # [PATCH] & [DELETE] 기능은 여전히 로그인이 필수입니다.
    # (로그인 안 한 사람은 어차피 '수정/탈퇴' 버튼이 안 보일 테니까요)
    # ---------------------------------------------------------
    
    # [PATCH] 내 정보 수정
    if request.method == 'PATCH':
        if not request.user.is_authenticated:
            return Response({"message": "로그인이 필요합니다."}, status=401)

        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    # [DELETE] 회원 탈퇴
    if request.method == 'DELETE':
        if not request.user.is_authenticated:
            return Response({"message": "로그인이 필요합니다."}, status=401)

        user = request.user
        password = request.data.get('password')
        is_social = user.social_accounts.exists()
        
        if not is_social:
            if not password:
                return Response({"message": "비밀번호를 입력해주세요."}, status=400)
            if not user.check_password(password):
                return Response({"message": "비밀번호가 일치하지 않습니다."}, status=403)
        
        user.delete()
        return Response({"message": "탈퇴 완료"}, status=204)

# =============================================================
# 6. 기타 화면들
# =============================================================
def nickname_view(request):
    return render(request, 'users/nickname.html')

def preference_view(request):
    return render(request, 'users/preference_steps.html')

def notification_view(request):
    user = request.user
    notifications = []
    
    if user.is_authenticated:
        # 1. [Model 활용] 곧 상하는 재료 가져오기 (ingredients/views.py 코드)
        upcoming_qs = UserIngredient.get_expiring_soon_ingredients(user, days_threshold=3)
        
        # 2. [Model 활용] 이미 상한 재료 가져오기 (ingredients/views.py 코드)
        # (유통기한 지난 것도 보여주려면 이것도 필요. ingredients/views.py에는 지난거는 없기 때문.)
        expired_qs = UserIngredient.get_expired_ingredients(user)
        
        # 3. 두 리스트 합치기 (상한 거 + 곧 상할 거)
        all_targets = list(chain(expired_qs, upcoming_qs))
        
        for item in all_targets:
            # 4. [Model 활용] 멘트 생성도 모델에게 맡긴다!
            msg = item.get_notification_message()
            
            # 아이콘 처리 (기존 로직 유지)
            icon_url = '/static/images/default_ing.png' # 기본값
            if item.ingredient.category and item.ingredient.category.icon_url:
                 icon_url = item.ingredient.category.icon_url

            notifications.append({
                'id': item.user_ingredient_id,
                'message': msg,          # 모델이 만들어준 문장 그대로 사용
                'ingredient_name': item.ingredient.name_ko,
                'icon_url': icon_url 
            })

    context = {
        'notifications': notifications,
    }
    return render(request, 'users/notification.html', context)

# =============================================================
# 7. 기능 전용 API
# =============================================================
@api_view(['GET'])
@permission_classes([AllowAny])
def check_nickname_view(request):
    nickname = request.query_params.get('nickname')
    if not nickname:
        return Response({"message": "닉네임을 입력해주세요."}, status=400)
    
    is_exist = User.objects.filter(nickname=nickname).exists()
    return Response({'is_available': not is_exist}, status=200)

@api_view(['POST']) # 이메일은 body에 담아 보내므로 POST 권장
@permission_classes([AllowAny])
def check_email_view(request):
    """
    이메일 중복 확인 API
    """
    email = request.data.get('email')
    
    # 이메일 값이 안 넘어왔을 때
    if not email:
        return Response({"message": "이메일을 입력해주세요.", "is_available": False}, status=400)
    
    # DB에 이미 있는지 확인
    is_exist = User.objects.filter(email=email).exists()
    
    if is_exist:
        return Response({
            "message": "이미 가입된 이메일입니다.",
            "is_available": False
        }, status=200)
    else:
        return Response({
            "message": "사용 가능한 이메일입니다.",
            "is_available": True
        }, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        # 1. JWT 토큰 블랙리스트 처리 (API용 로그아웃)
        refresh_token = request.data.get("refresh")
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()

        # 2. [★ 핵심 추가] 브라우저 세션 삭제 (화면용 로그아웃)
        logout(request)

        return Response({"message": "로그아웃 성공"}, status=205)
    except Exception as e:
        # 토큰이 없거나 만료되어도 세션 로그아웃은 시켜주는 게 안전합니다.
        logout(request) 
        return Response({"message": "잘못된 토큰이지만 로그아웃 처리되었습니다."}, status=200)