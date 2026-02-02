import json
from datetime import date
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date
from django.db.models import Q

# DRF 관련 임포트
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

# 모델 및 시리얼라이저
from .models import IngredientMaster, IngredientCategory, UserIngredient
from .serializers import (
    IngredientSerializer, IngredientCategorySerializer, UserIngredientSerializer,
    UserIngredientCreateSerializer, UserIngredientUpdateSerializer, UserIngredientConsumeSerializer
)

# 아이콘 매핑
ICON_MAP = {
    '당근': 'carrot.png', '소고기': 'beef.png', '돼지고기': 'pork.png',
    '우유': 'milk.png', '계란': 'egg.png',
}

# 카테고리 목록 (공통 사용)
CATEGORY_LIST = [
    "전체", "채소", "양념", "해산물", "조미료", 
    "곡물/면류", "제빵", "과일", "육류", "가공식품", 
    "음료", "건조", "유제품/계란", "절임", "기타"
]

# ==================== 1. API ViewSets ==================== #
class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
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
        keyword = request.query_params.get('keyword', '')
        if not keyword: return Response([])
        if hasattr(IngredientMaster, 'find_by_name'):
            exact_match = IngredientMaster.find_by_name(keyword)
            if exact_match:
                serializer = self.get_serializer(exact_match)
                return Response([serializer.data])
        ingredients = IngredientMaster.objects.filter(
            Q(name_ko__icontains=keyword) |
            Q(name_en__icontains=keyword) |
            Q(aliases__icontains=keyword)
        ).select_related('category')[:10]
        serializer = self.get_serializer(ingredients, many=True)
        return Response(serializer.data)

class IngredientCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IngredientCategory.objects.all()
    serializer_class = IngredientCategorySerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        queryset = super().get_queryset()
        parent_id = self.request.query_params.get('parent_id')
        if parent_id: queryset = queryset.filter(parent_id=parent_id)
        elif parent_id is None and not self.request.query_params.get('all'):
            queryset = queryset.filter(parent__isnull=True)
        return queryset

class UserIngredientViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated: return UserIngredient.objects.none()
        queryset = UserIngredient.objects.filter(user=user)
        is_consumed = self.request.query_params.get('is_consumed')
        if is_consumed is not None:
            queryset = queryset.filter(is_consumed=is_consumed.lower() in ['true', '1'])
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

# ==================== 2. 템플릿 뷰 ==================== #

@login_required
def my_fridge_view(request):
    """내 냉장고 페이지"""
    user_ingredients = UserIngredient.objects.filter(
        user=request.user,
        is_consumed=False
    ).select_related('ingredient', 'ingredient__category').order_by('expire_at')
    
    # 1. D-Day 및 아이콘 처리
    today = date.today()
    for ui in user_ingredients:
        if ui.expire_at:
            ui.days_left = (ui.expire_at - today).days
        else:
            ui.days_left = 999
        
        ing_name = ui.ingredient.name_ko
        ui.ingredient.icon_name = ICON_MAP.get(ing_name, None)

    # 2. [NEW] 카테고리별 개수 세기
    # 딕셔너리 초기화: {'채소': 0, '육류': 0 ...}
    category_counts = {cat: 0 for cat in CATEGORY_LIST if cat != "전체"}
    
    for ui in user_ingredients:
        # DB에 저장된 카테고리 이름 가져오기
        cat_name = ui.ingredient.category.name if ui.ingredient.category else '기타'
        if cat_name in category_counts:
            category_counts[cat_name] += 1
    
    # 3. 템플릿에 보낼 데이터 구성 (이름, 개수)
    # "전체"는 따로 계산
    final_categories = [{'name': '전체', 'count': len(user_ingredients)}]
    for cat in CATEGORY_LIST:
        if cat == "전체": continue
        final_categories.append({
            'name': cat,
            'count': category_counts.get(cat, 0)
        })

    context = {
        'ingredients': user_ingredients,
        'categories': final_categories # 개수 정보가 포함된 카테고리 리스트
    }
    return render(request, 'ingredients/my_fridge.html', context)

