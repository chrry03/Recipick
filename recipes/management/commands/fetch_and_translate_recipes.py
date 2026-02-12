"""
Spoonacular API 레시피 수집 + 한글 번역

사용법:
    # 기본 (한글 번역 포함)
    python manage.py fetch_and_translate_recipes --cuisine korean --limit 50
    
    # 번역 제외
    python manage.py fetch_and_translate_recipes --cuisine italian --limit 30 --no-translate
    
    # 검색어로 수집
    python manage.py fetch_and_translate_recipes --query "chicken pasta" --limit 20
"""

# recipes/management/commands/fetch_and_translate_recipes.py
from django.core.management.base import BaseCommand
from recipes.services.spoonacular import SpoonacularService


class Command(BaseCommand):
    help = 'Spoonacular 레시피 수집 + 한글 번역'

    def add_arguments(self, parser):
        parser.add_argument('--cuisine', type=str)
        parser.add_argument('--query', type=str)
        parser.add_argument('--limit', type=int, default=50)
        parser.add_argument('--delay', type=float, default=0.5)
        parser.add_argument('--no-translate', action='store_true')

    def handle(self, *args, **options):
        cuisine = options.get('cuisine')
        query = options.get('query')
        limit = options['limit']
        delay = options['delay']
        translate = not options['no_translate']

        if not cuisine and not query:
            self.stdout.write(self.style.ERROR(
                '❌ --cuisine 또는 --query 중 하나는 필수입니다.'
            ))
            return

        service = SpoonacularService()

        # ⚠️ query 기반 수집은 아직 서비스에 없으므로 cuisine 우선
        if query:
            self.stdout.write(self.style.WARNING(
                '⚠️ query 기반 수집은 아직 지원되지 않습니다. cuisine 기준으로 수집합니다.'
            ))

        collected, skipped, errors = service.fetch_and_save_recipes(
            cuisine=cuisine or 'korean',
            limit=limit,
            translate=translate,
            delay=delay
        )

        self.stdout.write(self.style.SUCCESS(
            f'\n✨ 완료!'
            f'\n- 새로 추가: {collected}개'
            f'\n- 중복 건너뜀: {skipped}개'
            f'\n- 오류: {errors}개'
        ))
