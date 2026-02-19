from django.contrib import admin
from .models import IngredientCategory, IngredientMaster, UserIngredient, IngredientNameMapping


@admin.register(IngredientCategory)
class IngredientCategoryAdmin(admin.ModelAdmin):
    list_display = ['category_id', 'name', 'parent', 'icon_url']
    search_fields = ['name']
    list_filter = ['parent']


@admin.register(IngredientMaster)
class IngredientMasterAdmin(admin.ModelAdmin):
    list_display = ['ingredient_id', 'name_ko', 'name_en', 'category', 'created_at']
    search_fields = ['name_ko', 'name_en']
    list_filter = ['category']
    autocomplete_fields = ['category']


@admin.register(IngredientNameMapping)
class IngredientNameMappingAdmin(admin.ModelAdmin):
    """식재료 이름 매핑 관리 (신규)"""
    list_display = ['alternative_name', 'ingredient', 'source', 'confidence', 'created_at']
    search_fields = ['alternative_name', 'ingredient__name_ko']
    list_filter = ['source', 'confidence']
    autocomplete_fields = ['ingredient']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('ingredient', 'alternative_name')
        }),
        ('메타 정보', {
            'fields': ('source', 'confidence')
        }),
    )


@admin.register(UserIngredient)
class UserIngredientAdmin(admin.ModelAdmin):
    list_display = ['user_ingredient_id', 'user', 'ingredient', 'expire_at', 'is_consumed', 'created_at']
    search_fields = ['user__nickname', 'ingredient__name_ko']
    list_filter = ['is_consumed', 'expire_at']
    date_hierarchy = 'expire_at'