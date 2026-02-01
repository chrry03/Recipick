from django.contrib import admin
from .models import IngredientMaster, IngredientCategory, UserIngredient


@admin.register(IngredientCategory)
class IngredientCategoryAdmin(admin.ModelAdmin):
    list_display = ['category_id', 'name', 'parent', 'icon_url', 'is_parent']
    list_filter = ['parent']
    search_fields = ['name']
    ordering = ['category_id']


@admin.register(IngredientMaster)
class IngredientMasterAdmin(admin.ModelAdmin):
    list_display = ['ingredient_id', 'name_ko', 'name_en', 'category', 'created_at']
    list_filter = ['category']
    search_fields = ['name_ko', 'name_en', 'aliases']
    ordering = ['name_ko']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')


@admin.register(UserIngredient)
class UserIngredientAdmin(admin.ModelAdmin):
    list_display = [
        'user_ingredient_id', 'user', 'get_ingredient_name', 
        'expire_at', 'days_until_expiry', 'is_consumed', 'created_at'
    ]
    list_filter = ['is_consumed', 'created_at']
    search_fields = ['user__username', 'ingredient__name_ko']
    date_hierarchy = 'created_at'
    
    def get_ingredient_name(self, obj):
        return obj.ingredient.name_ko
    get_ingredient_name.short_description = '식재료명'
    
    def days_until_expiry(self, obj):
        days = obj.days_until_expiry
        if days is None:
            return '-'
        if days < 0:
            return f'만료 ({days}일)'
        return f'{days}일'
    days_until_expiry.short_description = '유통기한'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'ingredient')