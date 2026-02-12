from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, timedelta

from .models import RecipeLog
from recipes.models import Recipe
from .serializers import RecipeLogCreateSerializer # 작성 시 유효성 검사용으로 사용

# =============================================================
# 1. 일지 목록 (HTML + 데이터 함께 전송)
# =============================================================
@login_required(login_url='/users/login/')
def log_list_view(request):
    """
    월별 일지 목록을 보여줍니다.
    URL 예시: /logs/?year=2026&month=2
    """
    # 1. 현재 날짜 구하기 (또는 URL 파라미터 받기)
    today = timezone.now()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # 2. DB에서 해당 연/월의 내 일지 가져오기
    logs = RecipeLog.objects.filter(
        user=request.user,
        cooked_at__year=year, 
        cooked_at__month=month
    ).order_by('-cooked_at', '-created_at')

    # 3. 템플릿에서 쓰기 좋게 데이터 가공 (별점 숫자 -> 별 문자)
    display_logs = []
    for log in logs:
        # 난이도 문자열 변환 (EASY -> 1개, NORMAL -> 2개...)
        diff_score = {'EASY':1, 'NORMAL':2, 'DIFFICULT':3}.get(log.perceived_difficulty, 1)
        
        display_logs.append({
            'id': log.recipe_log_id,
            'day': log.cooked_at.day,
            'time': log.created_at.strftime('%H:%M'),
            'recipe_name': log.recipe.title,
            # 이미지가 있으면 URL, 없으면 None
            'image': log.image.url if log.image else None,
            # 화면에 바로 뿌릴 별 문자열 (예: ★★★☆☆)
            'difficulty_stars': '★' * diff_score + '☆' * (3 - diff_score), # 난이도는 3점 만점 기준
            'satisfaction_stars': '★' * log.rating + '☆' * (5 - log.rating),
        })

    # 4. 이전달/다음달 버튼 링크 계산
    # (현재 1월이면 이전달은 작년 12월, 다음달은 2월...)
    curr_date = datetime(year, month, 1)
    prev_date = curr_date - timedelta(days=1)
    next_date = curr_date + timedelta(days=32)
    
    context = {
        'current_year': year,
        'current_month': month,
        'logs': display_logs, # 가공된 로그 데이터
        'prev_year': prev_date.year,
        'prev_month': prev_date.month,
        'next_year': next_date.year,
        'next_month': next_date.month,
    }
    return render(request, 'logs/log_list.html', context)


# =============================================================
# 2. 일지 상세 (HTML + 데이터 함께 전송)
# =============================================================
@login_required(login_url='/users/login/')
def log_detail_view(request, pk):
    """
    일지 상세 내용을 보여줍니다.
    """
    log = get_object_or_404(RecipeLog, pk=pk)
    
    # 템플릿용 데이터 정리
    context = {
        'log': {
            'id': log.recipe_log_id,
            'date': log.cooked_at.strftime('%m월 %d일'),
            'time': log.created_at.strftime('%H:%M'),
            'recipe_name': log.recipe.title,
            'recipe_image': log.recipe.image_url, # 레시피 원본 썸네일
            'difficulty': log.get_perceived_difficulty_display(), # '쉬움', '보통' 등으로 자동 변환
            'satisfaction': '★' * log.rating,
            'ingredients': "재료 정보 없음", # (추후 RecipeIngredient 연결 필요)
            'recipe_steps': log.recipe.instructions if log.recipe.instructions else [],
            'memo': log.memo,
            'image': log.image.url if log.image else None, # 내가 찍은 사진
        }
    }
    return render(request, 'logs/log_detail.html', context)


# =============================================================
# 3. 일지 작성 (GET: 화면, POST: 저장)
# =============================================================
@login_required(login_url='/users/login/')
def log_create_view(request):
    """
    GET: 작성 폼 화면을 보여줍니다.
    POST: 작성된 데이터를 저장합니다.
    """
    if request.method == 'POST':
        # 1. Serializer를 이용해 데이터 검증 (팀장님이 짠 코드 활용!)
        # request.data 대신 request.POST, request.FILES를 넘겨줍니다.
        serializer = RecipeLogCreateSerializer(data=request.POST)
        
        # 이미지 파일은 별도로 넣어줘야 함 (form-data 특성상)
        if 'image' in request.FILES:
            # request.POST는 수정 불가능(Immutable)해서 copy() 필요할 수도 있지만,
            # DRF Serializer는 initial_data에 파일과 데이터를 같이 넘기면 처리 가능합니다.
            data = request.POST.copy()
            data['image'] = request.FILES['image']
            serializer = RecipeLogCreateSerializer(data=data)

        if serializer.is_valid():
            # 2. 저장 (user는 현재 로그인한 사람)
            serializer.save(user=request.user)
            messages.success(request, "일지가 저장되었습니다!")
            return redirect('logs:list') # 목록으로 이동
        else:
            # 실패 시 에러 메시지와 함께 다시 입력창으로
            messages.error(request, f"입력 오류: {serializer.errors}")
            # 입력했던 내용 유지하기 위해 context에 담음
            return render(request, 'logs/log_create.html', {'errors': serializer.errors})

    # --- GET 요청 (화면 보여주기) ---
    # URL에서 레시피 ID와 제목을 가져옴 (예: /logs/create/?recipe_id=10&title=김치찌개)
    recipe_id = request.GET.get('recipe_id')
    recipe_name = request.GET.get('title', '요리 이름 없음')
    
    context = {
        'recipe_id': recipe_id,
        'recipe_name': recipe_name
    }
    return render(request, 'logs/log_create.html', context)

# =============================================================
# 4. 일지 수정 (GET: 기존 데이터 채운 폼, POST: 수정 반영)
# =============================================================
@login_required(login_url='/users/login/')
def log_update_view(request, pk):
    # 내 일지인지 확인 (남의 것은 404)
    log = get_object_or_404(RecipeLog, pk=pk, user=request.user)

    if request.method == 'POST':
        # 기존 instance를 넣어줘야 '수정' 모드로 동작함
        serializer = RecipeLogCreateSerializer(data=request.POST, instance=log)
        
        # 이미지 파일 처리
        if 'image' in request.FILES:
            data = request.POST.copy()
            data['image'] = request.FILES['image']
            serializer = RecipeLogCreateSerializer(data=data, instance=log)

        if serializer.is_valid():
            serializer.save()
            messages.success(request, "일지가 수정되었습니다.")
            return redirect('logs:detail', pk=log.pk)
        else:
            messages.error(request, f"수정 오류: {serializer.errors}")
    
    # GET 요청: 기존 데이터를 화면에 뿌려줌
    context = {
        'log': log, # 기존 일지 객체
        'recipe_name': log.recipe.title,
        'recipe_id': log.recipe.recipe_id,
        'is_edit': True # 템플릿에서 '작성' vs '수정' 구분용
    }
    return render(request, 'logs/log_create.html', context)

# =============================================================
# 5. 일지 삭제 (POST 요청만 허용)
# =============================================================
@login_required(login_url='/users/login/')
def log_delete_view(request, pk):
    log = get_object_or_404(RecipeLog, pk=pk, user=request.user)
    
    if request.method == 'POST':
        log.delete()
        messages.success(request, "일지가 삭제되었습니다.")
        return redirect('logs:list')
    
    # 만약 주소창에 직접 쳐서 GET으로 들어오면 상세페이지로 튕겨냄 (안전장치)
    return redirect('logs:detail', pk=pk)