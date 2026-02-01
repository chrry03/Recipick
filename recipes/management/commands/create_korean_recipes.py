"""
테스트용 한국 레시피를 수동으로 생성하는 관리 명령어
Spoonacular API 없이도 테스트 가능

사용법:
    python manage.py create_korean_recipes
"""

from django.core.management.base import BaseCommand
from recipes.models import Recipe, RecipeIngredient, RecipeSource
from ingredients.models import IngredientMaster


class Command(BaseCommand):
    help = '테스트용 한국 레시피를 생성합니다'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🍚 한국 레시피 생성 시작...')
        )

        recipes_data = [
            {
                'title': '김치볶음밥',
                'ready_minutes': 15,
                'servings': 2,
                'instructions': [
                    {"step": 1, "description": "프라이팬에 식용유를 두르고 중불로 달군다"},
                    {"step": 2, "description": "김치를 잘게 썰어 넣고 볶는다"},
                    {"step": 3, "description": "밥을 넣고 김치와 함께 볶는다"},
                    {"step": 4, "description": "간장으로 간을 맞추고 참기름을 두른다"},
                ],
                'ingredients': ['김치', '밥', '식용유', '간장'],
                'image_url': 'https://via.placeholder.com/400x300?text=Kimchi+Fried+Rice'
            },
            {
                'title': '계란말이',
                'ready_minutes': 10,
                'servings': 2,
                'instructions': [
                    {"step": 1, "description": "계란을 풀어 소금으로 간한다"},
                    {"step": 2, "description": "팬에 식용유를 두르고 계란물을 부어 익힌다"},
                    {"step": 3, "description": "반쯤 익으면 돌돌 말아준다"},
                    {"step": 4, "description": "먹기 좋은 크기로 썬다"},
                ],
                'ingredients': ['계란', '소금', '식용유'],
                'image_url': 'https://via.placeholder.com/400x300?text=Rolled+Omelette'
            },
            {
                'title': '된장찌개',
                'ready_minutes': 25,
                'servings': 3,
                'instructions': [
                    {"step": 1, "description": "물에 멸치와 다시마를 넣고 육수를 낸다"},
                    {"step": 2, "description": "된장을 풀고 두부를 넣는다"},
                    {"step": 3, "description": "애호박과 양파를 넣고 끓인다"},
                    {"step": 4, "description": "대파와 고추를 넣고 한소끔 끓인다"},
                ],
                'ingredients': ['두부', '애호박', '양파', '대파'],
                'image_url': 'https://via.placeholder.com/400x300?text=Doenjang+Jjigae'
            },
            {
                'title': '토마토 파스타',
                'ready_minutes': 30,
                'servings': 2,
                'instructions': [
                    {"step": 1, "description": "파스타면을 삶는다"},
                    {"step": 2, "description": "팬에 올리브유를 두르고 마늘을 볶는다"},
                    {"step": 3, "description": "토마토를 넣고 으깬다"},
                    {"step": 4, "description": "삶은 파스타를 넣고 소스와 버무린다"},
                ],
                'ingredients': ['파스타면', '토마토', '마늘', '식용유'],
                'image_url': 'https://via.placeholder.com/400x300?text=Tomato+Pasta'
            },
            {
                'title': '닭가슴살 샐러드',
                'ready_minutes': 20,
                'servings': 2,
                'instructions': [
                    {"step": 1, "description": "닭가슴살을 삶아 결대로 찢는다"},
                    {"step": 2, "description": "양파와 당근을 채썬다"},
                    {"step": 3, "description": "채소와 닭가슴살을 섞는다"},
                    {"step": 4, "description": "드레싱을 뿌려 완성한다"},
                ],
                'ingredients': ['닭가슴살', '양파', '당근'],
                'image_url': 'https://via.placeholder.com/400x300?text=Chicken+Salad'
            },
        ]

        created_count = 0
        
        for recipe_data in recipes_data:
            # 이미 존재하는지 확인
            if Recipe.objects.filter(title=recipe_data['title']).exists():
                self.stdout.write(
                    self.style.WARNING(f'   ⏭️  "{recipe_data["title"]}" 이미 존재 (건너뜀)')
                )
                continue

            # 레시피 생성
            recipe = Recipe.objects.create(
                external_id=None,
                source=RecipeSource.USER_CREATED,
                title=recipe_data['title'],
                image_url=recipe_data['image_url'],
                ready_minutes=recipe_data['ready_minutes'],
                servings=recipe_data['servings'],
                instructions=recipe_data['instructions'],
                is_active=True
            )
            
            # 난이도 자동 계산
            recipe.difficulty = recipe.calculate_difficulty()
            recipe.save()

            # 재료 추가
            for ingredient_name in recipe_data['ingredients']:
                try:
                    ingredient = IngredientMaster.objects.get(name_ko=ingredient_name)
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        ingredient=ingredient,
                        ingredient_name=ingredient_name,
                        is_optional=False
                    )
                except IngredientMaster.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'      ⚠️  "{ingredient_name}" 식재료를 찾을 수 없습니다')
                    )

            # 재료 개수 캐싱
            recipe.update_ingredient_counts()

            self.stdout.write(
                self.style.SUCCESS(f'   ✅ "{recipe.title}" 생성 완료 (재료 {recipe.total_ingredients}개)')
            )
            created_count += 1

        # 결과 요약
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(
            self.style.SUCCESS(f'🎉 한국 레시피 생성 완료!')
        )
        self.stdout.write(f'   생성: {created_count}개')
        self.stdout.write(
            self.style.SUCCESS(f'   총 DB 레시피 수: {Recipe.objects.count()}개')
        )
        self.stdout.write(self.style.SUCCESS('=' * 50))