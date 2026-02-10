from rest_framework import serializers
from .models import IngredientMaster, IngredientCategory, UserIngredient
from datetime import date

class IngredientCategorySerializer(serializers.ModelSerializer):
    """식재료 카테고리 시리얼라이저"""
    
    subcategories = serializers.SerializerMethodField()
    # 모델의 프로퍼티 이름인 display_icon을 사용
    icon = serializers.CharField(source='display_icon', read_only=True)
    
    class Meta:
        model = IngredientCategory
        fields = [
            'category_id', 'name', 'parent', 'icon', 
            'is_parent', 'full_path', 'subcategories'
        ]
    
    def get_subcategories(self, obj):
        if obj.subcategories.exists():
            return IngredientCategorySerializer(obj.subcategories.all(), many=True).data
        return []


class IngredientSerializer(serializers.ModelSerializer):
    """식재료 마스터 시리얼라이저 (수정됨)"""
    
    # [핵심 수정 1] 프론트엔드가 'id'를 찾으므로 ingredient_id를 'id'로 내보냅니다.
    id = serializers.IntegerField(source='ingredient_id', read_only=True)
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    # [핵심 수정 2] 모델에 icon_url 필드는 없고, icon 프로퍼티가 있습니다. source를 'icon'으로 변경!
    icon = serializers.CharField(source='icon', read_only=True)
    
    all_names = serializers.SerializerMethodField()
    
    class Meta:
        model = IngredientMaster
        fields = [
            'id', # [수정] id 필드 추가
            'ingredient_id', 'name_ko', 'name_en', 'category', 
            'category_name', 'aliases', 'icon', 'all_names'
        ]
    
    def get_all_names(self, obj):
        return obj.get_all_names()


class UserIngredientSerializer(serializers.ModelSerializer):
    """사용자 식재료 시리얼라이저"""
    
    ingredient_name = serializers.CharField(source='ingredient.name_ko', read_only=True)
    category_name = serializers.CharField(source='ingredient.category.name', read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    expiry_status = serializers.CharField(source='get_expiry_status', read_only=True)
    icon = serializers.CharField(source='ingredient.icon', read_only=True)
    urgency_score = serializers.IntegerField(source='get_urgency_score', read_only=True)
    
    class Meta:
        model = UserIngredient
        fields = [
            'user_ingredient_id', 'ingredient', 'ingredient_name', 
            'category_name', 'icon', 'expire_at', 'days_until_expiry', 
            'expiry_status', 'urgency_score', 'is_consumed', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user_ingredient_id', 'created_at', 'updated_at']


class UserIngredientCreateSerializer(serializers.ModelSerializer):
    """사용자 식재료 생성용 시리얼라이저"""
    
    class Meta:
        model = UserIngredient
        fields = ['ingredient', 'expire_at']
    
    def validate_ingredient(self, value):
        """식재료 존재 여부 확인"""
        if not IngredientMaster.objects.filter(ingredient_id=value.ingredient_id).exists():
            raise serializers.ValidationError("존재하지 않는 식재료입니다.")
        return value
    
    def create(self, validated_data):
        """사용자 정보를 자동으로 추가"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class UserIngredientUpdateSerializer(serializers.ModelSerializer):
    """사용자 식재료 수정용 시리얼라이저"""
    
    class Meta:
        model = UserIngredient
        fields = ['expire_at']


class UserIngredientConsumeSerializer(serializers.Serializer):
    """식재료 소비 처리용 시리얼라이저"""
    
    is_consumed = serializers.BooleanField(default=True)
    
    def update(self, instance, validated_data):
        """소비 상태 업데이트"""
        instance.is_consumed = validated_data.get('is_consumed', True)
        instance.save()
        return instance