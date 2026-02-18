import json
import requests
from django.conf import settings

from datetime import date
from django.shortcuts import render, redirect
from django.templatetags.static import static
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
from urllib.parse import quote  # ★ [추가] 한글 닉네임 깨짐 방지용

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
                login(request, user, backend='django.contrib.auth.backends.ModelBackend') # 세션 로그인
                
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
            login(request, user, backend='django.contrib.auth.backends.ModelBackend') # 세션 로그인
            
            token = RefreshToken.for_user(user) # 토큰 발급
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
# 3. 소셜 로그인 (구글)
# =============================================================

# 3-1. 구글 로그인 페이지로 리다이렉트
@api_view(['GET'])
@permission_classes([AllowAny])
def google_login_view(request):
    # 구글에게 "이메일"과 "프로필" 정보를 달라고 요청하는 범위 설정
    scope = "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile"
    
    # settings.py (또는 .env)에서 설정한 키 값 가져오기
    client_id = settings.GOOGLE_CLIENT_ID
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    # 구글 인증 페이지 URL 생성
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope}"
    )
    
    # 사용자를 구글 로그인 페이지로 보냄
    return redirect(google_auth_url)


# 3-2. 구글에서 돌아왔을 때 처리 (Callback)
@api_view(['GET'])
@permission_classes([AllowAny])
def google_callback_view(request):
    # 1. 구글이 보내준 "인증 코드" 받기
    code = request.GET.get('code')
    
    if not code:
        return Response({"message": "구글 인증 코드가 없습니다."}, status=400)

    # 2. 인증 코드를 주고 "액세스 토큰" 받아오기
    token_req = requests.post(
        f"https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        }
    )
    token_req_json = token_req.json()
    error = token_req_json.get("error")
    if error is not None:
        return Response({"error": error}, status=400)
        
    access_token = token_req_json.get('access_token')

    # 3. 액세스 토큰으로 "유저 정보" 가져오기
    user_req = requests.get(
        f"https://www.googleapis.com/oauth2/v1/userinfo?access_token={access_token}"
    )
    user_req_json = user_req.json()
    email = user_req_json.get('email')
    social_id = str(user_req_json.get('id')) # 구글의 고유 사용자 ID

    # 4. 내 DB에서 회원가입 또는 로그인 처리
    try:
        # 4-1. 이메일로 기존 회원 찾기
        user = User.objects.get(email=email)
        
        # 소셜 계정 연결 여부 확인 (없으면 연결)
        SocialAccount.objects.get_or_create(
            user=user,
            provider='GOOGLE',
            defaults={'provider_uid': social_id}
        )
        
    except User.DoesNotExist:
        # 4-2. 회원이 아니면 신규 가입
        user = User.objects.create_user(
            username=email,  # ★ [추가] username을 email과 똑같이 설정해줍니다.
            email=email,
            password=None, # 소셜 유저는 비밀번호 없음
            # 닉네임은 임시로 설정 (예: user_12345)
            nickname=f"user_{social_id[:5]}"
        )
        # 소셜 계정 정보 저장
        SocialAccount.objects.create(
            user=user,
            provider='GOOGLE',
            provider_uid=social_id
        )

    # 5. ★ Django 세션 로그인 (핵심!)
    # backend를 명시해주는 것이 안전합니다.
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    # ★ [추가] JS를 안심시키기 위해 토큰을 만들어서 URL에 붙여줍니다.
    token = RefreshToken.for_user(user)
    access_token = str(token.access_token)
    refresh_token = str(token)

    # ★ [추가] 닉네임을 URL에 넣기 좋게 포장합니다 (한글 -> %ED%8... 변환)
    encoded_nickname = quote(user.nickname)
    
    # 6. 페이지 이동 로직 (URL 뒤에 토큰을 달고 갑니다! URL 뒤에 nickname도 추가!)
    # 신규 가입자(임시 닉네임)라면 -> 닉네임 설정 페이지로
    # 기존 회원라면 -> 메인 페이지로
    if user.nickname.startswith('user_'):
        # 'users:nickname'은 urls.py에서 설정한 닉네임 페이지의 name입니다.
        # ★ 신규 유저는 닉네임 설정 후 "취향 설정"으로 가도록 next 파라미터 추가!
        return redirect(f'/users/nickname/?access={access_token}&refresh={refresh_token}&next=preference&nickname={encoded_nickname}')
    else:
        return redirect(f'/?access={access_token}&refresh={refresh_token}&nickname={encoded_nickname}')
# =============================================================
# 3. 소셜 로그인 (네이버)
# =============================================================

