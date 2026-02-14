from rest_framework import serializers
from .models import RecipeLog
from recipes.models import Recipe

# ===============================================================
# 1. [공통] 레시피 정보 요약용 (상세 조회 시 포함될 데이터)
# ===============================================================
class SimpleRecipeSerializer(serializers.ModelSerializer):
    # ========== [수정] 한글 제목 우선 표시 ==========
    display_title = serializers.SerializerMethodField()
    
    class Meta:
        model = Recipe
        fields = ['recipe_id', 'title', 'title_ko', 'display_title', 'image_url']
    
    def get_display_title(self, obj):
        """한글 제목 우선, 없으면 영문"""
        return obj.get_display_title()


# ===============================================================
# 2. [입력] 일지 생성/수정용 (Create/Update)
# ===============================================================
class RecipeLogCreateSerializer(serializers.ModelSerializer):
    # API 명세서에는 'difficulty'로 되어 있지만, 모델은 'perceived_difficulty'입니다.
    # 이름을 맞춰주기 위해 source 옵션을 사용합니다.
    difficulty = serializers.ChoiceField(
        choices=RecipeLog.PerceivedDifficulty.choices,
        source='perceived_difficulty'
    )
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = RecipeLog
        # 사용자가 입력하는 필드만 정의
        fields = ['recipe', 'cooked_at', 'rating', 'difficulty', 'memo', 'image']
    
    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("평점은 1~5 사이의 정수여야 합니다.")
        return value

    def update(self, instance, validated_data):
        # 수정 시 image가 넘어오지 않았거나 비어 있으면 기존 이미지 유지
        if 'image' in validated_data and validated_data['image'] is None:
            validated_data.pop('image')
        return super().update(instance, validated_data)


# ===============================================================
# 3. [조회] 월별 목록 조회용 (List)
# ===============================================================
class RecipeLogListSerializer(serializers.ModelSerializer):
    # 명세서: "id", "recipe_title", "cooked_at", "rating", "image"
    
    id = serializers.IntegerField(source='recipe_log_id', read_only=True)
    
    # ========== [수정] 한글 제목 우선 표시 ==========
    recipe_title = serializers.SerializerMethodField()
    
    class Meta:
        model = RecipeLog
        fields = ['id', 'recipe_title', 'cooked_at', 'rating', 'image']
    
    def get_recipe_title(self, obj):
        """한글 제목 우선, 없으면 영문"""
        if obj.recipe:
            return obj.recipe.get_display_title()
        return "알 수 없는 레시피"


# ===============================================================
# 4. [조회] 일지 상세 조회용 (Detail)
# ===============================================================
class RecipeLogDetailSerializer(serializers.ModelSerializer):
    # 명세서: "id", "cooked_at", "rating", "difficulty", "memo", "image", "share_image", "recipe"
    
    id = serializers.IntegerField(source='recipe_log_id', read_only=True)
    
    # 1. 레시피 정보를 중첩해서 보여줌
    recipe = SimpleRecipeSerializer(read_only=True)
    
    # 2. 필드명 매핑 (모델 -> API 명세서 이름)
    difficulty = serializers.CharField(source='perceived_difficulty')
    share_image = serializers.ImageField(source='shared_image')

    class Meta:
        model = RecipeLog
        fields = [
            'id', 
            'cooked_at', 
            'rating', 
            'difficulty', 
            'memo', 
            'image', 
            'share_image', 
            'recipe'
        ]