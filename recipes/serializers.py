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
            'created_at'
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

    class Meta:
        model = FavoriteRecipe
        fields = [
            'favorite_id',
            'recipe',
            'created_at'
        ]