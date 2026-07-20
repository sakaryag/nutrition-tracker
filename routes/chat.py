"""
POST /api/chat
Nutrition chatbot backend.

Flow:
  1. Extract candidate food names from the user message (simple tokenisation).
  2. Search the food DB for each candidate (reuse existing SavedFood search).
  3. Build a system prompt that contains:
       - today's macro totals vs targets
       - the top food matches found
  4. Send message history + system prompt to Ollama (local) or Anthropic (if key set).
  5. Parse the model response for a structured action block, execute it,
     and return both the natural-language reply and any logged entries.

Model response format (inside ```json ... ```):
  {
    "action": "log" | "none",
    "entries": [
      {
        "food_name": "Yulaf",
        "protein": 5.0, "fat": 2.0, "carbs": 27.0, "calories": 150,
        "serving_size": 80, "serving_unit": "g",
        "meal_type": "Breakfast",
        "saved_food_id": 42          // optional
      }
    ],
    "reply": "Yulaf 80g kaydedildi — 150 kcal."
  }
"""
import json
import re
import os
import logging
from datetime import date, datetime
from flask import Blueprint, jsonify, request, current_app, session
from sqlalchemy import or_
from models import db
from models.food_entry import FoodEntry
from models.saved_food import SavedFood
from models.daily_target import DailyTarget
from routes.auth import current_user_id

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# Ollama kept for optional use, but local_model is the primary offline backend
OLLAMA_URL   = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.1')

