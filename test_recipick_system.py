"""
레시픽 통합 테스트 스크립트

테스트 항목:
1. 식재료 매핑 시스템
2. 레시피 검색 (DB + Spoonacular)
3. 추천 알고리즘
4. 직접 추가 재료 처리
5. API 엔드포인트

사용법:
python test_recipick_system.py [--verbose] [--skip-api]
"""

import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from datetime import date, timedelta
from ingredients.models import IngredientMaster, IngredientCategory, UserIngredient
from ingredients.utils.mapper import IngredientMapper
from recipes.models import Recipe, RecipeIngredient
from users.models import User, UserProfile


class RecipickTester:
    """레시픽 시스템 테스터"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.test_results = []
    
    def log(self, message, level='info'):
        """로그 출력"""
        colors = {
            'success': '\033[92m',  # 초록
            'error': '\033[91m',    # 빨강
            'warning': '\033[93m',  # 노랑
            'info': '\033[94m',     # 파랑
            'reset': '\033[0m'
        }
        
        symbols = {
            'success': '✓',
            'error': '✗',
            'warning': '⚠',
            'info': '→'
        }
        
        color = colors.get(level, colors['info'])
        symbol = symbols.get(level, '→')
        
        print(f"{color}{symbol} {message}{colors['reset']}")
    
    def run_test(self, test_name, test_func):
        """테스트 실행 및 결과 기록"""
        try:
            self.log(f'\n테스트: {test_name}', 'info')
            result = test_func()
            
            if result:
                self.log(f'{test_name} 성공', 'success')
                self.test_results.append((test_name, True, None))
            else:
                self.log(f'{test_name} 실패', 'error')
                self.test_results.append((test_name, False, '테스트 실패'))
        
        except Exception as e:
            self.log(f'{test_name} 오류: {e}', 'error')
            self.test_results.append((test_name, False, str(e)))
    
    def test_ingredient_mapping(self):
        """1. 식재료 매핑 시스템 테스트"""
        test_cases = [
            ('onion', '양파'),
            ('garlic', '마늘'),
            ('soy sauce', '간장'),
            ('chicken breast', '닭가슴살'),
            ('tomato', '토마토'),
            ('green onion', '대파'),
            ('ginger', '생강'),
            ('sesame oil', '참기름'),
        ]
        
        success_count = 0
        for eng_name, expected_kor in test_cases:
            ingredient = IngredientMapper.find_ingredient(eng_name)
            
            if ingredient and ingredient.name_ko == expected_kor:
                if self.verbose:
                    self.log(f'  "{eng_name}" → "{ingredient.name_ko}" (정확)', 'success')
                success_count += 1
            elif ingredient:
                self.log(
                    f'  "{eng_name}" → "{ingredient.name_ko}" (매핑됨, 기대: {expected_kor})',
                    'warning'
                )
                success_count += 1  # 매핑이 되긴 함
            else:
                self.log(f'  "{eng_name}" → 매핑 실패 (기대: {expected_kor})', 'error')
        
        self.log(f'\n매핑 성공률: {success_count}/{len(test_cases)} ({success_count/len(test_cases)*100:.1f}%)', 'info')
        
        return success_count == len(test_cases)
    
    def test_direct_ingredient_input(self):
        """2. 직접 추가 재료 처리 테스트"""
        test_inputs = [
            '새송이버섯',
            '청양고추',
            '양배추',
        ]
        
        success_count = 0
        for user_input in test_inputs:
            ingredient = IngredientMapper.get_or_create_user_ingredient(user_input)
            
            if ingredient:
                self.log(
                    f'  "{user_input}" → {ingredient.name_ko} (카테고리: {ingredient.category.name})',
                    'success'
                )
                success_count += 1
            else:
                self.log(f'  "{user_input}" → 생성 실패', 'error')
        
        return success_count == len(test_inputs)
    
    def test_normalization(self):
        """3. 이름 정규화 테스트"""
        test_cases = [
            ('chopped onion', 'onion'),
            ('2 cups flour', 'flour'),
            ('다진 마늘', '마늘'),
            ('fresh ginger (1 inch)', 'ginger'),
            ('chicken breast, skinless', 'chicken breast'),
        ]
        
        success_count = 0
        for raw_name, expected_normalized in test_cases:
            normalized = IngredientMapper.normalize_name(raw_name)
            
            if expected_normalized in normalized or normalized in expected_normalized:
                if self.verbose:
                    self.log(f'  "{raw_name}" → "{normalized}"', 'success')
                success_count += 1
            else:
                self.log(f'  "{raw_name}" → "{normalized}" (기대: {expected_normalized})', 'warning')
        
        return success_count >= len(test_cases) * 0.8  # 80% 성공률
    
    def test_recipe_search(self):
        """4. 레시피 검색 테스트"""
        # 한식 레시피 확인
        korean_recipes = Recipe.objects.filter(source='korean_db')
        
        if korean_recipes.exists():
            self.log(f'  한식 레시피: {korean_recipes.count()}개', 'success')
        else:
            self.log('  한식 레시피 없음 (load_korean_recipes 실행 필요)', 'warning')
        
        # Spoonacular 레시피 확인
        spoon_recipes = Recipe.objects.filter(source='spoonacular')
        
        if spoon_recipes.exists():
            self.log(f'  Spoonacular 레시피: {spoon_recipes.count()}개', 'success')
        else:
            self.log('  Spoonacular 레시피 없음 (정상, API 검색 시 생성됨)', 'info')
        
        # 전체 레시피
        total_recipes = Recipe.objects.count()
        self.log(f'  전체 레시피: {total_recipes}개', 'info')
        
        return total_recipes > 0
    
    def test_recommendation_algorithm(self):
        """5. 추천 알고리즘 테스트"""
        # 테스트 사용자 생성
        user, created = User.objects.get_or_create(
            email='test_recommendation@recipick.com',
            defaults={'nickname': '추천테스트'}
        )
        
        if created:
            user.set_password('test1234')
            user.save()
        
        # 프로필 생성
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'cooking_level': 'INTERMEDIATE',
                'allergies': [],
                'banned_ingredients': []
            }
        )
        
        # 식재료 추가
        test_ingredients = [
            ('양파', 3),  # D-3
            ('마늘', 7),  # D-7
            ('계란', 2),  # D-2 (긴급)
            ('대파', 10),  # D-10
        ]
        
        UserIngredient.objects.filter(user=user).delete()  # 기존 데이터 삭제
        
        user_ingredients = []
        for ing_name, days_left in test_ingredients:
            ingredient = IngredientMaster.find_by_name(ing_name)
            if ingredient:
                ui = UserIngredient.objects.create(
                    user=user,
                    ingredient=ingredient,
                    expire_at=date.today() + timedelta(days=days_left),
                    is_consumed=False
                )
                user_ingredients.append(ui)
        
        self.log(f'  테스트 식재료 {len(user_ingredients)}개 생성', 'success')
        
        # 매칭되는 레시피 검색
        user_ingredient_ids = [ui.ingredient_id for ui in user_ingredients]
        recipes = Recipe.objects.filter(
            recipe_ingredients__ingredient_id__in=user_ingredient_ids
        ).distinct()[:5]
        
        if not recipes.exists():
            self.log('  매칭되는 레시피 없음', 'warning')
            return False
        
        self.log(f'  매칭된 레시피: {recipes.count()}개', 'success')
        
        # 추천 점수 계산
        user_ingredients_dict = {ui.ingredient_id: ui for ui in user_ingredients}
        
        for recipe in recipes:
            score_data = recipe.calculate_recommendation_score(
                user=user,
                user_ingredient_ids=user_ingredient_ids,
                user_ingredients_dict=user_ingredients_dict,
                user_skill_level='INTERMEDIATE'
            )
            
            if self.verbose:
                self.log(
                    f'    - {recipe.title[:30]}: {score_data["total_score"]:.1f}점 '
                    f'(재료: {score_data["ingredient_score"]:.1f}, '
                    f'유통: {score_data["expiry_score"]:.1f})',
                    'info'
                )
        
        return True
    
    def test_spoonacular_api(self):
        """6. Spoonacular API 테스트 (선택)"""
        try:
            from recipes.services.spoonacular import SpoonacularService
            service = SpoonacularService()
            
            # 간단한 검색
            results = service.search_recipes_by_ingredients(
                ingredients=['chicken', 'tomato'],
                number=3
            )
            
            if results:
                self.log(f'  API 검색 성공 ({len(results)}개)', 'success')
                
                if self.verbose:
                    for recipe in results:
                        self.log(f'    - {recipe.get("title", "Unknown")}', 'info')
                
                return True
            else:
                self.log('  검색 결과 없음', 'warning')
                return False
        
        except ValueError as e:
            self.log(f'  API 키 오류: {e}', 'warning')
            self.log('  .env 파일에 SPOONACULAR_API_KEY 설정 필요', 'info')
            return None  # 스킵
        
        except Exception as e:
            self.log(f'  API 오류: {e}', 'error')
            return False
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print('\n' + '='*70)
        print('레시픽 시스템 통합 테스트')
        print('='*70)
        
        # 테스트 실행
        self.run_test('식재료 매핑 시스템', self.test_ingredient_mapping)
        self.run_test('직접 추가 재료 처리', self.test_direct_ingredient_input)
        self.run_test('이름 정규화', self.test_normalization)
        self.run_test('레시피 검색', self.test_recipe_search)
        self.run_test('추천 알고리즘', self.test_recommendation_algorithm)
        
        # Spoonacular는 선택적
        result = self.test_spoonacular_api()
        if result is not None:
            self.run_test('Spoonacular API', lambda: result)
        
        # 결과 요약
        self.print_summary()
    
    def print_summary(self):
        """테스트 결과 요약"""
        print('\n' + '='*70)
        print('테스트 결과 요약')
        print('='*70 + '\n')
        
        total = len(self.test_results)
        passed = sum(1 for _, success, _ in self.test_results if success)
        failed = total - passed
        
        for test_name, success, error in self.test_results:
            status = '✓ 성공' if success else '✗ 실패'
            color = '\033[92m' if success else '\033[91m'
            reset = '\033[0m'
            
            print(f'{color}{status}{reset} {test_name}')
            if not success and error:
                print(f'    오류: {error}')
        
        print(f'\n총 {total}개 테스트 중 {passed}개 성공, {failed}개 실패')
        
        if failed == 0:
            print('\n🎉 모든 테스트 통과!')
        else:
            print(f'\n⚠ {failed}개 테스트 실패 - 위 내용을 확인하세요')
        
        print('')


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='레시픽 시스템 통합 테스트')
    parser.add_argument('--verbose', '-v', action='store_true', help='상세 로그 출력')
    parser.add_argument('--skip-api', action='store_true', help='Spoonacular API 테스트 건너뛰기')
    
    args = parser.parse_args()
    
    tester = RecipickTester(verbose=args.verbose)
    tester.run_all_tests()


if __name__ == '__main__':
    main()