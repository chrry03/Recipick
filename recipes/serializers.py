from rest_framework import serializers
from .models import Recipe, RecipeIngredient, FavoriteRecipe, DifficultyLevel


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """레시피 재료 시리얼라이저"""
    
    ingredient_name_ko = serializers.CharField(source='ingredient.name_ko', read_only=True)
    ingredient_name_en = serializers.CharField(source='ingredient.name_en', read_only=True)
    
    class Meta:
        model = RecipeIngredient
        fields = [
            'recipe_ingredient_id', 'ingredient', 'ingredient_name_ko',
            'ingredient_name_en', 'ingredient_name', 'is_optional'
        ]


class RecipeListSerializer(serializers.ModelSerializer):
    """레시피 목록용 시리얼라이저 (간략)"""
    
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    is_favorited = serializers.SerializerMethodField()
    
    # 추천 관련 필드 (동적으로 추가됨)
    recommendation_score = serializers.FloatField(read_only=True, required=False)
    recommendation_category = serializers.CharField(read_only=True, required=False)
    missing_ingredients_count = serializers.IntegerField(read_only=True, required=False)
    score_details = serializers.DictField(read_only=True, required=False)
    
    class Meta:
        model = Recipe
        fields = [
            'recipe_id', 'external_id', 'source', 'title', 'image_url',
            'ready_minutes', 'difficulty', 'difficulty_display', 'servings',
            'total_ingredients', 'required_ingredients', 'is_favorited',
            'recommendation_score', 'recommendation_category',
            'missing_ingredients_count', 'score_details'
        ]
    
    def get_is_favorited(self, obj):
        """찜 여부 확인"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return FavoriteRecipe.objects.filter(
                user=request.user,
                recipe=obj
            ).exists()
        return False


class RecipeDetailSerializer(serializers.ModelSerializer):
    """레시피 상세 시리얼라이저"""
    
    ingredients = RecipeIngredientSerializer(source='recipe_ingredients', many=True, read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    is_favorited = serializers.SerializerMethodField()
    steps = serializers.SerializerMethodField()
    
    # 추천 관련 필드
    recommendation_score = serializers.FloatField(read_only=True, required=False)
    score_details = serializers.DictField(read_only=True, required=False)
    ingredients_status = serializers.DictField(read_only=True, required=False)
    
    class Meta:
        model = Recipe
        fields = [
            'recipe_id', 'external_id', 'source', 'title', 'image_url',
            'ready_minutes', 'difficulty', 'difficulty_display', 'servings',
            'instructions', 'steps', 'ingredients', 'total_ingredients',
            'required_ingredients', 'is_favorited', 'is_active',
            'recommendation_score', 'score_details', 'ingredients_status',
            'created_at', 'updated_at'
        ]
    
    def get_ingredients(self, obj):
        """재료 목록"""
        return RecipeIngredientSerializer(obj.recipe_ingredients.all(), many=True).data
    
    def get_difficulty(self, obj):
        """난이도 반환"""
        return {
            'value': obj.difficulty,
            'label': obj.get_difficulty_display()
        }
    
    def get_is_favorited(self, obj):
        """찜 여부 확인"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return FavoriteRecipe.objects.filter(
                user=request.user,
                recipe=obj
            ).exists()
        return False
    
    def get_steps(self, obj):
        """조리 단계"""
        if not obj.instructions:
            return []
        return obj.instructions


class FavoriteRecipeSerializer(serializers.ModelSerializer):
    """찜한 레시피 시리얼라이저"""
    
    recipe = RecipeListSerializer(read_only=True)
    
    class Meta:
        model = FavoriteRecipe
        fields = ['favorite_id', 'recipe', 'created_at']
        read_only_fields = ['favorite_id', 'created_at']


class RecipeSearchSerializer(serializers.Serializer):
    """레시피 검색용 시리얼라이저 (파라미터 검증)"""
    
    keyword = serializers.CharField(required=False, allow_blank=True)
    ingredients = serializers.CharField(required=False, allow_blank=True)
    max_ready_time = serializers.IntegerField(required=False, min_value=1)
    difficulty = serializers.ChoiceField(
        choices=DifficultyLevel.choices,
        required=False
    )
    sort = serializers.ChoiceField(
        choices=['recommend', 'time', 'likes'],
        default='recommend'
    )
    min_score = serializers.FloatField(required=False, default=60.0, min_value=0, max_value=100)
    limit = serializers.IntegerField(required=False, default=10, min_value=1, max_value=100)