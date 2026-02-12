#!/usr/bin/env python
"""
레시피 탭이 비어있는 문제 진단 스크립트

사용법:
    python diagnose_recipe_tab.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from recipes.models import Recipe, RecipeIngredient
from ingredients.models import UserIngredient, IngredientMaster

User = get_user_model()

print("=" * 70)
print("🔍 레시피 탭 문제 진단")
print("=" * 70)

# ============================================
# 1. 사용자 확인
# ============================================
users = User.objects.all()
print(f"\n📋 등록된 사용자: {users.count()}명")
for u in users:
    print(f"  - {u.username}")

if users.count() == 0:
    print("\n❌ 사용자가 없습니다!")
    print("💡 먼저 회원가입을 하세요.")
    exit()

username = input("\n확인할 사용자 아이디 입력: ")

try:
    user = User.objects.get(username=username)
except User.DoesNotExist:
    print(f"\n❌ 사용자 '{username}'를 찾을 수 없습니다.")
    exit()

print(f"\n✅ 사용자: {user.username}")

# ============================================
# 2. 식재료 확인
# ============================================
user_ingredients = UserIngredient.objects.filter(
    user=user,
    is_consumed=False
)

print(f"\n🥬 등록된 식재료: {user_ingredients.count()}개")

if user_ingredients.count() == 0:
    print("❌ 식재료가 없습니다!")
    print("💡 웹에서 '식재료' 탭 → '+' 버튼으로 식재료를 추가하세요.")
    print("💡 또는 add_test_ingredients.py 스크립트를 실행하세요.")
    exit()

print("\n식재료 목록:")
for ui in user_ingredients[:10]:
    ing_name = ui.ingredient.name_ko or ui.ingredient.name_en
    print(f"  - [{ui.ingredient.ingredient_id}] {ing_name} (만료: {ui.expire_at})")

if user_ingredients.count() > 10:
    print(f"  ... 외 {user_ingredients.count() - 10}개")

# ============================================
# 3. 레시피 확인
# ============================================
total_recipes = Recipe.objects.count()
print(f"\n📚 DB 레시피: {total_recipes}개")

if total_recipes == 0:
    print("❌ DB에 레시피가 없습니다!")
    print("💡 레시피를 수집하세요:")
    print("   python manage.py fetch_and_translate_recipes --cuisine italian --limit 20")
    exit()

# 출처별
from django.db.models import Count
by_source = Recipe.objects.values('source').annotate(count=Count('source'))
print("\n출처별:")
for item in by_source:
    print(f"  - {item['source']}: {item['count']}개")

# ============================================
# 4. API 시뮬레이션 (핵심!)
# ============================================
print("\n" + "=" * 70)
print("🧪 API 시뮬레이션 시작...")
print("=" * 70)

from recipes.utils import search_recipes_from_db
from recipes.models import Recipe

# 사용자 식재료 ID 목록
ingredient_ids = list(user_ingredients.values_list('ingredient_id', flat=True))
print(f"\n📋 식재료 ID: {ingredient_ids[:10]}...")

# DB 검색 (utils.py 함수 사용)
try:
    db_recipes = list(search_recipes_from_db(ingredient_ids, user))
    print(f"\n✅ search_recipes_from_db 성공: {len(db_recipes)}개")
    
    if len(db_recipes) == 0:
        print("\n⚠️  식재료는 있지만 매칭되는 레시피가 없습니다!")
        print("💡 가능한 원인:")
        print("   1. DB 레시피들이 사용자 식재료를 전혀 사용하지 않음")
        print("   2. RecipeIngredient 연결이 안 됨")
        
        # RecipeIngredient 확인
        total_connections = RecipeIngredient.objects.count()
        print(f"\n🔗 RecipeIngredient 연결: {total_connections}개")
        
        if total_connections == 0:
            print("❌ 레시피-식재료 연결이 전혀 없습니다!")
            print("💡 레시피를 다시 수집하세요:")
            print("   python manage.py fetch_and_translate_recipes --cuisine italian --limit 20")
        else:
            # 샘플 레시피 확인
            sample = Recipe.objects.first()
            sample_ings = RecipeIngredient.objects.filter(recipe=sample)
            print(f"\n📝 샘플 레시피: {sample.title}")
            print(f"   필요한 식재료: {sample_ings.count()}개")
            
            if sample_ings.count() > 0:
                print("   예시:")
                for ri in sample_ings[:5]:
                    ing_name = ri.ingredient.name_ko or ri.ingredient.name_en
                    print(f"     - [{ri.ingredient.ingredient_id}] {ing_name}")
                
                # 교집합 확인
                recipe_ing_ids = set(sample_ings.values_list('ingredient_id', flat=True))
                user_ing_ids = set(ingredient_ids)
                overlap = recipe_ing_ids & user_ing_ids
                
                print(f"\n🔍 교집합: {len(overlap)}개")
                if len(overlap) == 0:
                    print("❌ 사용자 식재료와 레시피 식재료가 하나도 안 겹칩니다!")
                    print("💡 다른 cuisine 레시피를 수집하거나")
                    print("   더 다양한 식재료를 등록하세요.")
    else:
        print("\n✅ 매칭되는 레시피가 있습니다!")
        print(f"\n상위 5개 레시피:")
        for i, recipe in enumerate(db_recipes[:5], 1):
            title = recipe.get_display_title()
            print(f"  {i}. {title}")
            
except Exception as e:
    print(f"\n❌ search_recipes_from_db 실패!")
    print(f"   에러: {str(e)}")
    import traceback
    traceback.print_exc()

# ============================================
# 5. 추천 점수 계산 테스트
# ============================================
if db_recipes:
    print("\n" + "=" * 70)
    print("🧮 추천 점수 계산 테스트")
    print("=" * 70)
    
    from recipes.utils import calculate_final_recommendations
    
    user_ingredients_dict = {
        ui.ingredient_id: ui for ui in user_ingredients
    }
    
    try:
        result = calculate_final_recommendations(
            recipes=db_recipes[:20],
            user=user,
            user_ingredients_dict=user_ingredients_dict,
            user_skill_level='INTERMEDIATE'
        )
        
        print(f"\n✅ 점수 계산 성공!")
        print(f"   총 레시피: {result['total_count']}개")
        
        if result['total_count'] == 0:
            print("\n⚠️  레시피는 있지만 점수가 60점 미만입니다!")
            print("💡 해결 방법:")
            print("   1. 더 많은 식재료 등록")
            print("   2. 식재료에 소비기한 설정 (임박한 재료 가중치 높음)")
        else:
            # 카테고리별
            urgent = result['categories']['urgent_ready']['count']
            ready = result['categories']['ready']['count']
            almost = result['categories']['almost_ready']['count']
            
            print(f"\n📊 카테고리별:")
            print(f"   - 긴급 (임박 재료): {urgent}개")
            print(f"   - 바로 가능: {ready}개")
            print(f"   - 거의 가능: {almost}개")
            
            # 상위 3개 레시피
            all_recipes = (
                result['categories']['urgent_ready']['recipes'] +
                result['categories']['ready']['recipes'] +
                result['categories']['almost_ready']['recipes']
            )
            
            print(f"\n🏆 추천 레시피 TOP 3:")
            for i, recipe in enumerate(all_recipes[:3], 1):
                total_score = recipe.get('total_score', 0)
                missing = recipe.get('missing_ingredients_count', 0)
                
                # total_ingredients는 레시피 모델에서 가져와야 함
                recipe_obj = Recipe.objects.get(recipe_id=recipe['recipe_id'])
                total_ing = recipe_obj.total_ingredients
                have_count = total_ing - missing
                
                print(f"  {i}. {recipe['title']} (점수: {total_score}점)")
                print(f"     보유 재료: {have_count}/{total_ing}개")
        
    except Exception as e:
        print(f"\n❌ 점수 계산 실패!")
        print(f"   에러: {str(e)}")
        import traceback
        traceback.print_exc()

# ============================================
# 6. 최종 진단
# ============================================
print("\n" + "=" * 70)
print("📋 최종 진단 결과")
print("=" * 70)

issues = []
solutions = []

if user_ingredients.count() == 0:
    issues.append("❌ 식재료 없음")
    solutions.append("💡 식재료 등록 필요")

if total_recipes == 0:
    issues.append("❌ 레시피 없음")
    solutions.append("💡 레시피 수집 필요")

if 'db_recipes' in locals() and len(db_recipes) == 0:
    issues.append("❌ 매칭되는 레시피 없음")
    solutions.append("💡 다양한 cuisine 레시피 수집 또는 더 많은 식재료 등록")

if 'result' in locals() and result['total_count'] == 0:
    issues.append("❌ 추천 점수 60점 미만")
    solutions.append("💡 더 많은 식재료 등록 & 소비기한 설정")

if len(issues) == 0:
    print("\n🎉 모든 확인 완료!")
    print("✅ 레시피 탭이 정상 작동해야 합니다.")
    print("\n💡 웹에서 확인:")
    print("   1. F5 (새로고침)")
    print("   2. 레시피 탭 클릭")
else:
    print("\n발견된 문제:")
    for issue in issues:
        print(f"  {issue}")
    print("\n해결 방법:")
    for solution in solutions:
        print(f"  {solution}")

print("\n" + "=" * 70)