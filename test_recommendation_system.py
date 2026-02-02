import os
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from ingredients.models import IngredientCategory, IngredientMaster, UserIngredient, IngredientNameMapping
from recipes.models import Recipe, RecipeIngredient
from users.models import User, UserProfile
from ingredients.utils.mapper import IngredientMapper
from datetime import date, timedelta


def test_ingredient_mapping():
    """식재료 매핑 테스트"""
    print("\n" + "="*60)
    print("=== 식재료 매핑 테스트 ===")
    print("="*60)
    
    # 테스트 케이스
    test_cases = [
        ('onion', '양파'),
        ('garlic', '마늘'),
        ('soy sauce', '간장'),
        ('tomato', '토마토'),
        ('chicken', '닭고기'),
    ]
    
    for eng_name, expected_kor in test_cases:
        ingredient = IngredientMapper.find_ingredient(eng_name)
        if ingredient and ingredient.name_ko == expected_kor:
            print(f"✓ '{eng_name}' → '{ingredient.name_ko}' (성공)")
        elif ingredient:
            print(f"⚠️  '{eng_name}' → '{ingredient.name_ko}' (매핑됨, 기대: {expected_kor})")
        else:
            print(f"✗ '{eng_name}' → 매핑 실패 (기대: {expected_kor})")


def test_spoonacular_api():
    """Spoonacular API 테스트"""
    print("\n" + "="*60)
    print("=== Spoonacular API 테스트 ===")
    print("="*60)
    
    try:
        from recipes.services.spoonacular import SpoonacularService
        service = SpoonacularService()
        
        print("재료 기반 레시피 검색 중...")
        results = service.search_recipes_by_ingredients(
            ingredients=['chicken', 'tomato', 'garlic'],
            number=3
        )
        
        if results:
            print(f"✓ {len(results)}개 레시피 검색 성공")
            for recipe in results[:3]:
                print(f"  - {recipe.get('title', 'Unknown')}")
        else:
            print("✗ 검색 결과 없음")
            
    except ValueError as e:
        print(f"✗ API 키 오류: {e}")
        print("  .env 파일에 SPOONACULAR_API_KEY를 설정하세요")
    except Exception as e:
        print(f"✗ API 테스트 실패: {e}")


def create_test_data():
    """테스트 데이터 생성"""
    print("\n" + "="*60)
    print("=== 테스트 데이터 생성 ===")
    print("="*60)
    
    # 1. 카테고리 생성
    category, created = IngredientCategory.objects.get_or_create(
        name='채소류',
        defaults={'icon_url': '/static/images/vegetable.png'}
    )
    if created:
        print("✓ 카테고리 생성: 채소류")
    
    # 2. 식재료 생성
    ingredients_data = [
        ('양파', 'onion'),
        ('대파', 'green onion'),
        ('마늘', 'garlic'),
        ('당근', 'carrot'),
        ('토마토', 'tomato'),
    ]
    
    for name_ko, name_en in ingredients_data:
        ingredient, created = IngredientMaster.objects.get_or_create(
            name_ko=name_ko,
            defaults={
                'category': category,
                'name_en': name_en
            }
        )
        if created:
            print(f"✓ 식재료 생성: {name_ko} ({name_en})")
    
    # 3. 테스트 사용자 생성
    user, created = User.objects.get_or_create(
        email='test@recipick.com',
        defaults={
            'nickname': '테스트유저',
            'username': 'test@recipick.com'  # username 필드 명시
        }
    )
    if created:
        user.set_password('test1234')
        user.save()
        print(f"✓ 테스트 사용자 생성: {user.nickname}")
        
        # UserProfile 생성 (User 생성 시 자동으로 생성되지 않으므로 수동 생성)
        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'cooking_level': UserProfile.CookingLevel.INTERMEDIATE
            }
        )
        if profile_created:
            print(f"✓ 사용자 프로필 생성: 중급")
    else:
        print(f"○ 테스트 사용자 이미 존재: {user.nickname}")
        # 기존 사용자의 프로필 확인
        if not hasattr(user, 'profile'):
            profile, profile_created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'cooking_level': UserProfile.CookingLevel.INTERMEDIATE
                }
            )
            if profile_created:
                print(f"✓ 사용자 프로필 생성: 중급")
    
    # 4. 사용자 식재료 등록
    today = date.today()
    user_ingredients_data = [
        ('양파', 5),   # D-5
        ('대파', 10),  # D-10
        ('마늘', 3),   # D-3
    ]
    
    for ing_name, days in user_ingredients_data:
        try:
            ingredient = IngredientMaster.objects.get(name_ko=ing_name)
            user_ing, created = UserIngredient.objects.get_or_create(
                user=user,
                ingredient=ingredient,
                defaults={
                    'expire_at': today + timedelta(days=days),
                    'is_consumed': False
                }
            )
            if created:
                print(f"✓ 사용자 식재료 등록: {ing_name} (D-{days})")
        except IngredientMaster.DoesNotExist:
            print(f"✗ 식재료 '{ing_name}' 찾을 수 없음")
    
    return user


