from django.core.management.base import BaseCommand
from recipes.models import Recipe, RecipeIngredient, DifficultyLevel
from ingredients.models import IngredientMaster
from ingredients.utils.mapper import IngredientMapper
import json
import re


class Command(BaseCommand):
    help = '한식 레시피 DB를 로드합니다 (식품안전나라)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='foodsafetykorea.json',
            help='레시피 JSON 파일 경로 (기본: foodsafetykorea.json)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='로드할 레시피 개수 제한 (테스트용)'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        limit = options['limit']
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('한식 레시피 DB 로드 시작'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        
        self.stdout.write(f'파일: {file_path}')
        if limit:
            self.stdout.write(f'제한: {limit}개\n')
        
        # JSON 파일 읽기
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'✗ 파일을 찾을 수 없습니다: {file_path}'))
            self.stdout.write(self.style.WARNING('foodsafetykorea.json 파일을 프로젝트 루트에 배치하세요.\n'))
            return
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'✗ JSON 파싱 오류: {e}\n'))
            return
        
        # 레시피 데이터 추출
        try:
            recipes_data = data['COOKRCP01']['row']
        except KeyError:
            self.stdout.write(self.style.ERROR('✗ JSON 구조가 올바르지 않습니다.\n'))
            return
        
        total_count = len(recipes_data)
        self.stdout.write(f'총 {total_count}개 레시피 발견\n')
        
        # 제한 적용
        if limit:
            recipes_data = recipes_data[:limit]
        
        # 레시피 처리
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for i, recipe_data in enumerate(recipes_data, 1):
            try:
                # 이미 존재하는지 확인
                rcp_seq = recipe_data.get('RCP_SEQ', '')
                external_id = f"korean_{rcp_seq}"
                
                if Recipe.objects.filter(external_id=external_id).exists():
                    skip_count += 1
                    continue
                
                # 레시피 생성
                recipe = self.create_recipe(recipe_data)
                if recipe:
                    success_count += 1
                    if i % 100 == 0:
                        self.stdout.write(f'진행 중... {i}/{len(recipes_data)} ({success_count} 성공)')
                else:
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'✗ 레시피 처리 오류 ({i}번째): {e}'))
        
        # 결과 출력
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('한식 레시피 DB 로드 완료'))
        self.stdout.write('='*60)
        self.stdout.write(f'✓ 성공: {success_count}개')
        self.stdout.write(f'○ 건너뜀: {skip_count}개 (이미 존재)')
        self.stdout.write(f'✗ 실패: {error_count}개\n')
    
    def create_recipe(self, recipe_data):
        """개별 레시피 생성"""
        rcp_seq = recipe_data.get('RCP_SEQ', '')
        rcp_nm = recipe_data.get('RCP_NM', '').strip()
        
        if not rcp_nm:
            return None
        
        # Recipe 객체 생성
        recipe = Recipe(
            external_id=f"korean_{rcp_seq}",
            title=rcp_nm,  # ← name이 아닌 title
            source='korean_db',
            ready_minutes=self.estimate_cooking_time(recipe_data),  # ← cooking_time이 아닌 ready_minutes
            servings=2,  # 한식 DB에는 인분 정보가 없으므로 기본값
            image_url=recipe_data.get('ATT_FILE_NO_MAIN', ''),
        )
        
        # 난이도 추정
        recipe.difficulty = self.estimate_difficulty(recipe_data)  # ← difficulty_level이 아닌 difficulty
        
        # 조리 단계 추출
        instructions = self.extract_instructions(recipe_data)
        recipe.instructions = instructions  # JSON 필드라서 자동 변환
        
        recipe.save()
        
        # 재료 추출 및 매핑
        ingredients_text = recipe_data.get('RCP_PARTS_DTLS', '')
        if ingredients_text:
            self.add_ingredients_to_recipe(recipe, ingredients_text)
        
        # 재료 개수 업데이트
        recipe.update_ingredient_counts()
        
        return recipe
    
    def extract_instructions(self, recipe_data):
        """조리 단계 추출"""
        instructions = []
        
        # MANUAL01 ~ MANUAL20
        for i in range(1, 21):
            manual_key = f'MANUAL{i:02d}'
            manual_text = recipe_data.get(manual_key, '').strip()
            
            if manual_text:
                instructions.append({
                    'step': i,
                    'description': manual_text,  # ← text가 아닌 description
                    'image': recipe_data.get(f'MANUAL_IMG{i:02d}', '')
                })
        
        return instructions
    
    def add_ingredients_to_recipe(self, recipe, ingredients_text):
        """
        재료를 레시피에 추가 (자동 생성 포함 + 정규화)
        
        개선사항:
        1. "재료 " 접두사 제거
        2. IngredientMapper 사용
        3. 없으면 전체 DB에서 검색 (중복 방지)
        4. 그래도 없으면 FoodSafetyKorea 카테고리에 생성
        """
        # FoodSafetyKorea 카테고리 ID
        korea_category_id = self._get_foodsafety_category_id()
        
        # 재료 파싱 (예: "양파 1개, 마늘 3쪽, 간장 2큰술")
        ingredient_parts = re.split(r'[,·]', ingredients_text)
        
        created_count = 0
        
        for part in ingredient_parts:
            part = part.strip()
            if not part:
                continue
            
            # 재료명과 양 분리
            match = re.match(r'([가-힣a-zA-Z\s]+)\s*([\d./]+)?\s*([가-힣a-zA-Z()]+)?', part)
            
            if match:
                ing_name_raw = match.group(1).strip()
                
                # [1] 정규화 (괄호 안 내용 제거 + "재료 " 접두사 제거)
                ing_name = self._normalize_korean_ingredient(ing_name_raw)
                
                # [2] IngredientMapper로 매핑 시도
                ingredient = IngredientMapper.find_ingredient(ing_name)
                
                # [3] 못 찾으면 전체 DB에서 검색 (중복 방지)
                if not ingredient:
                    from ingredients.models import IngredientMaster
                    ingredient = IngredientMaster.objects.filter(
                        name_ko=ing_name
                    ).first()
                
                # [4] 그래도 없으면 자동 생성
                if not ingredient:
                    try:
                        from ingredients.models import IngredientMaster, IngredientCategory
                        
                        # 카테고리 가져오기
                        category = IngredientCategory.objects.get(category_id=korea_category_id)
                        
                        # 새로 생성
                        ingredient = IngredientMaster.objects.create(
                            category=category,
                            name_ko=ing_name,
                            name_en='',
                            aliases=[]
                        )
                        created_count += 1
                        self.stdout.write(f'   ➕ 식재료 자동 생성: {ing_name}')
                            
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(
                            f'   ⚠️  생성 실패: {ing_name} - {str(e)}'
                        ))
                        continue
                
                if ingredient:
                    # 이미 추가된 재료인지 확인
                    if not RecipeIngredient.objects.filter(
                        recipe=recipe,
                        ingredient=ingredient
                    ).exists():
                        RecipeIngredient.objects.create(
                            recipe=recipe,
                            ingredient=ingredient,
                            ingredient_name=ing_name,
                            is_optional=False
                        )
        
        if created_count > 0:
            self.stdout.write(f'   ✨ 새 식재료 {created_count}개 자동 생성됨')
    
    def _get_foodsafety_category_id(self):
        """FoodSafetyKorea 카테고리 ID 가져오기 (고정: 18번)"""
        from ingredients.models import IngredientCategory
        
        # FoodSafetyKorea 카테고리 찾기 (pk=18)
        category = IngredientCategory.objects.filter(pk=18).first()
        
        if not category:
            # fixtures에 없으면 생성 (비상 대비)
            category, created = IngredientCategory.objects.get_or_create(
                name='FoodSafetyKorea',
                defaults={
                    'icon': '🇰🇷',
                    'parent': None,
                    'is_parent': False
                }
            )
            if created:
                self.stdout.write(f'   🆕 FoodSafetyKorea 카테고리 생성 (ID: {category.category_id})')
        
        return category.category_id
    
    def _normalize_korean_ingredient(self, name):
        """
        한글 식재료명 정규화
        
        예시:
        - "재료 미나리" → "미나리"
        - "돼지고기 100g" → "돼지고기"
        - "양파(1개)" → "양파"
        - "청양고추 10g(1/2개)" → "청양고추"
        """
        import re
        
        # [핵심 추가!] "재료 " 접두사 제거
        name = re.sub(r'^재료\s+', '', name)
        
        # 괄호 안 내용 제거
        name = re.sub(r'\([^)]*\)', '', name)
        
        # 수량 표현 제거
        name = re.sub(r'\d+[가-힣a-zA-Z]*', '', name)
        
        # 앞뒤 공백 제거
        name = name.strip()
        
        return name
    
    def estimate_cooking_time(self, recipe_data):
        """조리 시간 추정 (분)"""
        # 조리 단계 개수로 추정
        manual_count = 0
        for i in range(1, 21):
            if recipe_data.get(f'MANUAL{i:02d}', '').strip():
                manual_count += 1
        
        # 단계당 평균 5분으로 추정
        return manual_count * 5 if manual_count > 0 else 30
    
    def estimate_difficulty(self, recipe_data):
        """난이도 추정 (DifficultyLevel enum 반환)"""
        # 조리 단계 개수로 추정
        manual_count = 0
        for i in range(1, 21):
            if recipe_data.get(f'MANUAL{i:02d}', '').strip():
                manual_count += 1
        
        if manual_count <= 5:
            return DifficultyLevel.EASY
        elif manual_count <= 10:
            return DifficultyLevel.NORMAL
        else:
            return DifficultyLevel.DIFFICULT