@login_required
def add_ingredient_view(request):
    """식재료 추가 페이지"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data.get('ingredients', [])
            for item in items:
                name = item.get('name')
                expiry = item.get('expiry_date')
                category_name = item.get('category')

                category, _ = IngredientCategory.objects.get_or_create(name=category_name)
                ingredient_master, _ = IngredientMaster.objects.get_or_create(
                    name_ko=name,
                    defaults={'category': category}
                )
                UserIngredient.objects.update_or_create(
                    user=request.user,
                    ingredient=ingredient_master,
                    defaults={'expire_at': parse_date(expiry), 'is_consumed': False}
                )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # 마스터 데이터 (하드코딩된 예시)
    master_ingredients = [
        {'id': 1, 'name': '당근', 'category': '채소', 'icon_name': 'carrot.png'},
        {'id': 2, 'name': '소고기', 'category': '육류', 'icon_name': 'beef.png'},
        {'id': 3, 'name': '돼지고기', 'category': '육류', 'icon_name': 'pork.png'},
        {'id': 4, 'name': '우유', 'category': '유제품/계란', 'icon_name': 'milk.png'},
        {'id': 5, 'name': '계란', 'category': '유제품/계란', 'icon_name': 'egg.png'},
        {'id': 6, 'name': '브로콜리', 'category': '채소', 'icon_name': None},
        {'id': 7, 'name': '양파', 'category': '채소', 'icon_name': None},
        {'id': 8, 'name': '사과', 'category': '과일', 'icon_name': None},
        {'id': 9, 'name': '대파', 'category': '채소', 'icon_name': None},
        {'id': 10, 'name': '고등어', 'category': '해산물', 'icon_name': None},
        {'id': 11, 'name': '식빵', 'category': '제빵', 'icon_name': None},
        {'id': 12, 'name': '간장', 'category': '조미료', 'icon_name': None},
        {'id': 13, 'name': '가지', 'category': '채소', 'icon_name': None},
        {'id': 14, 'name': '감자', 'category': '채소', 'icon_name': None},
        {'id': 15, 'name': '검은콩', 'category': '채소', 'icon_name': None},
        {'id': 16, 'name': '고구마', 'category': '채소', 'icon_name': None},
        {'id': 17, 'name': '고사리', 'category': '채소', 'icon_name': None},
        {'id': 18, 'name': '고추', 'category': '채소', 'icon_name': None},
        {'id': 19, 'name': '고수', 'category': '채소', 'icon_name': None},
        {'id': 20, 'name': '곤드레', 'category': '채소', 'icon_name': None},
        {'id': 21, 'name': '공심채', 'category': '채소', 'icon_name': None},
        {'id': 22, 'name': '깻잎', 'category': '채소', 'icon_name': None},
        {'id': 23, 'name': '꽈리 고추', 'category': '채소', 'icon_name': None},
        {'id': 24, 'name': '나물', 'category': '채소', 'icon_name': None},
        {'id': 25, 'name': '냉이', 'category': '채소', 'icon_name': None},
        {'id': 26, 'name': '느타리버섯', 'category': '채소', 'icon_name': None},
        {'id': 27, 'name': '단호박', 'category': '채소', 'icon_name': None},
        {'id': 28, 'name': '달래', 'category': '채소', 'icon_name': None},
    ]

    # [NEW] 이미 보유한 재료 확인
    user_owned_names = set(
        UserIngredient.objects.filter(
            user=request.user, 
            is_consumed=False
        ).values_list('ingredient__name_ko', flat=True)
    )
    for item in master_ingredients:
        item['is_added'] = item['name'] in user_owned_names

    # [NEW] 카테고리별 개수 세기 (Add 페이지용 - 전체 목록 기준)
    category_counts = {cat: 0 for cat in CATEGORY_LIST if cat != "전체"}
    for item in master_ingredients:
        c_name = item['category']
        if c_name in category_counts:
            category_counts[c_name] += 1
            
    final_categories = [{'name': '전체', 'count': len(master_ingredients)}]
    for cat in CATEGORY_LIST:
        if cat == "전체": continue
        final_categories.append({
            'name': cat,
            'count': category_counts.get(cat, 0)
        })

    context = {
        'categories': final_categories, 
        'ingredients': master_ingredients
    }
    return render(request, 'ingredients/add_ingredient.html', context)