def test_recommendation_algorithm():
    """추천 알고리즘 테스트"""
    print("\n" + "="*60)
    print("=== 추천 알고리즘 테스트 ===")
    print("="*60)
    
    # 테스트 사용자 가져오기
    try:
        user = User.objects.get(email='test@recipick.com')
    except User.DoesNotExist:
        print("✗ 테스트 사용자가 없습니다. create_test_data()를 먼저 실행하세요.")
        return
    
    # 사용자 보유 식재료
    user_ingredients = UserIngredient.objects.filter(
        user=user,
        is_consumed=False
    ).select_related('ingredient')
    
    print(f"사용자 보유 식재료: {user_ingredients.count()}개")
    for ui in user_ingredients:
        days_left = ui.days_until_expiry
        print(f"  - {ui.ingredient.name_ko} (D-{days_left})")
    
    # 매칭되는 레시피 조회
    ingredient_ids = list(user_ingredients.values_list('ingredient_id', flat=True))
    recipes = Recipe.objects.filter(
        recipe_ingredients__ingredient_id__in=ingredient_ids
    ).distinct()
    
    print(f"\n매칭 레시피: {recipes.count()}개")
    
    if recipes.count() == 0:
        print("⚠️  매칭되는 레시피가 없습니다.")
        print("   python manage.py load_korean_recipes를 실행해주세요.")
        return
    
    # 추천 점수 계산
    user_ingredients_dict = {
        ui.ingredient_id: ui for ui in user_ingredients
    }
    
    # 사용자 스킬 레벨 가져오기 (UserProfile에서)
    if hasattr(user, 'profile'):
        user_skill_level = user.profile.cooking_level
    else:
        user_skill_level = 'INTERMEDIATE'
        print("⚠️  사용자 프로필이 없어 기본값(중급) 사용")
    
    for recipe in recipes[:5]:  # 상위 5개만 테스트
        score_data = recipe.calculate_recommendation_score(
            user=user,
            user_ingredient_ids=ingredient_ids,
            user_ingredients_dict=user_ingredients_dict,
            user_skill_level=user_skill_level
        )
        
        print(f"\n레시피: {recipe.title}")
        print(f"  총점: {score_data['total_score']:.1f}")
        print(f"  - 재료 매칭: {score_data['ingredient_score']:.1f}")
        print(f"  - 유통기한: {score_data['expiry_score']:.1f}")
        print(f"  - 난이도: {score_data['difficulty_score']:.1f}")
        print(f"  - 개인화: {score_data['personalization_score']:.1f}")
        print(f"  부족한 재료: {score_data['missing_ingredients_count']}개")
        
        category = recipe.get_recommendation_category(score_data['total_score'])
        category_labels = {
            'urgent_ready': '긴급 (유통기한 임박)',
            'ready': '바로 가능',
            'almost_ready': '재료 1-2개 부족'
        }
        print(f"  카테고리: {category_labels.get(category, '해당 없음')}")


def main():
    """메인 테스트 실행"""
    print("\n" + "="*60)
    print("레시픽 레시피 추천 시스템 통합 테스트")
    print("="*60)
    
    # 1. 식재료 매핑 테스트
    test_ingredient_mapping()
    
    # 2. Spoonacular API 테스트
    test_spoonacular_api()
    
    # 3. 테스트 데이터 생성
    user = create_test_data()
    
    # 4. 추천 알고리즘 테스트
    test_recommendation_algorithm()
    
    print("\n" + "="*60)
    print("테스트 완료!")
    print("="*60)
    print("\n다음 단계:")
    print("1. python manage.py runserver로 서버 실행")
    print("2. 브라우저에서 http://localhost:8000/recipes/ 접속")
    print("3. 테스트 계정으로 로그인 (test@recipick.com / test1234)")
    print("4. '레시피 추천받기' 버튼 클릭\n")


if __name__ == '__main__':
    main()