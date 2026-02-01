"""
초기 레시피 데이터를 Spoonacular API에서 가져와 저장하는 관리 명령어

사용법:
    python manage.py load_initial_recipes
    python manage.py load_initial_recipes --count 50
    python manage.py load_initial_recipes --cuisine korean
"""

import time
import requests

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction

from recipes.models import Recipe
from ingredients.models import IngredientMaster


class Command(BaseCommand):
    help = 'Spoonacular API에서 초기 레시피 데이터를 가져옵니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=30,
            help='가져올 레시피 개수 (기본: 30)'
        )
        parser.add_argument(
            '--cuisine',
            type=str,
            default='',
            help='요리 종류 (예: korean, italian, chinese)'
        )

    def handle(self, *args, **options):
        count = options['count']
        cuisine = options['cuisine']

        # API 키 확인
        api_key = settings.SPOONACULAR_API_KEY
        if not api_key:
            self.stdout.write(
                self.style.ERROR('❌ SPOONACULAR_API_KEY가 설정되지 않았습니다!')
            )
            self.stdout.write(
                self.style.WARNING('   .env 파일에 SPOONACULAR_API_KEY를 추가해주세요.')
            )
            return

        self.stdout.write(self.style.SUCCESS('🔍 Spoonacular API에서 레시피 검색 중...'))
        self.stdout.write(f'   요청 개수: {count}개')
        if cuisine:
            self.stdout.write(f'   요리 종류: {cuisine}')

        # 식재료 매핑 생성
        self.stdout.write('📦 식재료 매핑 생성 중...')
        ingredient_mapping = IngredientMaster.create_ingredient_mapping_for_api()
        self.stdout.write(
            self.style.SUCCESS(f'   ✅ {len(ingredient_mapping)}개 식재료 매핑 완료')
        )

        # 레시피 ID 검색
        recipe_ids = self._search_recipes(api_key, count, cuisine)

        if not recipe_ids:
            self.stdout.write(self.style.WARNING('⚠️  검색된 레시피가 없습니다.'))
            return

        self.stdout.write(
            self.style.SUCCESS(f'✅ {len(recipe_ids)}개 레시피 ID 발견\n')
        )

        success_count = 0
        fail_count = 0
        failed_ids = []

        for idx, recipe_id in enumerate(recipe_ids, 1):
            self.stdout.write(f'[{idx}/{len(recipe_ids)}] 레시피 ID {recipe_id} 처리 중...')

            # 이미 저장된 레시피는 건너뜀
            if Recipe.objects.filter(
                external_id=str(recipe_id),
                source='spoonacular'
            ).exists():
                self.stdout.write(
                    self.style.WARNING('   ⏭️  이미 존재하는 레시피 (건너뜀)')
                )
                continue

            try:
                with transaction.atomic():
                    recipe = Recipe.fetch_and_save_from_spoonacular(
                        recipe_id=recipe_id,
                        api_key=api_key,
                        ingredient_mapping=ingredient_mapping
                    )

                if recipe:
                    self.stdout.write(
                        self.style.SUCCESS(f'   ✅ "{recipe.title}" 저장 완료')
                    )
                    success_count += 1
                else:
                    raise ValueError('레시피 저장 실패')

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ 실패: {e}')
                )
                fail_count += 1
                failed_ids.append(recipe_id)

            # API Rate Limit 방지
            if idx < len(recipe_ids):
                time.sleep(1)

        # 결과 요약
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('🎉 초기 레시피 로드 완료!'))
        self.stdout.write(f'   성공: {success_count}개')

        if fail_count > 0:
            self.stdout.write(
                self.style.WARNING(f'   실패: {fail_count}개')
            )
            self.stdout.write(
                self.style.WARNING(f'   실패한 recipe_ids: {failed_ids}')
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'   전체 DB 레시피 수: {Recipe.objects.count()}개'
            )
        )
        self.stdout.write(self.style.SUCCESS('=' * 50))

    # ---------------------------------------------------------
    # 내부 헬퍼 메서드
    # ---------------------------------------------------------

    def _search_recipes(self, api_key, count, cuisine):
        """
        Spoonacular API로 레시피 ID 검색 (pagination 지원)
        """
        url = "https://api.spoonacular.com/recipes/complexSearch"

        recipe_ids = []
        offset = 0
        page_size = 100

        while len(recipe_ids) < count:
            params = {
                'apiKey': api_key,
                'number': min(page_size, count - len(recipe_ids)),
                'offset': offset,
                'instructionsRequired': True,
                'sort': 'popularity',
            }

            if cuisine:
                params['cuisine'] = cuisine

            response = self._safe_request(url, params)
            if not response:
                break

            data = response.json()
            results = data.get('results', [])

            if not results:
                break

            recipe_ids.extend([r['id'] for r in results])
            offset += len(results)

            time.sleep(1)  # rate limit 보호

        return recipe_ids

    def _safe_request(self, url, params, retries=3):
        """
        Spoonacular API 안전 요청 (429 / 네트워크 오류 대응)
        """
        for attempt in range(retries):
            try:
                response = requests.get(url, params=params, timeout=10)

                if response.status_code == 429:
                    self.stdout.write(
                        self.style.WARNING('⚠️  Rate limit 도달, 5초 대기...')
                    )
                    time.sleep(5)
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  API 요청 실패 (재시도 {attempt + 1}/{retries}): {e}')
                )
                time.sleep(2)

        self.stdout.write(
            self.style.ERROR('❌ API 요청 최종 실패')
        )
        return None