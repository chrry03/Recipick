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
        # 난이도 3개 별 (EASY 1, NORMAL 2, DIFFICULT 3)
        diff_score = {'EASY': 1, 'NORMAL': 2, 'DIFFICULT': 3}.get(log.perceived_difficulty, 2)
        
        display_logs.append({
            'id': log.recipe_log_id,
            'day': log.cooked_at.day,
            'time': timezone.localtime(log.created_at).strftime('%H:%M'),
            'recipe_name': log.recipe.get_display_title(),  # ✅ 한글 우선
            # 이미지가 있으면 URL, 없으면 None
            'image': log.image.url if log.image else None,
            # 난이도 3개 별, 만족도 5개 별
            'difficulty_stars': '★' * diff_score + '☆' * (3 - diff_score),
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
    recipe = log.recipe

    # 레시피 재료: RecipeIngredient에서 가져와 표시용 문자열로 만듦
    ingredients_parts = []
    for ri in recipe.recipe_ingredients.select_related('ingredient').all():
        if ri.ingredient:
            name = ri.ingredient.name_ko or ri.ingredient.name_en or ri.ingredient_name or '알 수 없는 재료'
        else:
            name = ri.ingredient_name or '알 수 없는 재료'
        if ri.is_optional:
            name = f"{name}(선택)"
        ingredients_parts.append(name)
    ingredients_text = ', '.join(ingredients_parts) if ingredients_parts else '재료 정보 없음'

    # 템플릿용 데이터 정리 (난이도 3개 별, 만족도 5개 별)
    diff_score = {'EASY': 1, 'NORMAL': 2, 'DIFFICULT': 3}.get(log.perceived_difficulty, 2)
    context = {
        'log': {
            'id': log.recipe_log_id,
            'date': log.cooked_at.strftime('%m월 %d일'),
            'time': timezone.localtime(log.created_at).strftime('%H:%M'),
            'recipe_name': recipe.get_display_title(),  # ✅ 한글 우선
            'recipe_image': recipe.image_url,
            'difficulty': '★' * diff_score + '☆' * (3 - diff_score),
            'satisfaction': '★' * log.rating + '☆' * (5 - log.rating),
            'ingredients': ingredients_text,
            'recipe_steps': recipe.instructions if recipe.instructions else [],
            'memo': log.memo,
            'image': log.image.url if log.image else None,
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
        data = request.POST.copy()
        # 난이도·만족도 미선택 시 기본값 적용
        if not data.get('difficulty') or data.get('difficulty') not in dict(RecipeLog.PerceivedDifficulty.choices):
            data['difficulty'] = 'NORMAL'
        try:
            r = int(data.get('rating', 3))
            if not (1 <= r <= 5):
                data['rating'] = 3
        except (TypeError, ValueError):
            data['rating'] = 3
        # 이미지 파일은 별도로 넣어줘야 함 (form-data 특성상). 빈 파일은 제외
        if request.FILES.get('image') and request.FILES['image'].size > 0:
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
    
    # 작성 시 기본값 (난이도·만족도 미선택 시 사용)
    context = {
        'recipe_id': recipe_id,
        'recipe_name': recipe_name,
        'log': type('Log', (), {
            'perceived_difficulty': 'NORMAL',
            'rating': 3,
            'memo': '',
            'cooked_at': timezone.now().date(),
            'image': None
        })()
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
        data = request.POST.copy()
        # 사진 삭제 요청
        if request.POST.get('remove_image') in ('1', 'true', 'yes'):
            data['image'] = None
        else:
            # 새 이미지를 선택했을 때만 반영 (없으면 기존 이미지 유지)
            new_image = request.FILES.get('image')
            if new_image and new_image.size > 0:
                data['image'] = new_image
            else:
                data.pop('image', None)  # POST에 빈 값으로 올 수 있으므로 제거
        # 난이도가 폼에서 오는 그대로 반영되도록 data에 확실히 넣음
        difficulty_raw = request.POST.get('difficulty', '').strip()
        if difficulty_raw in dict(RecipeLog.PerceivedDifficulty.choices):
            data['difficulty'] = difficulty_raw
        serializer = RecipeLogCreateSerializer(data=data, instance=log, partial=True)
        if serializer.is_valid():
            # save()에 난이도 직접 전달해 수정 시에도 반영되게 함
            save_kwargs = {}
            if difficulty_raw in dict(RecipeLog.PerceivedDifficulty.choices):
                save_kwargs['perceived_difficulty'] = difficulty_raw
            serializer.save(**save_kwargs)
            messages.success(request, "일지가 수정되었습니다.")
            return redirect('logs:detail', pk=log.pk)
        else:
            messages.error(request, f"수정 오류: {serializer.errors}")
    
    # GET 요청: 기존 데이터를 화면에 뿌려줌
    context = {
        'log': log, # 기존 일지 객체
        'recipe_name': log.recipe.get_display_title(),  # ✅ 한글 우선
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