"""
Recipes Serializers (한글 필드 포함)

주요 수정사항:
1. title_ko, instructions_ko 필드 추가
2. display_title, display_instructions 메서드 추가
3. 한글 우선 반환
4. total_ingredients_count를 SerializerMethodField로 변경 (500 에러 해결)
"""
from rest_framework import serializers
from recipes.models import Recipe, RecipeIngredient, FavoriteRecipe
from ingredients.serializers import IngredientSerializer


class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer(read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = [
            'recipe_ingredient_id',
            'ingredient',
            'ingredient_name',
            'is_optional'
        ]


class RecipeListSerializer(serializers.ModelSerializer):
    display_title = serializers.SerializerMethodField()
    difficulty_display = serializers.CharField(
        source='get_difficulty_display',
        read_only=True
    )
    # ========== [수정] SerializerMethodField로 변경 (500 에러 해결) ==========
    total_ingredients_count = serializers.SerializerMethodField()

    # [🔥 추가] 찜 여부 필드 (기본값 False)
    is_favorited = serializers.BooleanField(default=False, read_only=True)

    class Meta:
        model = Recipe
        fields = [
            'recipe_id',
            'external_id',
            'source',
            'title',
            'title_ko',
            'display_title',
            'is_translated',
            'image_url',
            'ready_minutes',
            'difficulty',
            'difficulty_display',
            'servings',
            'total_ingredients_count',
            'created_at',
            'is_favorited',  # [🔥 추가]
        ]

    def get_display_title(self, obj):
        return obj.get_display_title()
    
    # ========== [추가] total_ingredients_count getter ==========
    def get_total_ingredients_count(self, obj):
        """레시피의 총 재료 개수 반환"""
        return obj.recipe_ingredients.count()


class RecipeDetailSerializer(serializers.ModelSerializer):
    display_title = serializers.SerializerMethodField()
    display_steps = serializers.SerializerMethodField()

    recipe_ingredients = RecipeIngredientSerializer(
        many=True,
        read_only=True
    )
    difficulty_display = serializers.CharField(
        source='get_difficulty_display',
        read_only=True
    )
    # ========== [수정] SerializerMethodField로 변경 ==========
    total_ingredients_count = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'recipe_id',
            'external_id',
            'source',
            'title',
            'title_ko',
            'display_title',
            'instructions',        # 원본 JSON
            'display_steps',       # 한글 우선
            'is_translated',
            'image_url',
            'ready_minutes',
            'difficulty',
            'difficulty_display',
            'servings',
            'recipe_ingredients',
            'total_ingredients_count',
            'created_at',
            'updated_at'
        ]

    def get_display_title(self, obj):
        return obj.get_display_title()

    def get_display_steps(self, obj):
        return obj.get_display_steps()
    
    # ========== [추가] total_ingredients_count getter ==========
    def get_total_ingredients_count(self, obj):
        """레시피의 총 재료 개수 반환"""
        return obj.recipe_ingredients.count()


class FavoriteRecipeSerializer(serializers.ModelSerializer):
    recipe = RecipeListSerializer(read_only=True)
    # ========== [추가] 재료 상태 정보 ==========
    ingredients_status = serializers.SerializerMethodField()

    class Meta:
        model = FavoriteRecipe
        fields = [
            'favorite_id',
            'recipe',
            'created_at',
            'ingredients_status'  # 추가
        ]
    
    def get_ingredients_status(self, obj):
        """
        사용자의 보유 재료를 기반으로 레시피 재료 상태 계산
        """
        from ingredients.models import UserIngredient
        
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        # 사용자의 보유 재료
        user_ingredients = UserIngredient.objects.filter(
            user=request.user,
            is_consumed=False
        ).select_related('ingredient')
        
        user_ingredient_ids = set(user_ingredients.values_list('ingredient_id', flat=True))
        
        # 레시피 재료
        recipe_ingredients = obj.recipe.recipe_ingredients.select_related('ingredient')
        
        status_map = {}
        for ri in recipe_ingredients:
            if ri.ingredient:
                name = ri.ingredient.name_ko or ri.ingredient.name_en or ri.ingredient_name or '알 수 없는 재료'
                status_map[name] = {
                    'is_owned': ri.ingredient_id in user_ingredient_ids,
                    'is_optional': ri.is_optional
                }
        
        return {
            'ingredients_status': status_map
        }