import json
from datetime import date
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date
from django.db.models import Q, F

# DRF 관련 임포트
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

# 모델 및 시리얼라이저
from .models import IngredientMaster, IngredientCategory, UserIngredient
from .serializers import (
    IngredientSerializer, IngredientCategorySerializer, UserIngredientSerializer,
    UserIngredientCreateSerializer, UserIngredientUpdateSerializer, UserIngredientConsumeSerializer
)

# [설정] 아이콘 매핑 (DB에 아이콘 정보가 없는 경우를 위한 매핑)
# 추후 DB IngredientMaster 모델에 icon 필드를 추가하여 이 부분도 제거하는 것을 권장합니다.
ICON_MAP = {
    '당근': 'carrot.png', '소고기': 'beef.png', '돼지고기': 'pork.png',
    '우유': 'milk.png', '계란': 'egg.png',
}

# ==================== 1. API ViewSets (DRF) ==================== #

class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """식재료 마스터 데이터 조회 (검색, 필터링)"""
    queryset = IngredientMaster.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name_ko', 'name_en', 'aliases']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        keyword = self.request.query_params.get('keyword')
        if keyword:
            queryset = queryset.filter(
                Q(name_ko__icontains=keyword) |
                Q(name_en__icontains=keyword) |
                Q(aliases__icontains=keyword)
            )
        return queryset.select_related('category')
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """키워드 검색 (자동완성 등)"""
        keyword = request.query_params.get('keyword', '')
        if not keyword:
            return Response([])
            
        # 정확히 일치하는 것이 있으면 우선 반환
        if hasattr(IngredientMaster, 'find_by_name'):
            exact_match = IngredientMaster.find_by_name(keyword)
            if exact_match:
                serializer = self.get_serializer(exact_match)
                return Response([serializer.data])
                
        # 포함 검색
        ingredients = IngredientMaster.objects.filter(
            Q(name_ko__icontains=keyword) |
            Q(name_en__icontains=keyword) |
            Q(aliases__icontains=keyword)
        ).select_related('category')[:10]
        
        serializer = self.get_serializer(ingredients, many=True)
        return Response(serializer.data)

class IngredientCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """카테고리 조회"""
    queryset = IngredientCategory.objects.all()
    serializer_class = IngredientCategorySerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        parent_id = self.request.query_params.get('parent_id')
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        elif parent_id is None and not self.request.query_params.get('all'):
            # 기본적으로 대분류만 조회
            queryset = queryset.filter(parent__isnull=True)
        return queryset

