"""
Local NLP food parser — no cloud API required.

Pipeline:
  1. spaCy (en_core_web_sm, 12MB) for sentence understanding:
       - quantity + unit extraction via dependency tree
       - food noun-phrase detection
       - cooking-adjective awareness (grilled, scrambled, boiled…)
  2. rapidfuzz token_set_ratio for fuzzy matching against the SavedFood DB
       - "scrambled eggs" → "Egg, whole, cooked"
       - "grilled chicken" → "Chicken, broilers, cooked, roasted"
       - handles typos and partial names

Setup (one time):
  pip install spacy rapidfuzz
  python -m spacy download en_core_web_sm
"""

import re
import logging

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

_WORD_NUMBERS = {
    'a': 1, 'an': 1, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'half': 0.5, 'quarter': 0.25, 'couple': 2, 'few': 3,
    # Turkish
    'bir': 1, 'iki': 2, 'üç': 3, 'dört': 4, 'beş': 5,
    'yarım': 0.5, 'çeyrek': 0.25,
}

_UNIT_MAP = {
    'g': 'g', 'gr': 'g', 'gram': 'g', 'grams': 'g',
    'ml': 'ml', 'milliliter': 'ml', 'millilitre': 'ml',
    'milliliters': 'ml', 'millilitres': 'ml',
    'cup': 'cup', 'cups': 'cup',
    'tbsp': 'tbsp', 'tablespoon': 'tbsp', 'tablespoons': 'tbsp',
    'tsp': 'tsp', 'teaspoon': 'tsp', 'teaspoons': 'tsp',
    'piece': 'piece', 'pieces': 'piece',
    'slice': 'slice', 'slices': 'slice',
    'serving': 'serving', 'servings': 'serving',
    'glass': 'glass',
    # Conversions (applied via _UNIT_MULTIPLIERS)
    'kg': 'g', 'l': 'ml', 'lt': 'ml', 'oz': 'g', 'lb': 'g',
    # Turkish
    'adet': 'piece', 'dilim': 'slice', 'porsiyon': 'serving',
    'bardak': 'glass', 'kaşık': 'tbsp', 'avuç': 'g',
}

_UNIT_MULTIPLIERS = {
    'kg': 1000.0, 'l': 1000.0, 'lt': 1000.0,
    'oz': 28.35, 'lb': 453.6,
    'avuç': 30.0,  # handful ≈ 30g
}

_MEAL_MAP = {
    'breakfast': 'Breakfast', 'morning': 'Breakfast', 'brekky': 'Breakfast', 'brunch': 'Breakfast',
    'lunch': 'Lunch', 'noon': 'Lunch', 'midday': 'Lunch',
    'dinner': 'Dinner', 'supper': 'Dinner', 'evening': 'Dinner',
    'snack': 'Snack', 'snacking': 'Snack',
    # Turkish
    'kahvaltı': 'Breakfast', 'sabah': 'Breakfast',
    'öğle': 'Lunch', 'öğlen': 'Lunch',
    'akşam': 'Dinner',
    'atıştırmalık': 'Snack', 'ara öğün': 'Snack',
}

# Words that are never food names
_SKIP = {
    'i', 'had', 'ate', 'drank', 'eaten', 'have', 'just', 'also', 'today',
    'some', 'the', 'and', 'with', 'for', 'at', 'plus', 'my', 'bit',
    'yedim', 'içtim', 'bugün', 've', 'ile', 'olan', 'aldım',
}

# Cooking adjectives — keep them as modifiers to improve match quality
_COOKING_ADJ = {
    'fried', 'grilled', 'baked', 'boiled', 'scrambled', 'cooked',
    'roasted', 'steamed', 'raw', 'fresh', 'frozen', 'smoked', 'dried',
    'whole', 'skimmed', 'low-fat', 'greek',
}

# ---------------------------------------------------------------------------
# spaCy lazy load
# ---------------------------------------------------------------------------
_nlp = None

def _get_nlp():
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy
        _nlp = spacy.load('en_core_web_sm')
        log.info('spaCy en_core_web_sm loaded')
    except (OSError, ImportError) as e:
        log.warning('spaCy unavailable (%s) — using regex-only parser', e)
        _nlp = False  # sentinel: tried and failed
    return _nlp


# ---------------------------------------------------------------------------
# Quantity / unit / food extraction
# ---------------------------------------------------------------------------