def _anthropic_key() -> str:
    """Read ANTHROPIC_API_KEY from environment or .env file."""
    # Check OS environment first (works on Railway, Docker, etc.)
    key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if key:
        return key
    # Fallback: read from .env file for local dev
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    try:
        with open(os.path.normpath(env_path), encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or '=' not in line:
                    continue
                k, _, v = line.partition('=')
                if k.strip() == 'ANTHROPIC_API_KEY':
                    return v.strip()
    except OSError:
        pass
    return ''


# ---------------------------------------------------------------------------
# Food search helper
# ---------------------------------------------------------------------------
_TR_EN = {
    'yumurta': 'egg', 'süt': 'milk', 'sut': 'milk', 'ekmek': 'bread',
    'tost': 'bread', 'tavuk': 'chicken', 'et': 'beef', 'balık': 'fish',
    'balik': 'fish', 'pirinç': 'rice', 'princ': 'rice', 'pilav': 'rice',
    'makarna': 'pasta', 'peynir': 'cheese', 'yoğurt': 'yogurt',
    'yogurt': 'yogurt', 'muz': 'banana', 'elma': 'apple', 'portakal': 'orange',
    'domates': 'tomato', 'salatalık': 'cucumber', 'salatalik': 'cucumber',
    'havuç': 'carrot', 'havuc': 'carrot', 'patates': 'potato',
    'yulaf': 'oat', 'kahve': 'coffee', 'çay': 'tea', 'cay': 'tea',
    'meyve': 'fruit', 'sebze': 'vegetable', 'zeytinyağı': 'olive oil',
    'zeytinyagi': 'olive oil', 'zeytin': 'olive', 'fındık': 'hazelnut',
    'findik': 'hazelnut', 'ceviz': 'walnut', 'badem': 'almond',
    'tereyağı': 'butter', 'tereyagi': 'butter', 'yağ': 'oil',
    'şeker': 'sugar', 'seker': 'sugar', 'bal': 'honey',
    'mercimek': 'lentil', 'fasulye': 'bean', 'nohut': 'chickpea',
    'salam': 'salami', 'sosis': 'sausage', 'jambon': 'ham',
    'ton': 'tuna', 'somon': 'salmon', 'karides': 'shrimp',
    'ispanak': 'spinach', 'marul': 'lettuce', 'brokoli': 'broccoli',
    'soğan': 'onion', 'sogan': 'onion', 'sarımsak': 'garlic',
    'sarımsak': 'garlic', 'biber': 'pepper', 'patlıcan': 'eggplant',
    'patlican': 'eggplant', 'kabak': 'zucchini', 'mısır': 'corn',
    'misir': 'corn', 'yer fıstığı': 'peanut', 'fıstık': 'peanut',
    'çikolata': 'chocolate', 'cikolata': 'chocolate',
    'dondurma': 'ice cream', 'kek': 'cake', 'bisküvi': 'cookie',
    'biskuvi': 'cookie', 'kraker': 'cracker',
    'portakal suyu': 'orange juice', 'elma suyu': 'apple juice',
    'su': 'water', 'ayran': 'ayran', 'kola': 'cola',
    'krema': 'cream', 'yoğurt': 'yogurt',
}


def _search_foods(query: str, lang: str = 'en', limit: int = 4):
    if not query or len(query) < 2:
        return []
    # If Turkish word has a known English equivalent, search that too
    en_query = _TR_EN.get(query.lower(), query)
    filters = [SavedFood.name.ilike(f'%{en_query}%')]
    if en_query != query:
        filters.append(SavedFood.name.ilike(f'%{query}%'))
    if SavedFood.name_tr is not None:
        filters.append(SavedFood.name_tr.ilike(f'%{query}%'))

    from sqlalchemy import case as sa_case
    name_col = SavedFood.name_tr if lang == 'tr' else SavedFood.name
    relevance = sa_case(
        (SavedFood.name.ilike(en_query),          0),  # exact match
        (SavedFood.name.ilike(f'{en_query} %'),   1),  # starts with
        (SavedFood.name.ilike(f'{en_query},%'),   1),
        (SavedFood.name.ilike(f'% {en_query} %'), 2),  # whole word in middle
        else_=3,
    )
    foods = (
        SavedFood.query
        .filter_by(is_archived=False)
        .filter(or_(*filters))
        .order_by(relevance, SavedFood.name)
        .limit(limit)
        .all()
    )
    return [
        {
            'id': f.id,
            'name': f.name,
            'name_tr': f.name_tr or f.name,
            'protein': f.protein,
            'fat': f.fat,
            'carbs': f.carbs,
            'calories': f.calories,
            'default_serving': f.default_serving,
            'serving_unit': f.serving_unit,
        }
        for f in foods
    ]


# ---------------------------------------------------------------------------
# Extract candidate tokens from user message for DB lookup
# ---------------------------------------------------------------------------
_STOP_WORDS = {
    'yedim', 'içtim', 'aldım', 'ekle', 'log', 'ate', 'drank', 'had', 'add',
    'gram', 'ml', 'cup', 'tsp', 'tbsp', 'piece', 'slice', 'serving',
    've', 'and', 'the', 'an', 'ile', 'bugün', 'today',
    'öğle', 'breakfast', 'lunch', 'dinner', 'snack',
    'tane', 'adet', 'dilim', 'porsiyon', 'bardak', 'kaşık',
}

def _extract_food_tokens(text: str):
    # Keep words ≥ 2 chars (catches "et", "su" etc.)
    words = re.findall(r"[a-zA-ZğüşıöçĞÜŞİÖÇ]{2,}", text.lower())
    tokens = [w for w in words if w not in _STOP_WORDS]
    # Also try bigrams (e.g. "yer fıstığı")
    bigrams = [tokens[i] + ' ' + tokens[i+1] for i in range(len(tokens)-1)]
    return list(dict.fromkeys(bigrams + tokens))[:10]


# ---------------------------------------------------------------------------
# Context: today's totals and target
# ---------------------------------------------------------------------------
def _today_context(uid, lang='en'):
    today = date.today()

    q = db.session.query(db.func.sum(FoodEntry.protein).label('p'),
                         db.func.sum(FoodEntry.fat).label('f'),
                         db.func.sum(FoodEntry.carbs).label('c'),
                         db.func.sum(FoodEntry.calories).label('k')
                         ).filter(FoodEntry.entry_date == today)
    if uid is not None:
        q = q.filter(FoodEntry.user_id == uid)
    row = q.one()
    totals = {
        'protein': round(row.p or 0, 1),
        'fat': round(row.f or 0, 1),
        'carbs': round(row.c or 0, 1),
        'calories': round(row.k or 0, 1),
    }

    tq = DailyTarget.query.filter(DailyTarget.effective_from <= today)
    if uid is not None:
        tq = tq.filter(DailyTarget.user_id == uid)
    target_row = tq.order_by(DailyTarget.effective_from.desc()).first()
    target = {
        'protein': target_row.protein if target_row else current_app.config.get('DEFAULT_PROTEIN_TARGET', 150),
        'fat': target_row.fat if target_row else current_app.config.get('DEFAULT_FAT_TARGET', 65),
        'carbs': target_row.carbs if target_row else current_app.config.get('DEFAULT_CARBS_TARGET', 250),
        'calories': target_row.calories if target_row else current_app.config.get('DEFAULT_CALORIES_TARGET', 2200),
    }

    remaining = {k: round(target[k] - totals[k], 1) for k in totals}
    return totals, target, remaining


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SYSTEM_TR = """Sen bir beslenme asistanısın. Kullanıcının yediği yiyecekleri kayıt etmesine yardım et.

Bugünkü makro durumu:
{context}

Veritabanında bulunan eşleşen yiyecekler:
{foods}

KURALLAR:
- Kullanıcı yiyecek bildirdiğinde, yukarıdaki DB sonuçlarından en uygun olanı seç.
- Makroları DB değerlerinden orantıla (porsiyon * (DB_değer / 100)).
- Sadece mantıklı öğün tipini ata (sabah→Breakfast, öğle→Lunch, akşam→Dinner, ara→Snack).
- Türkçe cevap ver.
- Cevabının sonunda, yiyecek kaydı varsa şu formatta bir JSON bloğu ekle:

```json
{{
  "action": "log",
  "entries": [
    {{
      "food_name": "Yulaf",
      "protein": 5.0, "fat": 2.0, "carbs": 27.0, "calories": 150,
      "serving_size": 80, "serving_unit": "g",
      "meal_type": "Breakfast",
      "saved_food_id": 42
    }}
  ],
  "reply": "Kısa özet mesaj"
}}
```

Kayıt yoksa action'ı "none" yap ve entries'i boş liste yap.
"""

_SYSTEM_EN = """You are a nutrition assistant. Help the user log what they eat.

Today's macro status:
{context}

Matching foods found in database:
{foods}

RULES:
- When the user reports eating food, pick the best match from the DB results above.
- Scale macros from DB per-100g values (portion * DB_value / 100).
- Assign a sensible meal type based on time cues (morning→Breakfast, noon→Lunch, evening→Dinner, else→Snack).
- Reply in English.
- At the end of your response, if logging food, include a JSON block:

```json
{{
  "action": "log",
  "entries": [
    {{
      "food_name": "Oats",
      "protein": 5.0, "fat": 2.0, "carbs": 27.0, "calories": 150,
      "serving_size": 80, "serving_unit": "g",
      "meal_type": "Breakfast",
      "saved_food_id": 42
    }}
  ],
  "reply": "Short summary message"
}}
```

If not logging, set action to "none" and entries to [].
"""


def _build_system(uid, lang, food_tokens):
    totals, target, remaining = _today_context(uid, lang)

    ctx_lines = [
        f"Protein:  {totals['protein']}g eaten / {target['protein']}g target ({remaining['protein']}g left)",
        f"Fat:      {totals['fat']}g eaten / {target['fat']}g target ({remaining['fat']}g left)",
        f"Carbs:    {totals['carbs']}g eaten / {target['carbs']}g target ({remaining['carbs']}g left)",
        f"Calories: {totals['calories']} eaten / {target['calories']} target ({remaining['calories']} left)",
        f"Date: {date.today().isoformat()}",
    ]

    all_matches = {}
    for token in food_tokens:
        for f in _search_foods(token, lang=lang, limit=3):
            all_matches[f['id']] = f
    food_lines = []
    for f in list(all_matches.values())[:10]:
        food_lines.append(
            f"  id={f['id']} | {f['name_tr']} ({f['name']}) | "
            f"per 100{f['serving_unit']}: P={f['protein']}g F={f['fat']}g C={f['carbs']}g "
            f"{f['calories']}kcal | default_serving={f['default_serving']}{f['serving_unit']}"
        )

    template = _SYSTEM_TR if lang == 'tr' else _SYSTEM_EN
    return template.format(
        context='\n'.join(ctx_lines),
        foods='\n'.join(food_lines) if food_lines else '  (no matches found)',
    )


# ---------------------------------------------------------------------------
# LLM backends
# ---------------------------------------------------------------------------
def _call_ollama(messages, system_prompt):
    import urllib.request
    payload = json.dumps({
        'model': OLLAMA_MODEL,
        'messages': [{'role': 'system', 'content': system_prompt}] + messages,
        'stream': False,
    }).encode()
    req = urllib.request.Request(
        f'{OLLAMA_URL}/api/chat',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data['message']['content']
    except Exception as e:
        raise RuntimeError(f'Ollama error: {e}')


def _call_anthropic(messages, system_prompt, api_key: str = ''):
    import urllib.request
    key = api_key or _anthropic_key()
    # Anthropic requires strictly alternating user/assistant roles.
    # Merge consecutive same-role messages to avoid 400 errors.
    formatted = []
    for m in messages:
        if formatted and formatted[-1]['role'] == m['role']:
            formatted[-1]['content'] += '\n' + m['content']
        else:
            formatted.append({'role': m['role'], 'content': m['content']})
    # Must start with user role
    if formatted and formatted[0]['role'] != 'user':
        formatted = formatted[1:]
    payload = json.dumps({
        'model': 'claude-haiku-4-5-20251001',
        'max_tokens': 1024,
        'system': system_prompt,
        'messages': formatted,
    }).encode()
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'x-api-key': key,
            'anthropic-version': '2023-06-01',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data['content'][0]['text']
    except Exception as e:
        raise RuntimeError(f'Anthropic error: {e}')


def _get_reply(messages, system_prompt, user_key: str = ''):
    key = user_key.strip() or _anthropic_key()
    if key:
        return _call_anthropic(messages, system_prompt, api_key=key)
    # Ollama is optional — try only if explicitly configured
    if os.getenv('OLLAMA_ENABLED', '').lower() in ('1', 'true', 'yes') and _ollama_available():
        return _call_ollama(messages, system_prompt)
    return None  # signal: use local NLP model / rule-based fallback


# ---------------------------------------------------------------------------
# Parse JSON action from model reply
# ---------------------------------------------------------------------------
def _parse_action(text: str):
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _strip_json_block(text: str) -> str:
    return re.sub(r'```json\s*.*?\s*```', '', text, flags=re.DOTALL).strip()


# ---------------------------------------------------------------------------
# Rule-based fallback (no LLM required)
# ---------------------------------------------------------------------------
_AMOUNT_RE = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*'
    r'(g|gr|gram|ml|cup|bardak|piece|adet|slice|dilim|serving|porsiyon)',
    re.IGNORECASE,
)

def _guess_meal_type(text: str, lang: str) -> str:
    t = text.lower()
    if any(w in t for w in ('breakfast', 'morning', 'sabah', 'kahvaltı')):
        return 'Breakfast'
    if any(w in t for w in ('lunch', 'noon', 'öğle')):
        return 'Lunch'
    if any(w in t for w in ('dinner', 'evening', 'akşam')):
        return 'Dinner'
    return 'Snack'

_UNIT_NORM = {'gr': 'g', 'gram': 'g', 'bardak': 'cup',
              'adet': 'piece', 'dilim': 'slice', 'porsiyon': 'serving'}

def _rule_based_chat(last_msg: str, uid, lang: str, food_tokens: list) -> dict:
    """
    Smart food parser using local NLP model (spaCy + rapidfuzz) when available,
    falling back to token search + regex amounts if not.
    """
    # ---- Try local NLP model first ----
    try:
        from local_model import parse_and_match as _nlp_parse
        # Build a broad candidate pool: token search + top foods by name
        from models.saved_food import SavedFood as _SF
        candidate_map: dict = {}

        # Token-based DB search (existing logic, fast)
        for token in food_tokens:
            for f in _search_foods(token, lang=lang, limit=5):
                candidate_map[f['id']] = f

        # If message mentions no recognisable tokens, pull top 300 foods for
        # fuzzy matching to have a chance at something obscure
        if not candidate_map:
            rows = _SF.query.filter_by(is_archived=False).limit(300).all()
            for r in rows:
                candidate_map[r.id] = {
                    'id': r.id, 'name': r.name, 'name_tr': r.name_tr,
                    'protein': r.protein, 'fat': r.fat,
                    'carbs': r.carbs, 'calories': r.calories,
                    'default_serving': r.default_serving,
                    'serving_unit': r.serving_unit,
                }
        else:
            # Ensure name_tr is included for Turkish matching
            for fid, f in candidate_map.items():
                if 'name_tr' not in f:
                    f['name_tr'] = None

        food_db = list(candidate_map.values())
        results = _nlp_parse(last_msg, food_db, lang=lang)

        if results:
            names = [e['food_name'] for e in results]
            total_kcal = round(sum(e['calories'] for e in results))
            if lang == 'tr':
                # Show per-item details in Turkish
                details = ', '.join(
                    f"{e['food_name']} {e['serving_size']}{e['serving_unit']} ({e['calories']} kcal)"
                    for e in results
                )
                reply = f"{details} kaydedildi — toplam {total_kcal} kcal."
            else:
                details = ', '.join(
                    f"{e['food_name']} {e['serving_size']}{e['serving_unit']} ({e['calories']} kcal)"
                    for e in results
                )
                reply = f"Logged: {details} — {total_kcal} kcal total."
            return {'action': 'log', 'entries': results, 'reply': reply}

    except Exception as exc:
        log.warning('local_model failed (%s) — using regex fallback', exc)

    # ---- Regex / token fallback (original logic) ----
    amounts = [(float(v.replace(',', '.')), _UNIT_NORM.get(u.lower(), u.lower()))
               for v, u in _AMOUNT_RE.findall(last_msg)]

    all_matches: dict = {}
    for token in food_tokens:
        for f in _search_foods(token, lang=lang, limit=3):
            all_matches[f['id']] = f

    if not all_matches:
        if lang == 'tr':
            reply = 'Veritabanında eşleşen besin bulunamadı. Daha açık bir şekilde belirtir misiniz?'
        else:
            reply = 'No matching food found in the database. Could you be more specific?'
        return {'action': 'none', 'entries': [], 'reply': reply}

    meal_type = _guess_meal_type(last_msg, lang)
    entries = []
    for i, food in enumerate(list(all_matches.values())[:3]):
        if i < len(amounts):
            amount_val, unit = amounts[i]
        else:
            amount_val = food['default_serving'] or 100
            unit = food['serving_unit'] or 'g'
        factor = amount_val / 100
        entries.append({
            'food_name': food['name_tr'] if lang == 'tr' else food['name'],
            'protein':   round(food['protein']  * factor, 1),
            'fat':       round(food['fat']       * factor, 1),
            'carbs':     round(food['carbs']     * factor, 1),
            'calories':  round(food['calories']  * factor, 1),
            'serving_size': amount_val,
            'serving_unit': unit,
            'meal_type':    meal_type,
            'saved_food_id': food['id'],
        })

    names = [e['food_name'] for e in entries]
    total_kcal = round(sum(e['calories'] for e in entries))
    if lang == 'tr':
        reply = f"{', '.join(names)} kaydedildi — toplam {total_kcal} kcal."
    else:
        reply = f"Logged {', '.join(names)} — {total_kcal} kcal total."
    return {'action': 'log', 'entries': entries, 'reply': reply}


def _local_model_available() -> bool:
    """True if spaCy + rapidfuzz are both installed."""
    try:
        from local_model import is_available
        return is_available()
    except ImportError:
        return False


def _ollama_available() -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f'{OLLAMA_URL}/api/tags', timeout=2):
            return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Execute log action