class UserIngredientViewSet(viewsets.ModelViewSet):
    """사용자 냉장고 식재료 관리 (CRUD)"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return UserIngredient.objects.none()
            
        queryset = UserIngredient.objects.filter(user=user)
        
        # 소비 여부 필터
        is_consumed = self.request.query_params.get('is_consumed')
        if is_consumed is not None:
            queryset = queryset.filter(is_consumed=is_consumed.lower() in ['true', '1'])
            
        # 만료된 재료 포함 여부 (기본값: true)
        include_expired = self.request.query_params.get('include_expired', 'true')
        if include_expired.lower() in ['false', '0']:
            queryset = queryset.filter(Q(expire_at__isnull=True) | Q(expire_at__gte=date.today()))
            
        return queryset.select_related('ingredient', 'ingredient__category')

    def get_serializer_class(self):
        if self.action == 'create': return UserIngredientCreateSerializer
        elif self.action in ['update', 'partial_update']: return UserIngredientUpdateSerializer
        elif self.action == 'consume': return UserIngredientConsumeSerializer
        return UserIngredientSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        response_serializer = UserIngredientSerializer(serializer.instance)
        headers = self.get_success_headers(serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=False, methods=['get'])
    def expiring(self, request):
        days_threshold = int(request.query_params.get('days_threshold', 5))
        ingredients = UserIngredient.get_expiring_soon_ingredients(user=request.user, days_threshold=days_threshold)
        serializer = UserIngredientSerializer(ingredients, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expired(self, request):
        ingredients = UserIngredient.get_expired_ingredients(user=request.user)
        serializer = UserIngredientSerializer(ingredients, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def consume(self, request, pk=None):
        ingredient = self.get_object()
        serializer = self.get_serializer(ingredient, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response_serializer = UserIngredientSerializer(ingredient)
        return Response(response_serializer.data)


# ==================== 2. 화면(Template) 뷰 ==================== #

@login_required
def my_fridge_view(request):
    """
    내 냉장고 페이지
    - 정렬: 유통기한 임박(NULL은 뒤로) -> 이름순
    - 하드코딩 제거: DB에서 카테고리 로드
    """
    # 1. 쿼리 및 정렬 (유통기한 오름차순, NULL은 마지막에 배치)
    user_ingredients = UserIngredient.objects.filter(
        user=request.user,
        is_consumed=False
    ).select_related('ingredient', 'ingredient__category').order_by(
        F('expire_at').asc(nulls_last=True), 
        'ingredient__name_ko'
    )
    
    today = date.today()
    category_counts = {} # {'채소': 2, ...}
    
    # 2. 데이터 가공
    for ui in user_ingredients:
        # 아이콘 매핑
        ing_name = ui.ingredient.name_ko
        ui.ingredient.icon_name = ICON_MAP.get(ing_name, None)
        
        # 카테고리 카운트
        cat_name = ui.ingredient.category.name if ui.ingredient.category else '기타'
        category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
        
        # D-Day 태그 생성
        if ui.expire_at:
            delta = (ui.expire_at - today).days
            if delta < 0:
                ui.d_day_tag = "만료"
                ui.is_urgent = True
            elif delta == 0:
                ui.d_day_tag = "D-Day"
                ui.is_urgent = True
            else:
                ui.d_day_tag = f"D-{delta}"
                ui.is_urgent = (delta <= 3)
        else:
            ui.d_day_tag = "-"
            ui.is_urgent = False

    # 3. 카테고리 리스트 생성 (DB 기반)
    # DB에 있는 모든 카테고리를 가져와서 0개라도 표시할지, 있는 것만 표시할지 결정
    # 여기서는 있는 것 + 전체만 표시하는 로직으로 구성
    final_categories = [{'name': '전체', 'count': len(user_ingredients)}]
    
    # 카테고리 이름 순으로 정렬하여 추가
    sorted_cats = sorted(category_counts.keys())
    for cat_name in sorted_cats:
        final_categories.append({
            'name': cat_name,
            'count': category_counts[cat_name]
        })

    context = {
        'ingredients': user_ingredients,
        'categories': final_categories
    }
    return render(request, 'ingredients/my_fridge.html', context)


@login_required
def add_ingredient_view(request):
    """
    식재료 추가 페이지
    - 하드코딩 제거: DB의 IngredientMaster 데이터를 조회하여 표시
    """
    # [POST] 데이터 저장
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # 1. 추가/수정
            added_items = data.get('added', [])
            for item in added_items:
                name = item.get('name')
                expiry = item.get('expiry_date')
                category_name = item.get('category', '기타')

                # 카테고리 (없으면 생성)
                category, _ = IngredientCategory.objects.get_or_create(name=category_name)
                
                # 마스터 데이터 (없으면 생성)
                ingredient_master, _ = IngredientMaster.objects.get_or_create(
                    name_ko=name,
                    defaults={'category': category}
                )
                
                # [수정] 날짜 처리 (빈 문자열 -> None 변환)
                expire_date_obj = parse_date(expiry) if expiry else None

                UserIngredient.objects.update_or_create(
                    user=request.user,
                    ingredient=ingredient_master,
                    defaults={
                        'expire_at': expire_date_obj,
                        'is_consumed': False
                    }
                )

            # 2. 삭제 (선택 취소한 항목)
            removed_items = data.get('removed', [])
            if removed_items:
                UserIngredient.objects.filter(
                    user=request.user, 
                    ingredient__name_ko__in=removed_items
                ).delete()

            return JsonResponse({'status': 'success'})
        except Exception as e:
            print(f"Error in add_ingredient_view: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # [GET] 화면 렌더링
    # 1. DB에서 모든 마스터 식재료 조회
    all_ingredients = IngredientMaster.objects.all().select_related('category').order_by('name_ko')
    
    # 2. 사용자가 이미 보유한 식재료 ID 조회 (체크박스 표시용)
    user_owned_ids = set(
        UserIngredient.objects.filter(
            user=request.user, 
            is_consumed=False
        ).values_list('ingredient_id', flat=True)
    )
    
    # 3. 데이터 가공
    master_list = []
    category_counts = {} # {'채소': 5, ...}

    for ing in all_ingredients:
        # 아이콘
        icon = ICON_MAP.get(ing.name_ko, None)
        # 카테고리명
        cat_name = ing.category.name if ing.category else '기타'
        
        master_list.append({
            'id': ing.ingredient_id,
            'name': ing.name_ko,
            'category': cat_name,
            'icon_name': icon,
            'is_added': ing.ingredient_id in user_owned_ids
        })
        
        # 카테고리 카운트
        category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

    # 4. 카테고리 리스트 구성 (DB에 존재하는 카테고리 기준)
    all_categories_db = IngredientCategory.objects.all().order_by('category_id')
    final_categories = [{'name': '전체', 'count': len(master_list)}]
    
    for cat in all_categories_db:
        count = category_counts.get(cat.name, 0)
        final_categories.append({
            'name': cat.name,
            'count': count
        })

    context = {
        'categories': final_categories, 
        'ingredients': master_list
    }
    return render(request, 'ingredients/add_ingredient.html', context)


# ==================== 3. JSON 데이터 제공 API (Users 앱 등 활용) ==================== #

@api_view(['GET'])
@permission_classes([AllowAny])
def category_list_view(request):
    """카테고리 목록 JSON"""
    categories = IngredientCategory.objects.all().order_by('category_id')
    data = []
    for cat in categories:
        data.append({
            "id": cat.pk,
            "name": cat.name,
            "icon_url": cat.icon_url
        })
    return Response(data)

@api_view(['GET'])
@permission_classes([AllowAny])
def ingredient_list_view(request):
    """식재료 목록 JSON (Add 페이지 비동기 로드용)"""
    category_id = request.GET.get('category_id')
    keyword = request.GET.get('keyword')

    ingredients = IngredientMaster.objects.all().select_related('category')

    if category_id:
        ingredients = ingredients.filter(category_id=category_id)
    
    if keyword:
        ingredients = ingredients.filter(name_ko__icontains=keyword)
    
    data = []
    for ing in ingredients:
        icon_file = ICON_MAP.get(ing.name_ko, None)
        cat_name = ing.category.name if ing.category else "기타"
        
        data.append({
            "id": ing.pk,
            "name_ko": ing.name_ko,
            "category_id": ing.category.pk if ing.category else None,
            "category_name": cat_name,
            "icon_name": icon_file 
        })
    return Response(data)

@api_view(['GET'])
@permission_classes([AllowAny])
def search_ingredient_view(request):
    """검색 전용 API"""
    keyword = request.GET.get('keyword', '')
    if keyword:
        ingredients = IngredientMaster.objects.filter(name_ko__icontains=keyword)
    else:
        ingredients = []

    data = [{"name_ko": ing.name_ko} for ing in ingredients]
    return Response(data)