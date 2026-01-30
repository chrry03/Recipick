from django.contrib import admin
from .models import IngredientCategory, IngredientMaster, UserIngredient

@admin.register(IngredientCategory)
class IngredientCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'icon_url', 'category_id') # 아이콘 URL 확인 가능
    list_filter = ('parent',) # 대분류별 필터링 (부모가 없는 것들만 보거나 등등)
    search_fields = ('name',)
    ordering = ('parent', 'name') # 정렬 기준

@admin.register(IngredientMaster)
class IngredientMasterAdmin(admin.ModelAdmin):
    # 영문명(API용) 추가됨 -> 목록에서 확인 가능
    list_display = ('name_ko', 'name_en', 'category', 'ingredient_id')
    list_filter = ('category',)
    # [중요] 한글, 영문, 별칭(JSON) 모두 검색 가능하도록 설정
    search_fields = ('name_ko', 'name_en', 'aliases') 

@admin.register(UserIngredient)
class UserIngredientAdmin(admin.ModelAdmin):
    list_display = ('user', 'ingredient', 'expire_at', 'is_consumed', 'created_at')
    list_filter = ('is_consumed', 'user') # 소비 여부로 필터링
    search_fields = ('user__nickname', 'user__email', 'ingredient__name_ko')
    ordering = ('expire_at',) # 유통기한 임박한 순서대로 정렬 (NULL은 맨 뒤로)