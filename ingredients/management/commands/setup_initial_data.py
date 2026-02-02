"""
초기 데이터 세팅 통합 Command
1. 식재료 매핑 데이터 생성
2. 한식 레시피 로드
"""
from django.core.management.base import BaseCommand
from ingredients.utils.mapper import IngredientMapper


class Command(BaseCommand):
    help = '레시픽 초기 데이터를 세팅합니다 (식재료 매핑 + 한식 레시피)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-mappings',
            action='store_true',
            help='식재료 매핑 생성을 건너뜁니다'
        )
        parser.add_argument(
            '--skip-recipes',
            action='store_true',
            help='한식 레시피 로드를 건너뜁니다'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('레시픽 초기 데이터 세팅 시작'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        
        # 1. 식재료 매핑 생성
        if not options['skip_mappings']:
            self.stdout.write('1. 식재료 이름 매핑 데이터 생성 중...')
            try:
                count = IngredientMapper.bulk_create_base_mappings()
                self.stdout.write(self.style.SUCCESS(f'   ✓ {count}개의 매핑 생성 완료\n'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ✗ 매핑 생성 실패: {e}\n'))
        else:
            self.stdout.write(self.style.WARNING('1. 식재료 매핑 생성 건너뜀 (--skip-mappings)\n'))
        
        # 2. 한식 레시피 로드
        if not options['skip_recipes']:
            self.stdout.write('2. 한식 레시피 DB 로드 중...')
            try:
                from django.core.management import call_command
                call_command('load_korean_recipes', '--file=foodsafetykorea.json')
                self.stdout.write(self.style.SUCCESS('   ✓ 한식 레시피 로드 완료\n'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ✗ 레시피 로드 실패: {e}\n'))
                self.stdout.write(self.style.WARNING('   foodsafetykorea.json 파일이 프로젝트 루트에 있는지 확인하세요.\n'))
        else:
            self.stdout.write(self.style.WARNING('2. 한식 레시피 로드 건너뜀 (--skip-recipes)\n'))
        
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('초기 데이터 세팅 완료'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        
        self.stdout.write('\n다음 단계:')
        self.stdout.write('1. .env 파일에 SPOONACULAR_API_KEY 설정')
        self.stdout.write('2. python manage.py runserver로 서버 실행')
        self.stdout.write('3. 프론트엔드에서 /api/recipes/api/recommendations/ 호출\n')