# 3-1. 네이버 로그인 페이지로 리다이렉트
@api_view(['GET'])
@permission_classes([AllowAny])
def naver_login_view(request):
    client_id = settings.NAVER_CLIENT_ID
    redirect_uri = settings.NAVER_REDIRECT_URI
    state = "STATE_STRING"  # CSRF 방지용 랜덤 문자열 (간단히 고정값 사용)

    # 네이버 인증 페이지 URL 생성
    naver_auth_url = (
        f"https://nid.naver.com/oauth2.0/authorize?"
        f"response_type=code&"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"state={state}"
    )
    
    return redirect(naver_auth_url)


# 3-2. 네이버에서 돌아왔을 때 처리 (Callback)
@api_view(['GET'])
@permission_classes([AllowAny])
def naver_callback_view(request):
    # 1. 네이버가 보내준 "인증 코드" 받기
    code = request.GET.get('code')
    state = request.GET.get('state')

    if not code:
        return Response({"message": "네이버 인증 코드가 없습니다."}, status=400)

    # 2. 인증 코드를 주고 "액세스 토큰" 받아오기
    token_url = "https://nid.naver.com/oauth2.0/token"
    token_params = {
        "grant_type": "authorization_code",
        "client_id": settings.NAVER_CLIENT_ID,
        "client_secret": settings.NAVER_CLIENT_SECRET,
        "code": code,
        "state": state,
    }
    
    token_res = requests.get(token_url, params=token_params)
    token_json = token_res.json()

    if "error" in token_json:
        return Response({"error": token_json.get("error_description")}, status=400)

    naver_access_token = token_json.get("access_token")

    # 3. 액세스 토큰으로 "유저 정보" 가져오기
    profile_url = "https://openapi.naver.com/v1/nid/me"
    headers = {"Authorization": f"Bearer {naver_access_token}"}
    
    profile_res = requests.get(profile_url, headers=headers)
    profile_json = profile_res.json()
    
    # 네이버는 response 키 안에 실질적인 유저 정보가 들어있음
    naver_account = profile_json.get("response")
    
    if not naver_account:
        return Response({"error": "네이버 유저 정보를 가져오지 못했습니다."}, status=400)

    email = naver_account.get("email")
    social_id = naver_account.get("id")  # 네이버의 고유 사용자 ID
    # 네이버는 닉네임, 프로필 사진 등도 줌 (필요하면 사용)
    # nickname = naver_account.get("nickname") 

    if not email:
        return Response({"error": "이메일 동의가 필요합니다."}, status=400)

    # 4. 내 DB에서 회원가입 또는 로그인 처리
    try:
        # 4-1. 이메일로 기존 회원 찾기
        user = User.objects.get(email=email)
        
        # 소셜 계정 연결 여부 확인 (없으면 연결)
        # 이미 구글로 가입했어도 이메일이 같으면 통합됨
        SocialAccount.objects.get_or_create(
            user=user,
            provider='NAVER',
            defaults={'provider_uid': social_id}
        )

    except User.DoesNotExist:
        # 4-2. 회원이 아니면 신규 가입
        # 닉네임 임시 생성 (예: user_abcdef12)
        # social_id가 길어서 앞부분만 따옴
        temp_nickname = f"user_{social_id[:8]}"
        
        user = User.objects.create_user(
            username=email,  # 구글과 동일하게 username=email
            email=email,
            password=None,   # 소셜 유저는 비밀번호 없음
            nickname=temp_nickname
        )
        
        # 소셜 계정 정보 저장
        SocialAccount.objects.create(
            user=user,
            provider='NAVER',
            provider_uid=social_id
        )

    # 5. ★ Django 세션 로그인 (하이브리드 핵심 1)
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    # 6. ★ JWT 토큰 생성 (하이브리드 핵심 2)
    token = RefreshToken.for_user(user)
    access_token = str(token.access_token)
    refresh_token = str(token)

    # ★ 닉네임 인코딩 (한글 깨짐 방지)
    encoded_nickname = quote(user.nickname)

    # 7. 페이지 이동 로직 (구글 코드와 동일하게 처리)
    # 신규 가입자(임시 닉네임)라면 -> 닉네임 설정 페이지로
    if user.nickname.startswith('user_'):
        return redirect(f'/users/nickname/?access={access_token}&refresh={refresh_token}&next=preference&nickname={encoded_nickname}')
    else:
        # 기존 회원 -> 메인 페이지로
        return redirect(f'/?access={access_token}&refresh={refresh_token}&nickname={encoded_nickname}')

# =============================================================
# s. 소셜 로그인 (카카오)
# =============================================================

# s-1. 카카오 로그인 페이지로 리다이렉트
@api_view(['GET'])
@permission_classes([AllowAny])
def kakao_login_view(request):
    client_id = settings.KAKAO_CLIENT_ID
    redirect_uri = settings.KAKAO_REDIRECT_URI
    
    # 카카오 인증 페이지 URL 생성
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code"
    )
    return redirect(kakao_auth_url)

