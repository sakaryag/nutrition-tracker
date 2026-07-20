"""
Tests for local_model.py — NLP food parsing quality.
Run: pytest tests/test_local_nlp.py -v

These tests don't require a DB connection — they use a fixed food_db fixture.
spaCy must be installed: pip install spacy && python -m spacy download en_core_web_sm
"""
import pytest

try:
    from local_model import parse_and_match, extract_mentions, detect_meal, is_available
    SKIP = not is_available()
except ImportError:
    SKIP = True

pytestmark = pytest.mark.skipif(SKIP, reason='spaCy/rapidfuzz not installed')

FOOD_DB = [
    {'id': 1,  'name': 'Egg, whole, boiled',                         'name_tr': 'Yumurta, tam, haslanmis',              'protein': 12.6, 'fat': 10.6, 'carbs': 1.1,  'calories': 155, 'default_serving': 1,   'serving_unit': 'piece'},
    {'id': 2,  'name': 'Egg, whole, raw',                            'name_tr': 'Yumurta, tam, cig',                    'protein': 12.6, 'fat': 10.6, 'carbs': 1.1,  'calories': 155, 'default_serving': 1,   'serving_unit': 'piece'},
    {'id': 3,  'name': 'Egg salad',                                  'name_tr': 'Yumurta salatasi',                     'protein': 7.0,  'fat': 9.0,  'carbs': 2.0,  'calories': 120, 'default_serving': 100, 'serving_unit': 'g'},
    {'id': 4,  'name': 'Egg, scrambled',                             'name_tr': 'Yumurta, citirilmis',                  'protein': 9.9,  'fat': 7.0,  'carbs': 1.6,  'calories': 149, 'default_serving': 1,   'serving_unit': 'piece'},
    {'id': 5,  'name': 'Milk, whole, 3.7% fat',                      'name_tr': 'Sut, tam yagli',                       'protein': 3.2,  'fat': 3.7,  'carbs': 4.8,  'calories': 61,  'default_serving': 240, 'serving_unit': 'ml'},
    {'id': 6,  'name': 'Oat milk, original',                         'name_tr': 'Yulaf sutu, orijinal',                 'protein': 1.0,  'fat': 1.5,  'carbs': 16.0, 'calories': 80,  'default_serving': 240, 'serving_unit': 'ml'},
    {'id': 7,  'name': 'Oat milk, unsweetened',                      'name_tr': 'Yulaf sutu, sekersiz',                 'protein': 1.0,  'fat': 1.5,  'carbs': 12.0, 'calories': 60,  'default_serving': 240, 'serving_unit': 'ml'},
    {'id': 8,  'name': 'Bread',                                      'name_tr': 'Ekmek',                                'protein': 9.0,  'fat': 3.2,  'carbs': 49.0, 'calories': 265, 'default_serving': 1,   'serving_unit': 'slice'},
    {'id': 9,  'name': 'Oats, rolled, dry',                          'name_tr': 'Yulaf ezmesi, kuru',                   'protein': 16.9, 'fat': 6.9,  'carbs': 66.3, 'calories': 389, 'default_serving': 80,  'serving_unit': 'g'},
    {'id': 10, 'name': 'Toast',                                      'name_tr': 'Tost',                                 'protein': 10.0, 'fat': 4.0,  'carbs': 50.0, 'calories': 275, 'default_serving': 1,   'serving_unit': 'slice'},
    {'id': 11, 'name': 'Chicken breast, boneless skinless, cooked',  'name_tr': 'Tavuk gogsu, derisiz kemiksiz, pismis','protein': 31.0, 'fat': 3.6,  'carbs': 0.0,  'calories': 165, 'default_serving': 150, 'serving_unit': 'g'},
    {'id': 12, 'name': 'Brown rice, long grain, cooked',             'name_tr': 'Esmer pirinc, uzun taneli, pismis',    'protein': 2.6,  'fat': 0.9,  'carbs': 23.0, 'calories': 112, 'default_serving': 200, 'serving_unit': 'g'},
    {'id': 13, 'name': 'Banana',                                     'name_tr': 'Muz',                                  'protein': 1.1,  'fat': 0.3,  'carbs': 23.0, 'calories': 89,  'default_serving': 1,   'serving_unit': 'piece'},
    {'id': 14, 'name': 'Greek yogurt, plain, nonfat',                'name_tr': 'Yunan yogurdu, sade, yagsiz',          'protein': 17.0, 'fat': 0.7,  'carbs': 6.0,  'calories': 100, 'default_serving': 200, 'serving_unit': 'g'},
    {'id': 15, 'name': 'Almond butter',                              'name_tr': 'Badem ezmesi',                         'protein': 7.0,  'fat': 18.0, 'carbs': 6.0,  'calories': 196, 'default_serving': 2,   'serving_unit': 'tbsp'},
    {'id': 16, 'name': 'Peanut butter, creamy',                      'name_tr': 'Fisitik ezmesi, kremali',              'protein': 7.0,  'fat': 16.0, 'carbs': 7.0,  'calories': 188, 'default_serving': 2,   'serving_unit': 'tbsp'},
    {'id': 17, 'name': 'Apple, Gala',                                'name_tr': 'Elma, Gala',                           'protein': 0.3,  'fat': 0.2,  'carbs': 14.0, 'calories': 52,  'default_serving': 1,   'serving_unit': 'piece'},
    {'id': 18, 'name': 'Salmon, Atlantic, cooked',                   'name_tr': 'Somon, Atlantik, pismis',              'protein': 25.0, 'fat': 13.0, 'carbs': 0.0,  'calories': 208, 'default_serving': 150, 'serving_unit': 'g'},
]