def _parse_number(s: str) -> float:
    """Parse int, decimal or fraction string to float."""
    s = s.replace(',', '.')
    if '/' in s:
        num, den = s.split('/', 1)
        return float(num) / float(den)
    return float(s)


# Regex fallback for when spaCy is unavailable
_QTY_RE = re.compile(
    r'(\d+(?:[.,]\d+)?(?:/\d+)?)'          # quantity: 1, 1.5, 1/2
    r'\s*'
    r'(g|gr|grams?|kg|ml|l\b|lt|cups?|tbsps?|tablespoons?|tsps?|teaspoons?'
    r'|pieces?|slices?|servings?|glasses?|oz|lb|adet|dilim|porsiyon|bardak|avuç)?'
    r'\s*(?:of\s+)?'
    r'([a-zA-ZğüşıöçĞÜŞİÖÇ][a-zA-ZğüşıöçĞÜŞİÖÇ ]{1,40})',
    re.IGNORECASE,
)


def _mentions_regex(text: str) -> list[dict]:
    lower = text.lower()
    results = []
    seen = set()
    for m in _QTY_RE.finditer(lower):
        if m.start() in seen:
            continue
        seen.add(m.start())

        raw_qty = m.group(1)
        raw_unit = (m.group(2) or '').strip().lower()
        food_text = ' '.join(
            w for w in (m.group(3) or '').strip().split()
            if w not in _SKIP
        )
        if not food_text:
            continue

        try:
            qty = _parse_number(raw_qty)
        except ValueError:
            qty = 1.0

        if raw_unit in _UNIT_MULTIPLIERS:
            qty *= _UNIT_MULTIPLIERS[raw_unit]
        unit = _UNIT_MAP.get(raw_unit, raw_unit or 'serving')

        results.append({'food_text': food_text, 'quantity': qty, 'unit': unit})
    return results


def _mentions_spacy(text: str, nlp) -> list[dict]:
    doc = nlp(text.lower())
    results = []
    used = set()  # token indices already consumed

    tokens = list(doc)
    n = len(tokens)
    i = 0

    while i < n:
        if i in used:
            i += 1
            continue

        tok = tokens[i]

        # Detect quantity token (numeric or word-number)
        qty = None
        if tok.like_num:
            try:
                qty = _parse_number(tok.text)
            except ValueError:
                i += 1
                continue
        elif tok.lower_ in _WORD_NUMBERS:
            qty = _WORD_NUMBERS[tok.lower_]
        else:
            i += 1
            continue

        used.add(i)
        i += 1

        # Optional unit
        raw_unit = None
        if i < n and tokens[i].lower_ in _UNIT_MAP:
            raw_unit = tokens[i].lower_
            if raw_unit in _UNIT_MULTIPLIERS:
                qty *= _UNIT_MULTIPLIERS[raw_unit]
            used.add(i)
            i += 1

        # Skip filler words
        while i < n and tokens[i].lower_ in ('of', 'the', 'a', 'an', 'some'):
            used.add(i)
            i += 1

        # Collect food noun phrase (up to 5 tokens)
        food_parts = []
        for j in range(i, min(i + 5, n)):
            t = tokens[j]
            if t.lower_ in (',', 'and', 'with', 'for', 'at', 'plus', 'or'):
                break
            if t.pos_ == 'VERB' and t.lower_ not in _COOKING_ADJ:
                break
            if t.lower_ in _SKIP:
                continue
            if t.is_punct:
                break
            # Use lemma so "eggs" → "egg", "almonds" → "almond"
            food_parts.append(t.lemma_.lower())
            used.add(j)

        if food_parts:
            unit = _UNIT_MAP.get(raw_unit, raw_unit or 'serving')
            results.append({
                'food_text': ' '.join(food_parts),
                'quantity': qty,
                'unit': unit,
            })

    # Second pass: noun chunks not yet covered (no quantity given)
    covered_words = {w for m in results for w in m['food_text'].split()}
    for chunk in doc.noun_chunks:
        words = [t.lower_ for t in chunk if not t.is_stop or t.lower_ in _COOKING_ADJ]
        words = [w for w in words if w not in _SKIP and not w.isnumeric() and len(w) > 1]
        if not words:
            continue
        food_text = ' '.join(words)
        # Skip if all words already covered or if clearly not a food
        if all(w in covered_words for w in words):
            continue
        if any(bad in food_text for bad in ('today', 'yesterday', 'morning', 'meal', 'day')):
            continue
        results.append({'food_text': food_text, 'quantity': None, 'unit': None})

    return results


