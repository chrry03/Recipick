from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.shortcuts import render
from datetime import date, timedelta
from .models import IngredientMaster, IngredientCategory, UserIngredient
from .serializers import (
    IngredientSerializer,
    IngredientCategorySerializer,
    UserIngredientSerializer,
    UserIngredientCreateSerializer,
    UserIngredientUpdateSerializer,
    UserIngredientConsumeSerializer
)

# Create your views here.
class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """식재료 마스터 데이터 조회 (읽기 전용)"""
    
    queryset = IngredientMaster.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name_ko', 'name_en', 'aliases']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 카테고리 필터링
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # 키워드 검색 (한글명, 영문명, 별칭)
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
        """
        식재료 자동완성 검색
        GET /ingredients/search?keyword=토마토
        """
        keyword = request.query_params.get('keyword', '')
        if not keyword:
            return Response([])
        
        # IngredientMaster의 find_by_name 활용
        exact_match = IngredientMaster.find_by_name(keyword)
        if exact_match:
            serializer = self.get_serializer(exact_match)
            return Response([serializer.data])
        
        # 부분 일치 검색
        ingredients = IngredientMaster.objects.filter(
            Q(name_ko__icontains=keyword) |
            Q(name_en__icontains=keyword) |
            Q(aliases__icontains=keyword)
        ).select_related('category')[:10]
        
        serializer = self.get_serializer(ingredients, many=True)
        return Response(serializer.data)


class IngredientCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """식재료 카테고리 조회"""
    
    queryset = IngredientCategory.objects.all()
    serializer_class = IngredientCategorySerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # parent_id로 필터링
        parent_id = self.request.query_params.get('parent_id')
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        elif parent_id is None and not self.request.query_params.get('all'):
            # parent_id 파라미터가 없고 all도 없으면 최상위 카테고리만
            queryset = queryset.filter(parent__isnull=True)
        
        return queryset


class UserIngredientViewSet(viewsets.ModelViewSet):
    """사용자 식재료 관리"""
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return UserIngredient.objects.none()

        queryset = UserIngredient.objects.filter(user=user)

        is_consumed = self.request.query_params.get('is_consumed')
        if is_consumed is not None:
            queryset = queryset.filter(
                is_consumed=is_consumed.lower() in ['true', '1']
            )

        include_expired = self.request.query_params.get('include_expired', 'true')
        if include_expired.lower() in ['false', '0']:
            queryset = queryset.filter(
                Q(expire_at__isnull=True) |
                Q(expire_at__gte=date.today())
            )

        return queryset.select_related('ingredient', 'ingredient__category')

    
    def get_serializer_class(self):
        """액션에 따라 다른 시리얼라이저 사용"""
        if self.action == 'create':
            return UserIngredientCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserIngredientUpdateSerializer
        elif self.action == 'consume':
            return UserIngredientConsumeSerializer
        return UserIngredientSerializer
    
    def create(self, request, *args, **kwargs):
        """식재료 등록"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # 응답은 상세 정보로
        response_serializer = UserIngredientSerializer(serializer.instance)
        headers = self.get_success_headers(serializer.data)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """
        유통기한 임박 식재료 조회
        GET /user-ingredients/expiring?days_threshold=5
        """
        days_threshold = int(request.query_params.get('days_threshold', 5))
        
        # UserIngredient 모델의 클래스 메서드 활용
        ingredients = UserIngredient.get_expiring_soon_ingredients(
            user=request.user,
            days_threshold=days_threshold
        )
        
        serializer = UserIngredientSerializer(ingredients, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expired(self, request):
        """
        유통기한 지난 식재료 조회
        GET /user-ingredients/expired
        """
        ingredients = UserIngredient.get_expired_ingredients(user=request.user)
        serializer = UserIngredientSerializer(ingredients, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def consume(self, request, pk=None):
        """
        식재료 소비 처리
        PATCH /user-ingredients/{id}/consume
        Body: { "is_consumed": true }
        """
        ingredient = self.get_object()
        serializer = self.get_serializer(ingredient, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # 응답은 상세 정보로
        response_serializer = UserIngredientSerializer(ingredient)
        return Response(response_serializer.data)


def my_fridge_view(request):
    # 빈 리스트를 보내서 'Empty State' 화면 유지
    ingredients = [] 
    return render(request, 'ingredients/my_fridge.html', {'ingredients': ingredients})


def add_ingredient_view(request):
    # 1. 요청하신 카테고리 전체 목록
    categories = [
        "전체", "채소", "양념", "해산물", "조미료", 
        "곡물/면류", "제빵", "과일", "육류", "가공식품", 
        "음료", "건조", "유제품/계란", "절임", "기타"
    ]
    
    # 2. 식재료 마스터 데이터 (아이콘 매칭)
    # 아이콘이 있는 것은 파일명을 적고, 없는 것은 None으로 두어 기본 접시가 뜨게 함
    master_ingredients = [
        # --- 아이콘 보유 ---
        {'name': '당근', 'category': '채소', 'is_added': False, 'icon_name': 'carrot.png'},
        {'name': '소고기', 'category': '육류', 'is_added': False, 'icon_name': 'beef.png'},
        {'name': '돼지고기', 'category': '육류', 'is_added': False, 'icon_name': 'pork.png'},
        {'name': '우유', 'category': '유제품/계란', 'is_added': False, 'icon_name': 'milk.png'},
        {'name': '계란', 'category': '유제품/계란', 'is_added': True, 'icon_name': 'egg.png'}, # 이미 추가됨 예시
        
        # --- 아이콘 미보유 (기본 이미지) ---
        {'name': '브로콜리', 'category': '채소', 'is_added': False, 'icon_name': None},
        {'name': '양파', 'category': '채소', 'is_added': False, 'icon_name': None},
        {'name': '사과', 'category': '과일', 'is_added': False, 'icon_name': None},
        {'name': '대파', 'category': '채소', 'is_added': False, 'icon_name': None},
        {'name': '고등어', 'category': '해산물', 'is_added': False, 'icon_name': None},
        {'name': '식빵', 'category': '제빵', 'is_added': False, 'icon_name': None},
        {'name': '간장', 'category': '조미료', 'is_added': False, 'icon_name': None},
    ]

    context = {
        'categories': categories,
        'ingredients': master_ingredients,
    }
    return render(request, 'ingredients/add_ingredient.html', context)