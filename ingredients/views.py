"""
Ingredients Views (개선 버전)

주요 개선사항:
1. 직접 추가 재료 처리 로직
2. 소비기한 관리 개선
3. API 응답 최적화
4. 에러 처리 강화
"""

import json
from datetime import date
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date
from django.db.models import Q, F

# DRF 관련
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

# 모델 및 시리얼라이저
from ingredients.models import IngredientMaster, IngredientCategory, UserIngredient
from ingredients.serializers import (
    IngredientSerializer, IngredientCategorySerializer, UserIngredientSerializer,
    UserIngredientCreateSerializer, UserIngredientUpdateSerializer, UserIngredientConsumeSerializer
)

# 매핑 유틸리티
from ingredients.utils.mapper import IngredientMapper

# 직접 추가 로직을 위한 구현
from .models import IngredientMaster, IngredientCategory 
from .serializers import IngredientSerializer


@api_view(['POST'])
def create_custom_ingredient(request):
    name = request.data.get('name')
    
    if not name:
        return Response({'error': '이름을 입력해주세요.'}, status=400)

    # 1. '직접 추가' 카테고리 찾기 (IngredientCategory 사용)
    try:
        category, _ = IngredientCategory.objects.get_or_create(name='직접 추가')
    except Exception as e:
        print(f"카테고리 생성 오류: {e}")
        category = None

    # 2. 식재료 생성 (IngredientMaster 사용)
    # 모델에 icon_name 필드가 없으므로 defaults에서 제외했습니다.
    ingredient, created = IngredientMaster.objects.get_or_create(
        name_ko=name,
        defaults={
            'category': category
        }
    )
    
    # 3. Serializer를 통해 프론트엔드 포맷(json)으로 변환
    serializer = IngredientSerializer(ingredient)
    return Response(serializer.data)

# ==================== API ViewSets (DRF) ==================== #

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
        
        # IngredientMapper 사용
        suggestions = IngredientMapper.suggest_matches(keyword, limit=10)
        serializer = self.get_serializer(suggestions, many=True)
        return Response(serializer.data)


class IngredientCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """식재료 카테고리 조회"""
    queryset = IngredientCategory.objects.all()
    serializer_class = IngredientCategorySerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def with_counts(self, request):
        """각 카테고리별 식재료 개수 포함"""
        categories = self.get_queryset()
        
        data = []
        for category in categories:
            data.append({
                'id': category.category_id,
                'name': category.name,
                'icon_url': category.icon_url,
                'ingredient_count': category.ingredients.count()
            })
        
        return Response(data)