# 3-2. 카카오에서 돌아왔을 때 처리 (Callback)
@api_view(['GET'])
@permission_classes([AllowAny])
def kakao_callback_view(request):
    # 1. 카카오가 보내준 "인증 코드" 받기
    code = request.GET.get('code')
    if not code:
        return Response({"message": "카카오 인증 코드가 없습니다."}, status=400)

    # 2. 인증 코드로 "액세스 토큰" 요청 (POST 방식)
    token_url = "https://kauth.kakao.com/oauth/token"
    token_data = {
        "grant_type": "authorization_code",
        "client_id": settings.KAKAO_CLIENT_ID,
        "client_secret": settings.KAKAO_CLIENT_SECRET,
        "redirect_uri": settings.KAKAO_REDIRECT_URI,
        "code": code,
    }
    
    token_res = requests.post(token_url, data=token_data)
    token_json = token_res.json()

    # 에러 확인을 위해 로그 출력 (디버깅용)
    print("카카오 응답:", token_json)

    if "error" in token_json:
        return Response({
            "error": token_json.get("error"),
            "description": token_json.get("error_description")
        }, status=400)

    kakao_access_token = token_json.get("access_token")

    # 3. 액세스 토큰으로 "유저 정보" 가져오기
    profile_url = "https://kapi.kakao.com/v2/user/me"
    headers = {
        "Authorization": f"Bearer {kakao_access_token}",
        "Content-type": "application/x-www-form-urlencoded;charset=utf-8",
    }
    
    profile_res = requests.get(profile_url, headers=headers)
    profile_json = profile_res.json()
    
    # 유저 정보 추출
    kakao_account = profile_json.get("kakao_account")
    social_id = str(profile_json.get("id"))
    email = kakao_account.get("email") if kakao_account else None

    if not email:
        return Response({"error": "카카오 계정에 이메일 설정이 없거나 동의하지 않았습니다."}, status=400)

    # 4. 내 DB에서 회원가입 또는 로그인 처리
    try:
        user = User.objects.get(email=email)
        SocialAccount.objects.get_or_create(
            user=user,
            provider='KAKAO',
            defaults={'provider_uid': social_id}
        )
    except User.DoesNotExist:
        temp_nickname = f"user_{social_id[:8]}"
        user = User.objects.create_user(
            username=email,
            email=email,
            password=None,
            nickname=temp_nickname
        )
        SocialAccount.objects.create(
            user=user,
            provider='KAKAO',
            provider_uid=social_id
        )

    # 5. Django 세션 로그인 및 JWT 토큰 생성
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    # 6. ★ JWT 토큰 생성
    token = RefreshToken.for_user(user)
    access_token = str(token.access_token)
    refresh_token = str(token)
    encoded_nickname = quote(user.nickname)

    # 7. 리다이렉트 (기존 로직 유지)
    if user.nickname.startswith('user_'):
        return redirect(f'/users/nickname/?access={access_token}&refresh={refresh_token}&next=preference&nickname={encoded_nickname}')
    else:
        return redirect(f'/?access={access_token}&refresh={refresh_token}&nickname={encoded_nickname}')


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
            'name': r.get_display_title(),  # ✅ 한글 우선
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
                'name': f.recipe.get_display_title(),  # ✅ 한글 우선
                'image': f.recipe.image_url,
                'isFavorite': True
            })

    # 3. 내 식재료 (소비기한 임박한 순서 8개)
    ingredients = []
    if user.is_authenticated:
        # [Logic] is_consumed=False인 것만, expire_at 오름차순(급한거 먼저), NULL은 마지막에 배치
        ing_qs = UserIngredient.objects.filter(
            user=user, 
            is_consumed=False
        ).select_related('ingredient').order_by(
            F('expire_at').asc(nulls_last=True)
        )[:8]
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

    # 4. 내 일지 (최근 등록순 10개)
    diary_entries = []
    if user.is_authenticated:
        log_qs = RecipeLog.objects.filter(user=user).select_related('recipe').order_by('-created_at')[:10]
        for log in log_qs:
            # 일지 이미지가 있으면 쓰고, 없으면 Recipick 로고 사용
            display_image = log.image.url if log.image else static('images/Recipick_logo.png')
            
            diary_entries.append({
                'id': log.recipe_log_id,
                'title': log.recipe.get_display_title(),  # ✅ 한글 우선
                'date': log.cooked_at.strftime('%y.%m.%d'), # 26.01.11 형식
                'image': display_image
            })

    # Context에 담기 (recipeData는 JSON 문자열로 전달해 템플릿에서 파싱 오류 방지)
    context = {
        'recommended_recipes': json.dumps(recommended_recipes, ensure_ascii=False),
        'favorite_recipes': json.dumps(favorite_recipes, ensure_ascii=False),
        'ingredients': ingredients,
        'diary_entries': json.dumps(diary_entries, ensure_ascii=False),
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
        # (소비기한 지난 것도 보여주려면 이것도 필요. ingredients/views.py에는 지난거는 없기 때문.)
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
    
    return Response({'is_available': True}, status=200)

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