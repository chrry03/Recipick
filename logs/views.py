from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action

from .models import RecipeLog
from .serializers import (
    RecipeLogCreateSerializer,
    RecipeLogListSerializer,
    RecipeLogDetailSerializer
)

# ===============================================================
# 1. 페이지 렌더링 View (HTML 리턴)
# 프론트엔드에서 페이지 이동할 때 쓰이는 함수들입니다.
# 데이터는 JS(fetch)가 아래의 API ViewSet을 통해 가져옵니다.
# ===============================================================

def log_list_view(request):
    """일지 목록 페이지 (빈 껍데기 렌더링)"""
    return render(request, 'logs/log_list.html')

def log_create_view(request):
    """일지 작성 페이지 (빈 껍데기 렌더링)"""
    # URL 파라미터로 recipe_id가 넘어올 수 있음 (예: /logs/create/?recipe_id=10)
    return render(request, 'logs/log_create.html')

def log_detail_view(request, pk):
    """일지 상세 페이지 (빈 껍데기 렌더링)"""
    # 실제 데이터는 JS가 API(/logs/api/{pk}/)로 요청해서 채웁니다.
    # 단, 존재하지 않는 일지에 접근하면 404를 띄우기 위해 체크 정도는 해줍니다.
    get_object_or_404(RecipeLog, pk=pk)
    return render(request, 'logs/log_detail.html')


# ===============================================================
# 2. API ViewSet (JSON 데이터 처리)
# 실제 DB와 통신하며 CRUD를 수행하는 핵심 로직입니다.
# ===============================================================

class RecipeLogViewSet(viewsets.ModelViewSet):
    """
    일지(RecipeLog) CRUD 및 최근 일지 조회 API
    """
    permission_classes = [IsAuthenticated] # 로그인한 사람만 가능
    parser_classes = [MultiPartParser, FormParser] # 이미지 업로드 처리용

    def get_queryset(self):
        # 내 일지만, 최신순(조리일 -> 작성일)으로 정렬
        return RecipeLog.objects.filter(user=self.request.user).order_by('-cooked_at', '-created_at')

    def get_serializer_class(self):
        """상황에 따라 다른 포장지(Serializer) 사용"""
        if self.action == 'list' or self.action == 'recent':
            return RecipeLogListSerializer
        elif self.action == 'retrieve':
            return RecipeLogDetailSerializer
        # create, update, partial_update 일 때는 입력용 사용
        return RecipeLogCreateSerializer

    # [POST] /logs/api/ : 일지 작성
    def create(self, request, *args, **kwargs):
        # 1. 데이터 검증
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 2. 저장 (user는 현재 로그인한 사람으로 자동 설정)
        instance = serializer.save(user=self.request.user)
        
        # 3. (옵션) 이미지 합성 로직은 나중에 여기에 추가 (Pillow)
        # share_image_url = make_share_image(...) 
        
        # 4. 응답 (API 명세서 형식 준수)
        return Response({
            "id": instance.recipe_log_id,
            "message": "일지가 저장되었습니다.",
            "share_url": instance.shared_image.url if instance.shared_image else None
        }, status=status.HTTP_201_CREATED)

    # [GET] /logs/api/?year=2026&month=1 : 월별 필터링
    def list(self, request, *args, **kwargs):
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        
        queryset = self.get_queryset()
        
        # 연/월 필터링 적용
        if year and month:
            queryset = queryset.filter(cooked_at__year=year, cooked_at__month=month)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # [PATCH] /logs/api/{id}/ : 수정
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # 수정 후에는 상세 정보를 반환 (명세서 기준)
        response_serializer = RecipeLogDetailSerializer(instance)
        return Response(response_serializer.data)

    # [GET] /logs/api/recent/ : 홈 화면용 최신 5개
    @action(detail=False, methods=['get'])
    def recent(self, request):
        queryset = self.get_queryset()[:5]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)