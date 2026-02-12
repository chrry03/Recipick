"""
Translation Service (번역 서비스)

Google Translate API를 사용한 자동 번역
- 레시피 제목 번역
- 조리법 번역
- 조리 단계 번역
"""
# recipes/services/translator.py
from deep_translator import GoogleTranslator
import time
import re


class RecipeTranslator:
    """Recipe.instructions 구조에 맞춘 번역 서비스"""

    def __init__(self):
        self.translator = GoogleTranslator(source='en', target='ko')
        self.delay = 0.3

    def _is_korean(self, text):
        return bool(re.search(r'[가-힣]', text))

    def translate_text(self, text, max_retries=3):
        if not text:
            return ''

        if self._is_korean(text):
            return text

        for attempt in range(max_retries):
            try:
                translated = self.translator.translate(text)
                time.sleep(self.delay)
                return translated
            except Exception:
                if attempt == max_retries - 1:
                    return text
                time.sleep(1)

        return text

    def translate_full_recipe(self, recipe_data):
        """
        recipe_data = {
            'title': str,
            'instructions': [
                {'step': 1, 'description': 'Mix...', 'image': None}
            ]
        }
        """
        result = {}

        # 제목 번역
        if recipe_data.get('title'):
            print(f"📝 제목 번역: {recipe_data['title']}")
            result['title_ko'] = self.translate_text(recipe_data['title'])

        # instructions 번역 (⭐ 핵심 ⭐)
        instructions = recipe_data.get('instructions') or []

        # [수정] instructions가 리스트인지 확인
        if instructions and isinstance(instructions, list):
            print(f"🔢 {len(instructions)}개 단계 번역 중...")
            translated = []

            for step in instructions:
                # [수정] step이 dict인지 확인
                if not isinstance(step, dict):
                    continue
                    
                description = step.get('description', '')
                description_ko = step.get('description_ko')

                if description and not description_ko:
                    description_ko = self.translate_text(description)

                translated.append({
                    **step,
                    'description_ko': description_ko
                })

            result['instructions'] = translated
        elif isinstance(instructions, str):
            # instructions가 문자열이면 그냥 저장
            result['instructions'] = []

        result['is_translated'] = True
        return result