# ---------------------------------------------------------------------------
def _execute_log(entries_data, uid):
    now = datetime.utcnow()
    today = date.today()
    logged = []
    for ed in entries_data:
        food_name = ed.get('food_name', '').strip()
        if not food_name:
            continue
        try:
            protein  = float(ed.get('protein', 0))
            fat      = float(ed.get('fat', 0))
            carbs    = float(ed.get('carbs', 0))
            calories = float(ed.get('calories', protein*4 + fat*9 + carbs*4))
        except (TypeError, ValueError):
            continue
        entry = FoodEntry(
            food_name=food_name,
            protein=round(protein, 1),
            fat=round(fat, 1),
            carbs=round(carbs, 1),
            calories=round(calories, 1),
            meal_type=ed.get('meal_type', 'Snack'),
            serving_size=float(ed['serving_size']) if ed.get('serving_size') else None,
            serving_unit=ed.get('serving_unit', 'g'),
            saved_food_id=int(ed['saved_food_id']) if ed.get('saved_food_id') else None,
            user_id=uid,
            entry_date=today,
            entry_time=now.time(),
        )
        db.session.add(entry)
        logged.append(food_name)
    if logged:
        db.session.commit()
    return logged


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------
@chat_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


@chat_bp.route('', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    messages   = data.get('messages', [])   # [{role, content}, ...]
    lang       = data.get('lang', 'en')
    uid        = current_user_id()
    user_key   = data.get('api_key', '').strip()

    if not messages:
        return jsonify({'error': 'messages required'}), 400

    last_user_msg = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), '')
    food_tokens   = _extract_food_tokens(last_user_msg)
    system_prompt = _build_system(uid, lang, food_tokens)

    try:
        raw_reply = _get_reply(messages, system_prompt, user_key=user_key)
    except RuntimeError as e:
        return jsonify({'error': str(e), 'reply': str(e), 'logged': []}), 502

    if raw_reply is None:
        # No LLM available — use rule-based parser
        action = _rule_based_chat(last_user_msg, uid, lang, food_tokens)
        logged = []
        if action.get('action') == 'log' and action.get('entries'):
            logged = _execute_log(action['entries'], uid)
        return jsonify({'reply': action['reply'], 'logged': logged, 'raw': None})

    action = _parse_action(raw_reply)
    display_reply = _strip_json_block(raw_reply)
    if action and action.get('reply'):
        display_reply = action['reply']

    logged = []
    if action and action.get('action') == 'log' and action.get('entries'):
        logged = _execute_log(action['entries'], uid)

    return jsonify({
        'reply': display_reply,
        'logged': logged,
        'raw': raw_reply,
    })


