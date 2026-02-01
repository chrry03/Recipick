from django.contrib import admin
from .models import Recipe, RecipeIngredient, FavoriteRecipe


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 0
    fields = ['ingredient', 'ingredient_name', 'is_optional']
    raw_id_fields = ['ingredient']


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = [
        'recipe_id', 'title', 'source', 'difficulty', 'ready_minutes',
        'total_ingredients', 'required_ingredients', 'is_active', 'created_at'
    ]
    list_filter = ['source', 'difficulty', 'is_active', 'created_at']
    search_fields = ['title', 'external_id']
    inlines = [RecipeIngredientInline]
    readonly_fields = ['recipe_id', 'external_id', 'created_at', 'updated_at', 'step_count']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('recipe_id', 'external_id', 'source', 'title', 'image_url')
        }),
        ('레시피 상세', {
            'fields': ('ready_minutes', 'difficulty', 'servings', 'step_count')
        }),
        ('재료 정보', {
            'fields': ('total_ingredients', 'required_ingredients')
        }),
        ('상태', {
            'fields': ('is_active',)
        }),
        ('시스템', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """저장 시 난이도 자동 계산"""
        if not obj.difficulty or obj.difficulty == 'NORMAL':
            obj.difficulty = obj.calculate_difficulty()
        super().save_model(request, obj, form, change)


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = [
        'recipe_ingredient_id', 'recipe', 'ingredient', 'ingredient_name', 'is_optional'
    ]
    list_filter = ['is_optional']
    search_fields = ['recipe__title', 'ingredient__name_ko', 'ingredient_name']
    raw_id_fields = ['recipe', 'ingredient']


@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ['favorite_id', 'user', 'recipe', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'recipe__title']
    raw_id_fields = ['user', 'recipe']
    date_hierarchy = 'created_at'