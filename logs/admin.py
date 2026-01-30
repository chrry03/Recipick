from django.contrib import admin
from .models import RecipeLog

@admin.register(RecipeLog)
class RecipeLogAdmin(admin.ModelAdmin):
    list_display = (
        'recipe_log_id', 
        'user_info',      # 아래 정의한 함수 사용 (가독성 UP)
        'recipe_title',   # 아래 정의한 함수 사용 (가독성 UP)
        'cooked_at', 
        'rating', 
        'perceived_difficulty'
    )
    
    list_filter = ('cooked_at', 'rating', 'perceived_difficulty')
    search_fields = ('user__nickname', 'user__email', 'recipe__title', 'memo')
    
    # 상단에 날짜 네비게이션 바 생성 (연도 -> 월 -> 일 순으로 탐색 가능)
    date_hierarchy = 'cooked_at'
    
    # FK 필드 커스텀 표시 (그냥 user라고 하면 객체가 나와서 안 예쁨)
    def user_info(self, obj):
        return f"{obj.user.nickname} ({obj.user.email})"
    user_info.short_description = '사용자'

    def recipe_title(self, obj):
        return obj.recipe.title
    recipe_title.short_description = '요리명'