class UserIngredientViewSet(viewsets.ModelViewSet):
    """사용자 보유 식재료 관리"""
    serializer_class = UserIngredientSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserIngredient.objects.filter(
            user=self.request.user,
            is_consumed=False
        ).select_related('ingredient', 'ingredient__category').order_by(
            F('expire_at').asc(nulls_last=True),
            'ingredient__name_ko'
        )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserIngredientCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserIngredientUpdateSerializer
        elif self.action == 'consume':
            return UserIngredientConsumeSerializer
        return UserIngredientSerializer
    
    def create(self, request, *args, **kwargs):
        """
        식재료 등록 (개선된 버전)

        Request Body:
        {
            "ingredient_id": 123,  // 기존 식재료 ID (선택)
            "ingredient_name": "토마토",  // 직접 입력 (선택)
            "expire_at": "2025-02-20",  // 소비기한 (선택)
            "is_direct_input": false  // 직접 입력 여부
        }
        """

        # [추가] 0. 식재료 개수 제한 (100개)
        current_count = UserIngredient.objects.filter(
            user=request.user, 
            is_consumed=False
        ).count()
        
        if current_count >= 100:
            return Response(
                {'error': '식재료는 최대 100개까지만 등록 가능합니다. 소진 처리 후 다시 등록해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ingredient_id = request.data.get('ingredient_id')
        ingredient_name = request.data.get('ingredient_name')
        is_direct_input = request.data.get('is_direct_input', False)
        expire_at = request.data.get('expire_at')
        
        # 1. 식재료 처리
        if ingredient_id:
            # 기존 식재료 사용
            try:
                ingredient = IngredientMaster.objects.get(ingredient_id=ingredient_id)
            except IngredientMaster.DoesNotExist:
                return Response(
                    {'error': '존재하지 않는 식재료입니다'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif ingredient_name and is_direct_input:
            # 직접 입력: IngredientMapper 사용
            ingredient = IngredientMapper.get_or_create_user_ingredient(
                user_input_name=ingredient_name,
                category_id=17  # 직접 추가 카테고리
            )
        else:
            return Response(
                {'error': 'ingredient_id 또는 ingredient_name이 필요합니다'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 2. 중복 확인
        existing = UserIngredient.objects.filter(
            user=request.user,
            ingredient=ingredient,
            is_consumed=False
        ).first()
        
        if existing:
            return Response(
                {
                    'error': '이미 등록된 식재료입니다',
                    'existing_id': existing.user_ingredient_id
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 3. 소비기한 파싱
        expire_date = None
        if expire_at:
            try:
                expire_date = parse_date(expire_at)
            except (ValueError, TypeError):
                return Response(
                    {'error': '잘못된 날짜 형식입니다 (YYYY-MM-DD)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 4. 생성
        user_ingredient = UserIngredient.objects.create(
            user=request.user,
            ingredient=ingredient,
            expire_at=expire_date,
            is_consumed=False
        )
        
        serializer = self.get_serializer(user_ingredient)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def update_expiry(self, request, pk=None):
        """소비기한 수정"""
        user_ingredient = self.get_object()
        expire_at = request.data.get('expire_at')
        
        if expire_at:
            try:
                user_ingredient.expire_at = parse_date(expire_at)
            except (ValueError, TypeError):
                return Response(
                    {'error': '잘못된 날짜 형식입니다'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            user_ingredient.expire_at = None
        
        user_ingredient.save()
        serializer = self.get_serializer(user_ingredient)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def consume(self, request, pk=None):
        """식재료 소진 처리"""
        user_ingredient = self.get_object()
        user_ingredient.is_consumed = True
        user_ingredient.save()
        
        return Response({'message': '식재료가 소진 처리되었습니다'})
    
    @action(detail=False, methods=['post'])
    def batch_consume(self, request):
        """여러 식재료 일괄 소진 처리"""
        ingredient_ids = request.data.get('ingredient_ids', [])
        
        if not ingredient_ids:
            return Response(
                {'error': 'ingredient_ids가 필요합니다'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_count = UserIngredient.objects.filter(
            user=request.user,
            user_ingredient_id__in=ingredient_ids,
            is_consumed=False
        ).update(is_consumed=True)
        
        return Response({
            'message': f'{updated_count}개 식재료가 소진 처리되었습니다',
            'count': updated_count
        })
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """유통기한 임박 식재료 조회 (D-3 이내)"""
        from datetime import timedelta
        
        threshold_date = date.today() + timedelta(days=3)
        
        expiring = UserIngredient.objects.filter(
            user=request.user,
            is_consumed=False,
            expire_at__lte=threshold_date,
            expire_at__gte=date.today()
        ).select_related('ingredient', 'ingredient__category').order_by('expire_at')
        
        serializer = self.get_serializer(expiring, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """카테고리별로 그룹화된 식재료 목록"""
        user_ingredients = self.get_queryset()
        
        # 카테고리별로 그룹화
        by_category = {}
        for ui in user_ingredients:
            cat_name = ui.ingredient.category.name if ui.ingredient.category else '기타'
            
            if cat_name not in by_category:
                by_category[cat_name] = []
            
            by_category[cat_name].append({
                'id': ui.user_ingredient_id,
                'ingredient_id': ui.ingredient.ingredient_id,
                'name': ui.ingredient.name_ko,
                'expire_at': ui.expire_at,
                'days_until_expiry': ui.days_until_expiry,
                'is_urgent': ui.is_urgent
            })
        
        return Response(by_category)


# ==================== 화면(Template) 뷰 ==================== #

@login_required
def my_fridge_view(request):
    """
    내 냉장고 페이지
    """
    # 사용자 식재료 조회
    user_ingredients = UserIngredient.objects.filter(
        user=request.user,
        is_consumed=False
    ).select_related('ingredient', 'ingredient__category').order_by(
        F('expire_at').asc(nulls_last=True),
        'ingredient__name_ko'
    )
    
    today = date.today()
    category_counts = {}
    
    # 데이터 가공
    for ui in user_ingredients:
        cat_name = ui.ingredient.category.name if ui.ingredient.category else '기타'
        category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
        
        # [추가] 카테고리 아이콘 URL을 템플릿으로 전달
        if ui.ingredient.category and ui.ingredient.category.icon_url:
            ui.display_icon = ui.ingredient.category.icon_url
        else:
            # 카테고리가 없거나 아이콘이 없는 경우 기본 이미지 (예: 기타)
            ui.display_icon = '/static/images/categories/etc.png'

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
    
    # 카테고리 리스트
    final_categories = [{'name': '전체', 'count': len(user_ingredients)}]
    for cat_name in sorted(category_counts.keys()):
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
    """
    # [POST] 데이터 저장
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            ingredient_id = data.get('ingredient_id')
            ingredient_name = data.get('ingredient_name')
            is_direct_input = data.get('is_direct_input', False)
            expire_at = data.get('expire_at')
            
            # 식재료 처리
            if ingredient_id:
                try:
                    ingredient = IngredientMaster.objects.get(ingredient_id=ingredient_id)
                except IngredientMaster.DoesNotExist:
                    return JsonResponse({'success': False, 'message': '존재하지 않는 식재료입니다'})
            
            elif ingredient_name and is_direct_input:
                # 직접 추가
                ingredient = IngredientMapper.get_or_create_user_ingredient(
                    user_input_name=ingredient_name,
                    category_id=17
                )
            else:
                return JsonResponse({'success': False, 'message': '식재료 정보가 필요합니다'})
            
            # 중복 확인
            existing = UserIngredient.objects.filter(
                user=request.user,
                ingredient=ingredient,
                is_consumed=False
            ).first()
            
            if existing:
                return JsonResponse({
                    'success': False,
                    'message': '이미 등록된 식재료입니다'
                })
            
            # 소비기한 파싱
            expire_date = None
            if expire_at:
                try:
                    expire_date = parse_date(expire_at)
                except (ValueError, TypeError):
                    return JsonResponse({'success': False, 'message': '잘못된 날짜 형식입니다'})
            
            # 생성
            user_ingredient = UserIngredient.objects.create(
                user=request.user,
                ingredient=ingredient,
                expire_at=expire_date,
                is_consumed=False
            )
            
            return JsonResponse({
                'success': True,
                'message': '식재료가 등록되었습니다',
                'ingredient_id': user_ingredient.user_ingredient_id
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': '잘못된 요청입니다'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    # [GET] 식재료 목록 제공
    # 사용자가 이미 보유한 식재료 ID 목록
    user_owned_ids = list(
        UserIngredient.objects.filter(
            user=request.user,
            is_consumed=False
        ).values_list('ingredient_id', flat=True)
    )
    
    # 모든 식재료 조회
    all_ingredients = IngredientMaster.objects.select_related('category').order_by(
        'category__category_id',
        'name_ko'
    )
    
    # 데이터 가공
    master_list = []
    category_counts = {}
    
    for ing in all_ingredients:
        cat_name = ing.category.name if ing.category else '기타'
        
        master_list.append({
            'id': ing.ingredient_id,
            'name': ing.name_ko,
            'category': cat_name,
            'category_id': ing.category.category_id if ing.category else None,
            'is_added': ing.ingredient_id in user_owned_ids
        })
        
        category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
    
    # 카테고리 리스트
    all_categories_db = IngredientCategory.objects.all().order_by('category_id')
    final_categories = [{'id': None, 'name': '전체', 'count': len(master_list)}]
    
    for cat in all_categories_db:
        count = category_counts.get(cat.name, 0)
        final_categories.append({
            'id': cat.category_id,
            'name': cat.name,
            'count': count,
            'icon_url': cat.icon_url
        })
    
    context = {
        'categories': final_categories,
        'ingredients': master_list
    }
    return render(request, 'ingredients/add_ingredient.html', context)


# ==================== JSON 데이터 제공 API ==================== #

@api_view(['GET'])
@permission_classes([AllowAny])
def category_list_view(request):
    """카테고리 목록 JSON"""
    categories = IngredientCategory.objects.all().order_by('category_id')
    data = []
    for cat in categories:
        data.append({
            "id": cat.category_id,
            "name": cat.name,
            "icon_url": cat.icon_url,
            "ingredient_count": cat.ingredients.count()
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def ingredient_list_view(request):
    """식재료 목록 JSON"""
    category_id = request.GET.get('category_id')
    keyword = request.GET.get('keyword')
    
    ingredients = IngredientMaster.objects.all().select_related('category')
    
    if category_id:
        ingredients = ingredients.filter(category_id=category_id)
    
    if keyword:
        # IngredientMapper 사용
        suggestions = IngredientMapper.suggest_matches(keyword, limit=20)
        ingredients = suggestions
    
    data = []
    for ing in ingredients:
        cat_name = ing.category.name if ing.category else "기타"
        
        data.append({
            "id": ing.ingredient_id,
            "name_ko": ing.name_ko,
            "name_en": ing.name_en,
            "category_id": ing.category.category_id if ing.category else None,
            "category_name": cat_name,
            "icon_url": ing.category.icon_url if ing.category else None
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_ingredient_view(request):
    """검색 전용 API"""
    keyword = request.GET.get('keyword', '')
    
    if not keyword:
        return Response([])
    
    # IngredientMapper 사용
    suggestions = IngredientMapper.suggest_matches(keyword, limit=10)
    
    data = []
    for ing in suggestions:
        data.append({
            "id": ing.ingredient_id,
            "name_ko": ing.name_ko,
            "name_en": ing.name_en,
            "category": ing.category.name if ing.category else "기타"
        })
    
    return Response(data)