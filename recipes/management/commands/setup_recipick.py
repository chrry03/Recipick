"""
통합 초기화 스크립트

실행 순서:
1. fixtures 데이터 로드 (카테고리, 식재료)
2. 식재료 매핑 생성
3. 한식 레시피 로드
4. Spoonacular 테스트 (선택)

사용법:
python manage.py setup_recipick [--skip-mappings] [--skip-recipes] [--test-spoonacular]
"""

import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command
from django.core.management.base import BaseCommand
from ingredients.utils.mapper import IngredientMapper
from ingredients.models import IngredientMaster, IngredientCategory, UserIngredient
from recipes.models import Recipe
from users.models import User


class Command(BaseCommand):
    help = '레시픽 프로젝트 초기 데이터를 세팅합니다'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-fixtures',
            action='store_true',
            help='fixtures 로드를 건너뜁니다'
        )
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
        parser.add_argument(
            '--test-spoonacular',
            action='store_true',
            help='Spoonacular API 테스트를 실행합니다'
        )
        parser.add_argument(
            '--create-test-user',
            action='store_true',
            help='테스트 사용자 및 데이터를 생성합니다'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('레시픽 프로젝트 초기 데이터 세팅 시작'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
        
        # 1. Fixtures 로드
        if not options['skip_fixtures']:
            self.load_fixtures()
        else:
            self.stdout.write(self.style.WARNING('1. Fixtures 로드 건너뜀 (--skip-fixtures)\n'))
        
        # 2. 식재료 매핑 생성
        if not options['skip_mappings']:
            self.create_mappings()
        else:
            self.stdout.write(self.style.WARNING('2. 식재료 매핑 생성 건너뜀 (--skip-mappings)\n'))
        
        # 3. 한식 레시피 로드
        if not options['skip_recipes']:
            self.load_korean_recipes()
            # ========== [추가] 하드코딩 레시피 로드 ==========
            self.load_hardcoded_recipes()
        else:
            self.stdout.write(self.style.WARNING('3. 한식 레시피 로드 건너뜀 (--skip-recipes)\n'))
        
        # 4. Spoonacular 테스트
        if options['test_spoonacular']:
            self.test_spoonacular()
        
        # 5. 테스트 사용자 생성
        if options['create_test_user']:
            self.create_test_user()
        
        # 최종 통계
        self.print_statistics()
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('초기 데이터 세팅 완료!'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
        
        self.print_next_steps()
    
    def load_fixtures(self):
        """Fixtures 데이터 로드"""
        self.stdout.write('\n📦 1. Fixtures 데이터 로드 중...')
        
        fixtures = [
            ('fixtures/categories.json', '식재료 카테고리'),
            ('fixtures/ingredients.json', '식재료 마스터 데이터')
        ]
        
        for fixture_file, description in fixtures:
            if os.path.exists(fixture_file):
                try:
                    call_command('loaddata', fixture_file, verbosity=0)
                    self.stdout.write(self.style.SUCCESS(f'   ✓ {description} 로드 완료'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   ✗ {description} 로드 실패: {e}'))
            else:
                self.stdout.write(self.style.WARNING(f'   ⚠ {fixture_file} 파일을 찾을 수 없습니다'))
        
        self.stdout.write('')
    
    def create_mappings(self):
        """식재료 매핑 생성"""
        self.stdout.write('🔗 2. 식재료 이름 매핑 데이터 생성 중...')
        
        try:
            count = IngredientMapper.bulk_create_base_mappings()
            self.stdout.write(self.style.SUCCESS(f'   ✓ {count}개의 매핑 생성 완료\n'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ 매핑 생성 실패: {e}\n'))
    
    def load_korean_recipes(self):
        """한식 레시피 로드"""
        self.stdout.write('🍚 3. 한식 레시피 DB 로드 중...')
        
        json_file = 'foodsafetykorea.json'
        
        if not os.path.exists(json_file):
            self.stdout.write(self.style.WARNING(
                f'   ⚠ {json_file} 파일을 찾을 수 없습니다\n'
                '   프로젝트 루트에 foodsafetykorea.json 파일을 배치하세요.\n'
            ))
            return
        
        try:
            call_command('load_korean_recipes', f'--file={json_file}', verbosity=1)
            self.stdout.write(self.style.SUCCESS('   ✓ 한식 레시피 로드 완료\n'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ 한식 레시피 로드 실패: {e}\n'))
    
    def load_hardcoded_recipes(self):
        """하드코딩 레시피 로드"""
        self.stdout.write('📝 3-1. 하드코딩 레시피 로드 중...')
        
        import json
        from recipes.models import Recipe, RecipeIngredient
        
        json_file = 'hardcoded_recipes.json'
        
        if not os.path.exists(json_file):
            self.stdout.write(self.style.WARNING(
                f'   ⚠ {json_file} 파일을 찾을 수 없습니다\n'
                '   프로젝트 루트에 hardcoded_recipes.json 파일을 배치하세요.\n'
            ))
            return
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            recipes_data = data.get('recipes', [])
            created_count = 0
            updated_count = 0
            
            for recipe_data in recipes_data:
                external_id = recipe_data.get('external_id')
                
                # 레시피 생성 또는 업데이트
                recipe, created = Recipe.objects.update_or_create(
                    external_id=external_id,
                    defaults={
                        'source': recipe_data.get('source', 'HARDCODED'),
                        'title': recipe_data.get('title', ''),
                        'title_ko': recipe_data.get('title_ko', ''),
                        'difficulty': recipe_data.get('difficulty', 'NORMAL'),
                        'ready_minutes': recipe_data.get('ready_minutes', 30),
                        'servings': recipe_data.get('servings', 2),
                        'image_url': recipe_data.get('image_url', ''),
                        'instructions': recipe_data.get('instructions', []),  # instructions_ko → instructions
                        'is_translated': True  # 이미 한글임
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                
                # 기존 재료 삭제
                RecipeIngredient.objects.filter(recipe=recipe).delete()
                
                # 재료 추가
                for idx, ing_data in enumerate(recipe_data.get('ingredients', [])):
                    # 식재료 마스터에서 찾기
                    ingredient = None
                    name_ko = ing_data.get('name_ko', '')
                    name_en = ing_data.get('name_en', '')
                    
                    if name_ko:
                        ingredient = IngredientMaster.objects.filter(
                            name_ko__icontains=name_ko
                        ).first()
                    
                    if not ingredient and name_en:
                        ingredient = IngredientMaster.objects.filter(
                            name_en__icontains=name_en
                        ).first()
                    
                    # ========== [수정] 식재료가 없으면 자동 생성 → HARDCODED 카테고리로 ==========
                    if not ingredient and (name_ko or name_en):
                        # HARDCODED 카테고리 찾기 (pk=19)
                        hardcoded_category = IngredientCategory.objects.filter(
                            name='HARDCODED'
                        ).first()
                        
                        if not hardcoded_category:
                            # HARDCODED 카테고리가 없으면 생성 (fixtures 로드 안된 경우)
                            hardcoded_category, _ = IngredientCategory.objects.get_or_create(
                                name='HARDCODED',
                                defaults={
                                    'name': 'HARDCODED',
                                    'icon_url': '/static/images/categories/hardcoded.png'
                                }
                            )
                        
                        # 식재료 생성
                        ingredient = IngredientMaster.objects.create(
                            name_ko=name_ko or name_en,
                            name_en=name_en or name_ko,
                            category=hardcoded_category
                        )
                        self.stdout.write(
                            f'      ✓ 식재료 자동 생성 (HARDCODED): {name_ko or name_en}'
                        )
                    
                    # RecipeIngredient 생성
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        ingredient=ingredient,  # 이제 항상 있음
                        ingredient_name=name_ko or name_en,
                        is_optional=ing_data.get('is_optional', False)
                    )
                
                self.stdout.write(
                    f'   {"✓ 생성" if created else "✓ 업데이트"}: {recipe.title_ko}'
                )
            
            self.stdout.write(self.style.SUCCESS(
                f'   ✓ 하드코딩 레시피 로드 완료 (생성: {created_count}, 업데이트: {updated_count})\n'
            ))
        
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'   ✗ {json_file} 파일을 찾을 수 없습니다\n'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'   ✗ JSON 파싱 오류: {e}\n'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ 하드코딩 레시피 로드 실패: {e}\n'))
    
    def test_spoonacular(self):
        """Spoonacular API 테스트"""
        self.stdout.write('\n🌐 4. Spoonacular API 테스트 중...')
        
        try:
            from recipes.services.spoonacular import SpoonacularService
            service = SpoonacularService()
            
            # 간단한 검색 테스트
            results = service.search_recipes_by_ingredients(
                ingredients=['chicken', 'tomato'],
                number=3
            )
            
            if results:
                self.stdout.write(self.style.SUCCESS(
                    f'   ✓ API 정상 작동 ({len(results)}개 레시피 검색)\n'
                ))
                for recipe in results:
                    self.stdout.write(f'     - {recipe.get("title", "Unknown")}')
            else:
                self.stdout.write(self.style.WARNING('   ⚠ 검색 결과 없음\n'))
        
        except ValueError as e:
            self.stdout.write(self.style.ERROR(
                f'   ✗ API 키 오류: {e}\n'
                '   .env 파일에 SPOONACULAR_API_KEY를 설정하세요.\n'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ API 테스트 실패: {e}\n'))
    
    def create_test_user(self):
        """테스트 사용자 및 데이터 생성"""
        self.stdout.write('\n👤 5. 테스트 사용자 생성 중...')
        
        from users.models import UserProfile
        from datetime import date, timedelta
        
        # 사용자 생성
        try:
            user, created = User.objects.get_or_create(
                email='test@recipick.com',
                defaults={
                    'nickname': '테스트유저',
                }
            )
            
            if created:
                user.set_password('test1234')
                user.save()
                self.stdout.write(self.style.SUCCESS('   ✓ 테스트 사용자 생성 (test@recipick.com / test1234)'))
            else:
                self.stdout.write(self.style.WARNING('   ⚠ 테스트 사용자 이미 존재'))
            
            # 프로필 생성
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'cooking_level': 'INTERMEDIATE',
                    'allergies': [],
                    'banned_ingredients': []
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS('   ✓ 사용자 프로필 생성'))
            
            # 식재료 추가
            test_ingredients = [
                ('양파', 3),
                ('대파', 5),
                ('마늘', 7),
                ('당근', 2),
                ('계란', 4),
            ]
            
            added_count = 0
            for ing_name, days_left in test_ingredients:
                ingredient = IngredientMaster.find_by_name(ing_name)
                if ingredient:
                    _, created = UserIngredient.objects.get_or_create(
                        user=user,
                        ingredient=ingredient,
                        defaults={
                            'expire_at': date.today() + timedelta(days=days_left),
                            'is_consumed': False
                        }
                    )
                    if created:
                        added_count += 1
            
            self.stdout.write(self.style.SUCCESS(f'   ✓ {added_count}개 식재료 추가\n'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ 테스트 사용자 생성 실패: {e}\n'))
    
    def print_statistics(self):
        """현재 데이터 통계 출력"""
        self.stdout.write('\n📊 데이터베이스 통계:')
        
        stats = [
            ('식재료 카테고리', IngredientCategory.objects.count()),
            ('식재료 마스터', IngredientMaster.objects.count()),
            ('레시피', Recipe.objects.count()),
            ('사용자', User.objects.count()),
        ]
        
        for name, count in stats:
            self.stdout.write(f'   - {name}: {count}개')
        
        self.stdout.write('')
    
    def print_next_steps(self):
        """다음 단계 안내"""
        self.stdout.write('📝 다음 단계:')
        self.stdout.write('   1. .env 파일에 SPOONACULAR_API_KEY 설정 (선택)')
        self.stdout.write('   2. python manage.py runserver로 서버 실행')
        self.stdout.write('   3. 브라우저에서 http://localhost:8000 접속')
        
        if User.objects.filter(email='test@recipick.com').exists():
            self.stdout.write('   4. 테스트 계정 로그인 (test@recipick.com / test1234)')
        
        self.stdout.write('')


if __name__ == '__main__':
    # 스크립트로 직접 실행하는 경우
    command = Command()
    command.handle()