def first_name(text, lang='en'):
    results = parse_and_match(text, FOOD_DB, lang=lang)
    return results[0]['food_name'] if results else None


# ---------------------------------------------------------------------------
# English — food identification
# ---------------------------------------------------------------------------

class TestEnglishBasic:
    def test_two_eggs_and_toast(self):
        results = parse_and_match('2 eggs and toast for breakfast', FOOD_DB)
        names = [r['food_name'] for r in results]
        assert any('Egg' in n and 'salad' not in n.lower() for n in names), f'No plain egg in {names}'
        assert any('Toast' in n or 'Bread' in n for n in names), f'No toast/bread in {names}'

    def test_scrambled_eggs(self):
        name = first_name('scrambled eggs')
        assert name and 'Egg' in name and 'salad' not in name.lower(), f'Got: {name}'

    def test_oats_gram_quantity(self):
        results = parse_and_match('80g oats with milk', FOOD_DB)
        oat = next((r for r in results if 'Oat' in r['food_name'] and 'milk' not in r['food_name'].lower()), None)
        assert oat, 'Should match oats'
        assert oat['serving_size'] == 80.0
        assert oat['serving_unit'] == 'g'

    def test_milk_not_oat_milk(self):
        results = parse_and_match('a glass of milk', FOOD_DB)
        names = [r['food_name'] for r in results]
        milk = next((n for n in names if 'Milk' in n), None)
        assert milk, f'No milk in {names}'
        assert 'Oat milk' not in milk, f'Matched oat milk for plain "milk": {milk}'

    def test_chicken_and_rice(self):
        results = parse_and_match('100g chicken breast with rice', FOOD_DB)
        names = [r['food_name'] for r in results]
        assert any('Chicken' in n for n in names), f'No chicken in {names}'
        assert any('rice' in n.lower() for n in names), f'No rice in {names}'

    def test_banana_and_yogurt(self):
        results = parse_and_match('a banana and greek yogurt', FOOD_DB)
        names = [r['food_name'] for r in results]
        assert any('Banana' in n for n in names), f'No banana in {names}'
        assert any('yogurt' in n.lower() for n in names), f'No yogurt in {names}'

    def test_tablespoon_unit(self):
        results = parse_and_match('2 tablespoons almond butter', FOOD_DB)
        ab = next((r for r in results if 'Almond butter' in r['food_name']), None)
        assert ab, f'Should match almond butter, got: {[r["food_name"] for r in results]}'
        assert ab['serving_size'] == 2.0

    def test_salmon(self):
        name = first_name('150g grilled salmon')
        assert name and 'Salmon' in name, f'Got: {name}'

    def test_no_duplicate_ids(self):
        results = parse_and_match('2 eggs and toast', FOOD_DB)
        ids = [r['saved_food_id'] for r in results]
        assert len(ids) == len(set(ids)), f'Duplicate food IDs: {ids}'


