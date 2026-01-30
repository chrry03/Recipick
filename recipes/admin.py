from django.contrib import admin
from .models import Recipe, RecipeIngredient, FavoriteRecipe

# 레시피 상세 페이지에서 재료를 바로 추가/수정할 수 있게 함 (Inline)
class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    # [중요] 식재료가 많으므로 드롭다운 대신 '검색'으로 입력 (IngredientMasterAdmin에 search_fields 필수)
    autocomplete_fields = ['ingredient'] 

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'title', 
        'source', 
        'difficulty', 
        'ready_minutes', 
        'is_active', 
        'total_ingredients', # 캐싱된 재료 수 확인
        'created_at'
    )
    list_filter = ('source', 'difficulty', 'is_active')
    search_fields = ('title', 'external_id') # 제목과 외부 ID로 검색
    
    # 레시피 들어가면 재료 목록도 같이 뜨도록 설정
    inlines = [RecipeIngredientInline] 
    
    # 수정 불가능하게 막고 싶은 필드 (자동 계산되는 캐싱 필드들)
    readonly_fields = ('total_ingredients', 'required_ingredients', 'created_at', 'updated_at')

@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'created_at')
    search_fields = ('user__nickname', 'recipe__title')