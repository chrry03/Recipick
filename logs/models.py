from django.db import models
from django.conf import settings # AUTH_USER_MODEL 참조용
from recipes.models import Recipe # recipes/models.py의 레시피 모델을 직접 가져옴

class RecipeLog(models.Model):
    """
    10. 요리 일지
    - 사용자가 특정 레시피를 요리하고 남기는 기록
    """
    class PerceivedDifficulty(models.TextChoices): # 체감 난이도
        EASY = 'EASY', '쉬움'
        NORMAL = 'NORMAL', '보통'
        DIFFICULT = 'DIFFICULT', '어려움'

    recipe_log_id = models.BigAutoField(primary_key=True)
    
    # settings.AUTH_USER_MODEL을 쓰는 것이 Django 권장 사항: 그냥 User를 import 해서 쓰지 않고, 설정 파일(settings.py)을 바라보게
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='logs')
    # related_name='logs': 유저 입장에서 내 일지를 찾을 때: user.logs.all() 이라고 직관적으로 호출할 수 있게 해줌
    
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='logs')
    
    cooked_at = models.DateField() # 조리일자
    rating = models.IntegerField() # 1~5 별점(만족도)
    perceived_difficulty = models.CharField(max_length=20, choices=PerceivedDifficulty.choices) # 체감난이도
    memo = models.TextField(null=True, blank=True) # 사용자 작성 메모(글)
    
    # 왜 ImageField가 정답인가요? (추천)
    # Django의 ImageField는 **"중개인"**입니다. 개발자는 그냥 "파일 저장해!"라고만 하면, 설정 파일(settings.py)에 따라 알아서 저장소를 바꿔줍니다.
    # - DB에 저장되는 것: ImageField를 써도 DB 내부에는 **파일 경로(문자열)**가 저장됩니다. (예: logs/2026/01/28/pizza.jpg)
    # - 로컬 개발 시 (settings.py가 기본일 때): 자동으로 컴퓨터의 media 폴더에 파일을 저장합니다.
    # - AWS 배포 시 (django-storages 라이브러리 설치 후): models.py 코드는 단 한 줄도 수정 안 해도, 자동으로 AWS S3로 날아가서 저장됩니다.
    
    # 1. 사용자가 직접 찍은 요리 사진
    # 저장 위치 예시: media/recipe_logs/original/2026/01/28/pizza.jpg
    image = models.ImageField(
        upload_to='recipe_logs/original/%Y/%m/%d/', 
        null=True, 
        blank=True
    )
    # 2. 공유용으로 생성된 템플릿 이미지 (9:16 비율)
    # 저장 위치 예시: media/recipe_logs/shared/2026/01/28/pizza_story.jpg
    shared_image = models.ImageField(
        upload_to='recipe_logs/shared/%Y/%m/%d/', 
        null=True, 
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'RecipeLog' # DB 테이블명 지정
        # ordering 옵션 없음 -> 기본적으로 PK순(입력한 순서)대로 나옴: 최신꺼가 마지막으로

    def __str__(self):
        # 관리자 페이지에서 "김철수님의 김치찌개 일지" 처럼 보이게 설정
        return f"{self.user}님의 {self.recipe.title} 일지 ({self.cooked_at})"