def extract_mentions(text: str) -> list[dict]:
    """Extract (food_text, quantity, unit) mentions from natural language."""
    nlp = _get_nlp()
    if nlp:
        mentions = _mentions_spacy(text, nlp)
        if not mentions:                     # spaCy found nothing → try regex
            mentions = _mentions_regex(text)
    else:
        mentions = _mentions_regex(text)
    return mentions


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

def fuzzy_match(food_text: str, db_names: list[str], threshold: int = 55) -> tuple[int, float]:
    """
    Match food_text against db_names using rapidfuzz token_set_ratio.
    Returns (index, score) or (-1, 0) if below threshold.
    token_set_ratio handles word-order differences and partial names well.
    """
    if not food_text or not db_names:
        return -1, 0.0
    try:
        from rapidfuzz import process as rfp, fuzz as rff
        result = rfp.extractOne(
            food_text, db_names,
            scorer=rff.token_set_ratio,
            score_cutoff=threshold,
        )
        if result is None:
            return -1, 0.0
        _matched, score, idx = result
        return idx, float(score)
    except ImportError:
        # No rapidfuzz — plain substring fallback
        ft = food_text.lower()
        for idx, name in enumerate(db_names):
            nl = name.lower()
            if ft in nl or nl in ft:
                return idx, 70.0
        return -1, 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_meal(text: str) -> str:
    lower = text.lower()
    for kw, label in _MEAL_MAP.items():
        if kw in lower:
            return label
    return 'Snack'


def parse_and_match(text: str, food_db: list[dict]) -> list[dict]:
    """
    Full pipeline: natural language → matched food entries with scaled macros.

    food_db items must have:
      id, name, protein, fat, carbs, calories, default_serving, serving_unit

    Returns list of dicts compatible with FoodEntry / chat _execute_log schema.
    """
    if not food_db:
        return []

    meal = detect_meal(text)
    mentions = extract_mentions(text)
    if not mentions:
        return []

    db_names = [f['name'].lower() for f in food_db]
    # Also build lemmatized first-word index for better matching
    # e.g. "Egg, whole, cooked" → "egg" as primary key
    db_first_words = [n.split(',')[0].split()[0] for n in db_names]
    results = []
    seen_ids: set = set()

    for mention in mentions:
        idx, score = fuzzy_match(mention['food_text'], db_names)
        # If full-name match is weak, try matching just the first word of each DB entry
        # e.g. "scrambled egg" weak against "Egg, whole, cooked" full name,
        # but strong against first-word "egg"
        if score < 70:
            idx2, score2 = fuzzy_match(mention['food_text'], db_first_words, threshold=65)
            if score2 > score:
                idx, score = idx2, score2
        if idx < 0:
            continue

        food = food_db[idx]
        fid = food['id']
        if fid in seen_ids:
            continue
        seen_ids.add(fid)

        quantity = mention['quantity']
        unit = mention['unit']

        if quantity is None:
            quantity = food.get('default_serving') or 100.0
            unit = food.get('serving_unit') or 'g'

        # Macros in DB are per 100 g/ml
        if unit in ('g', 'ml'):
            factor = quantity / 100.0
        else:
            default_g = float(food.get('default_serving') or 100)
            factor = (quantity * default_g) / 100.0

        results.append({
            'food_name':     food['name'],
            'saved_food_id': fid,
            'protein':       round(food['protein']  * factor, 1),
            'fat':           round(food['fat']       * factor, 1),
            'carbs':         round(food['carbs']     * factor, 1),
            'calories':      round(food['calories']  * factor, 1),
            'serving_size':  quantity,
            'serving_unit':  unit,
            'meal_type':     meal,
            'match_score':   round(score, 1),
        })

    return results


def is_available() -> bool:
    """Return True if spaCy model and rapidfuzz are both installed."""
    try:
        import spacy  # noqa: F401
        spacy.load('en_core_web_sm')
    except (ImportError, OSError):
        return False
    try:
        import rapidfuzz  # noqa: F401
    except ImportError:
        return False
    return True