# ---------------------------------------------------------------------------
# English — quantities and meal type
# ---------------------------------------------------------------------------

class TestEnglishQuantities:
    def test_word_number_two(self):
        results = parse_and_match('two eggs', FOOD_DB)
        egg = next((r for r in results if 'Egg' in r['food_name'] and 'salad' not in r['food_name'].lower()), None)
        assert egg, f'No plain egg matched'
        assert egg['serving_size'] == 2.0

    def test_gram_scaling(self):
        results = parse_and_match('200g chicken breast', FOOD_DB)
        c = next((r for r in results if 'Chicken' in r['food_name']), None)
        assert c, 'No chicken matched'
        assert c['serving_size'] == 200.0
        assert c['serving_unit'] == 'g'

    def test_meal_detection_breakfast(self):
        results = parse_and_match('had eggs for breakfast', FOOD_DB)
        assert results, 'No results'
        assert results[0]['meal_type'] == 'Breakfast', f'Got: {results[0]["meal_type"]}'

    def test_meal_detection_dinner(self):
        results = parse_and_match('salmon for dinner', FOOD_DB)
        assert results, 'No results'
        assert results[0]['meal_type'] == 'Dinner', f'Got: {results[0]["meal_type"]}'

    def test_macro_scaling_correct(self):
        # 200g chicken: protein ≈ 200/100 * 31 = 62g
        results = parse_and_match('200g chicken breast', FOOD_DB)
        c = next((r for r in results if 'Chicken' in r['food_name']), None)
        assert c, 'No chicken matched'
        assert abs(c['protein'] - 62.0) < 5.0, f'Protein scaling wrong: {c["protein"]}'


# ---------------------------------------------------------------------------
# Turkish input
# ---------------------------------------------------------------------------

class TestTurkish:
    def test_yumurta_not_salata(self):
        results = parse_and_match('2 yumurta yedim', FOOD_DB, lang='tr')
        names = [r['food_name'] for r in results]
        assert any('Egg' in n for n in names), f'No egg matched: {names}'
        primary = names[0] if names else ''
        assert 'salad' not in primary.lower(), f'Primary match is egg salad: {primary}'

    def test_sut_not_yulaf_sutu(self):
        results = parse_and_match('bir bardak sut', FOOD_DB, lang='tr')
        names = [r['food_name'] for r in results]
        milk = next((n for n in names if 'Milk' in n), None)
        assert milk, f'No milk matched: {names}'
        assert 'Oat milk' not in milk, f'Matched oat milk for plain "sut": {milk}'

    def test_yulaf_not_yulaf_sutu(self):
        results = parse_and_match('80g yulaf', FOOD_DB, lang='tr')
        names = [r['food_name'] for r in results]
        assert any('Oat' in n and 'milk' not in n.lower() for n in names), f'No oats matched: {names}'

    def test_muz(self):
        results = parse_and_match('bir muz yedim', FOOD_DB, lang='tr')
        names = [r['food_name'] for r in results]
        assert any('Banana' in n for n in names), f'No banana: {names}'

    def test_tavuk(self):
        results = parse_and_match('200g tavuk gogsu', FOOD_DB, lang='tr')
        names = [r['food_name'] for r in results]
        assert any('Chicken' in n for n in names), f'No chicken: {names}'

    def test_kahvalti_meal_type(self):
        results = parse_and_match('kahvaltida yumurta yedim', FOOD_DB, lang='tr')
        assert results, 'No results'
        assert results[0]['meal_type'] == 'Breakfast', f'Got: {results[0]["meal_type"]}'

    def test_aksam_meal_type(self):
        results = parse_and_match('aksam yemeginde tavuk', FOOD_DB, lang='tr')
        assert results, 'No results'
        assert results[0]['meal_type'] == 'Dinner', f'Got: {results[0]["meal_type"]}'


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_string(self):
        assert parse_and_match('', FOOD_DB) == []

    def test_no_food_content(self):
        results = parse_and_match('hello how are you', FOOD_DB)
        assert isinstance(results, list)