@chat_bp.route('/status', methods=['GET'])
def status():
    """Check which backend is active."""
    has_user_key = request.args.get('has_user_key') == '1'
    if has_user_key or _anthropic_key():
        return jsonify({'backend': 'anthropic', 'model': 'claude-haiku-4-5-20251001', 'ready': True})
    nlp_avail = _local_model_available()
    if nlp_avail:
        return jsonify({'backend': 'local-nlp', 'model': 'spaCy + rapidfuzz', 'ready': True})
    # Debug: report why local-nlp is unavailable
    try:
        import spacy  # noqa: F401
        spacy_ok = True
    except ImportError:
        spacy_ok = False
    try:
        import rapidfuzz  # noqa: F401
        rf_ok = True
    except ImportError:
        rf_ok = False
    try:
        import spacy as _sp
        _sp.load('en_core_web_sm')
        model_ok = True
    except Exception as e:
        model_ok = str(e)
    if os.getenv('OLLAMA_ENABLED', '').lower() in ('1', 'true', 'yes') and _ollama_available():
        import urllib.request
        try:
            with urllib.request.urlopen(f'{OLLAMA_URL}/api/tags', timeout=3) as r:
                data = json.loads(r.read())
                models = [m['name'] for m in data.get('models', [])]
                ready = any(OLLAMA_MODEL in m for m in models)
                return jsonify({'backend': 'ollama', 'model': OLLAMA_MODEL, 'models': models, 'ready': ready})
        except Exception:
            pass
    return jsonify({
        'backend': 'rule-based', 'model': None, 'ready': True,
        '_debug': {'spacy': spacy_ok, 'rapidfuzz': rf_ok, 'en_core_web_sm': model_ok},
    })
