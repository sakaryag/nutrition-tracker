"""Token-authenticated voice/automation API (Alexa, Home Assistant, curl).

Auth is `Authorization: Bearer nt_...` only; the session cookie is deliberately ignored
so cross-site requests can't ride a logged-in browser session. All state lives in the DB
(VoiceLog, AiFoodCache) so it works on stateless, scale-to-zero hosts.
"""
import base64
import hmac
import json
import logging
import math
import re
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, current_app, g, jsonify, request

from local_model import detect_meal, extract_mentions, fuzzy_match
from models import db
from models.api_token import ApiToken, TOKEN_PREFIX, hash_token
from models.food_entry import FoodEntry
from models.saved_food import SavedFood
from models.voice_log import AiFoodCache, VoiceLog
from routes.chat import _TR_EN, _extract_food_tokens, _search_foods
from routes.summary import _get_target, _totals_for_date
from utils import gemini

log = logging.getLogger(__name__)

voice_bp = Blueprint('voice_api', __name__, url_prefix='/api/v1')

MAX_TEXT = 500
MAX_BODY = 8192
MAX_AUDIO_BODY = 8 * 1024 * 1024
# Normalised MIME types Gemini accepts for inline audio.
_AUDIO_MIME = {
    'audio/wav': 'audio/wav', 'audio/x-wav': 'audio/wav', 'audio/wave': 'audio/wav',
    'audio/aiff': 'audio/aiff', 'audio/x-aiff': 'audio/aiff',
    'audio/mpeg': 'audio/mp3', 'audio/mp3': 'audio/mp3',
    'audio/aac': 'audio/aac', 'audio/ogg': 'audio/ogg', 'audio/flac': 'audio/flac',
    'audio/mp4': 'audio/mp4', 'audio/m4a': 'audio/mp4', 'audio/x-m4a': 'audio/mp4',
    'video/mp4': 'audio/mp4',
}
_AUDIO_EXT = {'wav': 'audio/wav', 'aif': 'audio/aiff', 'aiff': 'audio/aiff', 'mp3': 'audio/mp3',
              'aac': 'audio/aac', 'ogg': 'audio/ogg', 'flac': 'audio/flac', 'm4a': 'audio/mp4',
              'mp4': 'audio/mp4'}
MAX_MENTIONS = 10
DB_MATCH_THRESHOLD = 75
CACHE_DAYS = 30
VOICE_LOG_DAYS = 7
MEAL_TYPES = {'breakfast': 'Breakfast', 'lunch': 'Lunch', 'dinner': 'Dinner', 'snack': 'Snack'}
# Rough grams per household unit when the food has no g_per_unit.
_UNIT_GRAMS = {'cup': 240.0, 'glass': 200.0, 'tbsp': 15.0, 'tsp': 5.0}
_UNIT_RE = re.compile(r'^[A-Za-z]{1,20}$')


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _err(msg, status=400):
    return jsonify({'error': msg}), status


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@voice_bp.before_request
def token_auth():
    is_audio = (request.mimetype or '').startswith('multipart/')
    if request.content_length and request.content_length > (MAX_AUDIO_BODY if is_audio else MAX_BODY):
        return _err('payload_too_large', 413)
    header = request.headers.get('Authorization', '')
    scheme, _, token = header.partition(' ')
    token = token.strip()
    if scheme.lower() != 'bearer' or not token.startswith(TOKEN_PREFIX) or len(token) > 128:
        return _err('invalid_token', 401)
    token_hash = hash_token(token)
    row = ApiToken.query.filter_by(token_hash=token_hash).first()
    if row is None or row.revoked or not hmac.compare_digest(row.token_hash, token_hash):
        return _err('invalid_token', 401)
    # A token minted while auth was off must not become an anonymous key once auth is on.
    if current_app.config.get('AUTH_ENABLED') and row.user_id is None:
        return _err('invalid_token', 401)
    g.api_user_id = row.user_id
    g.token_ai_key = gemini.open_for_token(row.enc_gemini_key, token) if row.enc_gemini_key else ''
    now = _utcnow()
    if row.last_used_at is None or now - row.last_used_at >= timedelta(minutes=1):
        row.last_used_at = now
        db.session.commit()


def _gemini_key() -> str:
    supplied = (request.headers.get('X-Gemini-Key') or '').strip()
    if supplied and gemini.looks_like_key(supplied):
        return supplied
    return getattr(g, 'token_ai_key', '') or gemini.server_key()


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def _lang(value) -> str:
    return value if value in ('en', 'tr') else 'en'


def _parse_date(value):
    if value is None or value == '':
        return date.today()
    if not isinstance(value, str):
        raise ValueError
    return date.fromisoformat(value)


def _parse_meal(value):
    if value is None or value == '':
        return None
    if not isinstance(value, str) or value.strip().lower() not in MEAL_TYPES:
        raise ValueError
    return MEAL_TYPES[value.strip().lower()]


def _parse_number(value, lo, hi):
    if isinstance(value, bool):
        raise ValueError
    if isinstance(value, str):
        value = value.strip()
        if not value or len(value) > 20:
            raise ValueError
    n = float(value)
    if not math.isfinite(n) or n < lo or n > hi:
        raise ValueError
    return n


def _clamp(value, lo, hi, default=0.0):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return default
    if isinstance(value, bool) or not math.isfinite(n):
        return default
    return min(max(n, lo), hi)


def _normalize(phrase: str) -> str:
    phrase = re.sub(r'[^\w\s\-]', ' ', (phrase or '').lower())
    return ' '.join(phrase.split())[:200]


def _owned(query, model, uid):
    return query.filter(model.user_id.is_(None) if uid is None else model.user_id == uid)


# ---------------------------------------------------------------------------
# Speech helpers
# ---------------------------------------------------------------------------
def _num(n, lang) -> str:
    s = f'{round(n):,}'
    return s.replace(',', '.') if lang == 'tr' else s


def _join(items, lang) -> str:
    items = [i for i in items if i]
    if not items:
        return ''
    if len(items) == 1:
        return items[0]
    return ', '.join(items[:-1]) + (' ve ' if lang == 'tr' else ' and ') + items[-1]


def _short_name(name: str) -> str:
    return (name or '').split(',')[0].strip()


def _status_speech(d, totals, target, lang) -> str:
    eaten, goal = totals['calories'], target['calories']
    left = goal - eaten
    today = d == date.today()
    if lang == 'tr':
        when = 'Bugün' if today else f'{d.isoformat()} tarihinde'
        s = (f'{when} {_num(goal, lang)} kaloriden {_num(eaten, lang)} kalori aldın, '
             f'{_num(totals["protein"], lang)} gram protein. ')
        s += f'{_num(left, lang)} kalori kaldı.' if left >= 0 else f'Hedefi {_num(-left, lang)} kalori aştın.'
        return s
    when = "Today you've had" if today else f'On {d.isoformat()} you had'
    s = (f'{when} {_num(eaten, lang)} of {_num(goal, lang)} calories, '
         f'with {_num(totals["protein"], lang)} grams of protein. ')
    s += f'{_num(left, lang)} calories left.' if left >= 0 else f"You're {_num(-left, lang)} calories over."
    return s


# ---------------------------------------------------------------------------
# Food resolution
# ---------------------------------------------------------------------------
def _portion(m, grams_per_unit):
    """(grams eaten, serving_size, serving_unit) for a food with `grams_per_unit` per serving."""
    q, u = m['quantity'], m['unit']
    if q is None:
        return grams_per_unit, grams_per_unit, 'g'
    if u in ('g', 'ml'):
        return q, q, u
    return q * grams_per_unit, q, u or 'serving'


def _item(name, per100, grams, serving_size, serving_unit, source, phrase, saved_food_id=None):
    f = grams / 100.0
    return {
        'food_name': name[:200],
        'protein': round(per100['protein'] * f, 1),
        'fat': round(per100['fat'] * f, 1),
        'carbs': round(per100['carbs'] * f, 1),
        'calories': round(per100['calories'] * f, 1),
        'serving_size': round(serving_size, 2),
        'serving_unit': serving_unit,
        'saved_food_id': saved_food_id,
        'source': source,
        'phrase': phrase,
    }


def _from_cache(m, uid):
    cutoff = _utcnow() - timedelta(days=CACHE_DAYS)
    row = (_owned(AiFoodCache.query, AiFoodCache, uid)
           .filter(AiFoodCache.phrase == m['key'], AiFoodCache.created_at >= cutoff).first())
    if row is None:
        return None
    grams, size, unit = _portion(m, row.default_grams or 100.0)
    per100 = {'protein': row.protein, 'fat': row.fat, 'carbs': row.carbs, 'calories': row.calories}
    return _item(row.food_name, per100, grams, size, unit, 'cache', m['food_text'])


def _main_names(f):
    """Singular first segment of both the English and Turkish names ("Yumurta, tam, çiğ" -> "yumurta")."""
    return {_singular_phrase(n.split(',')[0]) for n in (f['name'], f.get('name_tr')) if n}


def _from_db(m, lang, strict=False):
    query = _singular_phrase(m['food_text'])
    targets = {query}
    if m['food_text'].lower() in _TR_EN:
        targets.add(_singular_phrase(_TR_EN[m['food_text'].lower()]))
    queries = list(targets)
    for tok in _extract_food_tokens(m['food_text'])[:6]:
        queries.append(tok)
        if tok in _TR_EN:
            queries.append(_TR_EN[tok])
    candidates = {}
    for q in dict.fromkeys(queries):
        for f in _search_foods(q, lang, limit=8):
            candidates.setdefault(f['id'], f)
    if not candidates:
        return None
    foods = list(candidates.values())

    # Prefer foods whose main name (EN or TR) is exactly the spoken food: "yumurta"/"eggs" ->
    # "Egg, whole, raw", never "Yumurtalı erişte" or "Omelet, cheese, 2 eggs".
    counted = m['quantity'] is not None and (m['unit'] or 'serving') not in ('g', 'ml')
    variant = (m.get('variant') or '').lower()
    exact = [i for i, f in enumerate(foods) if _main_names(f) & targets]
    if exact:
        idx = min(exact, key=lambda i: (
            0 if variant and variant in foods[i]['name'].lower() else 1,
            0 if counted and (foods[i].get('serving_unit') or 'g') not in ('g', 'ml') else 1,
            len(foods[i]['name'])))
        score = 100.0
    else:
        threshold = 90 if strict else DB_MATCH_THRESHOLD
        en = [f['name'].lower() for f in foods]
        tr = [(f.get('name_tr') or f['name']).lower() for f in foods]
        idx, score = fuzzy_match(query, en, threshold=threshold)
        idx2, score2 = fuzzy_match(query, tr, threshold=threshold)
        if score2 > score:
            idx, score = idx2, score2
        if idx < 0:
            return None
    food = foods[idx]
    row = db.session.get(SavedFood, food['id'])
    q, u = m['quantity'], m['unit']
    su = food.get('serving_unit') or 'g'
    weight_food = su in ('g', 'ml')
    ds = float(food.get('default_serving') or (100.0 if weight_food else 1.0))
    gpu = row.g_per_unit if row is not None and row.g_per_unit and row.g_per_unit > 1 else None
    if q is None:
        q, u = ds, su
    u = u or 'serving'
    hint = m.get('grams_hint') or 0

    # Weight foods store macros per 100 g; counted foods (piece/slice/serving) per default serving.
    if weight_food:
        if u in ('g', 'ml'):
            grams = q
        elif u in _UNIT_GRAMS:
            grams = q * _UNIT_GRAMS[u]
        else:
            grams = q * gpu if gpu else (hint or q * ds)
        factor = grams / 100.0
    else:
        if u in ('g', 'ml'):
            units = q / (gpu or 100.0)
        else:
            units = q
        factor = units / ds
    per100 = {k: float(food[k] or 0) for k in ('protein', 'fat', 'carbs', 'calories')}
    name = (food.get('name_tr') or food['name']) if lang == 'tr' else food['name']
    it = _item(name, per100, factor * 100.0, q, u, 'db', m['food_text'], food['id'])
    it['match_score'] = round(score, 1)
    return it


_AI_UNITS = {'piece', 'slice', 'serving', 'g', 'ml', 'cup', 'glass', 'tbsp', 'tsp'}


def _ai_parse(text, audio, lang, key):
    """One Gemini call: (voice note or dictated text) -> corrected sentence + structured items."""
    name_lang = 'Turkish' if lang == 'tr' else 'the language the user spoke'
    system = (
        'You convert a spoken food log into JSON. The input may contain speech-recognition '
        'mistakes and may be Turkish, English or mixed; fix obvious errors from context '
        "(e.g. 'to eggs'/'too eggs' -> 2 eggs, 'for' -> 4 when it is a quantity). Only include foods "
        'and drinks the user says they consumed; never invent items. Estimate typical nutrition values.'
    )
    instructions = (
        'Return JSON exactly like {"heard": <the sentence as you understood it>, '
        '"meal": "Breakfast"|"Lunch"|"Dinner"|"Snack"|null, '
        '"items": [{"food": <short food name in ' + name_lang + '>, '
        '"db_name": <generic singular English base food, e.g. "egg", "banana", "chicken breast">, '
        '"variant": <English preparation/variety word or null, e.g. "boiled">, '
        '"quantity": <number or null>, '
        '"unit": "piece"|"slice"|"serving"|"g"|"ml"|"cup"|"glass"|"tbsp"|"tsp"|null, '
        '"grams": <estimated total grams of this portion>, '
        '"per100": {"protein": <g>, "fat": <g>, "carbs": <g>, "calories": <kcal>}}]}.'
    )
    parts = []
    if audio:
        parts.append({'inlineData': {'mimeType': audio[1], 'data': base64.b64encode(audio[0]).decode()}})
        parts.append({'text': "The user's voice note is attached.\n" + instructions})
    else:
        parts.append({'text': f'User said: {json.dumps(text, ensure_ascii=False)}\n' + instructions})
    try:
        data = gemini.generate_json_parts(parts, key, system=system, timeout=20 if audio else 10)
    except (RuntimeError, ValueError) as e:
        log.warning('voice api gemini parse failed: %s', e)
        return None
    if not isinstance(data, dict) or not isinstance(data.get('items'), list):
        return None

    items = []
    for it in data['items'][:MAX_MENTIONS]:
        if not isinstance(it, dict):
            continue
        food = it.get('food') if isinstance(it.get('food'), str) else ''
        db_name = it.get('db_name') if isinstance(it.get('db_name'), str) else ''
        food, db_name = food.strip()[:120], db_name.strip()[:120]
        if not (food or db_name):
            continue
        q = it.get('quantity')
        q = _clamp(q, 0, 1000, default=None) if q is not None else None
        unit = it.get('unit') if it.get('unit') in _AI_UNITS else None
        if q is not None and unit is None:
            unit = 'serving'
        per = it.get('per100') if isinstance(it.get('per100'), dict) else {}
        per100 = {
            'protein': _clamp(per.get('protein'), 0, 100),
            'fat': _clamp(per.get('fat'), 0, 100),
            'carbs': _clamp(per.get('carbs'), 0, 100),
            'calories': _clamp(per.get('calories'), 0, 900),
        }
        if per100['calories'] == 0:
            per100['calories'] = min(900.0, per100['protein'] * 4 + per100['fat'] * 9 + per100['carbs'] * 4)
        variant = it.get('variant') if isinstance(it.get('variant'), str) else ''
        items.append({'food': food or db_name, 'db_name': db_name or food, 'variant': variant.strip()[:40],
                      'quantity': q, 'unit': unit, 'grams': _clamp(it.get('grams'), 0, 5000),
                      'per100': per100})
    heard = data.get('heard') if isinstance(data.get('heard'), str) else ''
    meal = data.get('meal') if data.get('meal') in MEAL_TYPES.values() else None
    return {'heard': heard.strip()[:MAX_TEXT], 'meal': meal, 'items': items}


def _resolve_ai_items(parsed, lang, uid):
    resolved, unresolved = [], []
    for it in parsed['items']:
        m = {'food_text': it['db_name'], 'quantity': it['quantity'], 'unit': it['unit'],
             'variant': it['variant'], 'grams_hint': it['grams'],
             'norm': _normalize(it['db_name']), 'key': _singular_phrase(it['db_name'])}
        r = _from_db(m, lang, strict=True)
        if r:
            r['phrase'] = it['food']
            resolved.append(r)
            continue
        if not any(it['per100'].values()):
            unresolved.append(it['food'])
            continue
        grams = it['grams'] or 100.0
        q, u = it['quantity'], it['unit']
        default_grams = grams / q if q and u not in ('g', 'ml') else grams
        _cache_upsert(uid, _singular_phrase(it['food']), {
            'food_name': it['food'], 'per100': it['per100'], 'default_grams': default_grams or 100.0})
        size, unit = (q, u) if q is not None else (grams, 'g')
        resolved.append(_item(it['food'], it['per100'], grams, size, unit, 'ai', it['food']))
    return resolved, unresolved


def _cache_upsert(uid, norm, ai):
    row = _owned(AiFoodCache.query, AiFoodCache, uid).filter(AiFoodCache.phrase == norm).first()
    if row is None:
        row = AiFoodCache(user_id=uid, phrase=norm)
        db.session.add(row)
    row.food_name = ai['food_name']
    row.protein = ai['per100']['protein']
    row.fat = ai['per100']['fat']
    row.carbs = ai['per100']['carbs']
    row.calories = ai['per100']['calories']
    row.default_grams = ai['default_grams']
    row.created_at = _utcnow()


def _cleanup(uid):
    now = _utcnow()
    _owned(VoiceLog.query, VoiceLog, uid).filter(
        VoiceLog.created_at < now - timedelta(days=VOICE_LOG_DAYS)).delete(synchronize_session=False)
    _owned(AiFoodCache.query, AiFoodCache, uid).filter(
        AiFoodCache.created_at < now - timedelta(days=CACHE_DAYS)).delete(synchronize_session=False)


def _singular(word: str) -> str:
    if len(word) <= 3 or word.endswith('ss'):
        return word
    if word.endswith('ies'):
        return word[:-3] + 'y'
    if word.endswith(('oes', 'ches', 'shes', 'xes', 'sses')):
        return word[:-2]
    if word.endswith('s'):
        return word[:-1]
    return word


def _singular_phrase(text: str) -> str:
    return ' '.join(_singular(w) for w in _normalize(text).split())


def _mentions(text):
    out, seen = [], set()
    for m in extract_mentions(text):
        ft = (m.get('food_text') or '').strip()
        norm = _normalize(ft)
        key = _singular_phrase(ft)
        if not norm or key in seen:
            continue
        seen.add(key)
        out.append({'food_text': ft, 'quantity': m.get('quantity'), 'unit': m.get('unit'),
                    'norm': norm, 'key': key})
    # Drop quantity-less mentions already covered by another mention ("2 eggs" + "eggs").
    out = [m for m in out if m['quantity'] is not None or not any(
        o is not m and set(m['key'].split()) <= set(o['key'].split()) for o in out)]
    out = out[:MAX_MENTIONS]
    if not out:
        norm = _normalize(text)
        if norm:
            out.append({'food_text': text.strip()[:200], 'quantity': None, 'unit': None,
                        'norm': norm, 'key': _singular_phrase(text)})
    return out


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@voice_bp.route('/log', methods=['POST'])
def log_food():
    audio = None
    if (request.mimetype or '').startswith('multipart/'):
        data = request.form.to_dict()
        if 'dry_run' in data:
            data['dry_run'] = data['dry_run'].strip().lower() in ('1', 'true', 'yes')
        f = request.files.get('audio')
        if f is not None:
            raw = f.read(MAX_AUDIO_BODY + 1)
            if len(raw) > MAX_AUDIO_BODY:
                return _err('payload_too_large', 413)
            ext = (f.filename or '').rsplit('.', 1)[-1].lower()
            mime = _AUDIO_MIME.get((f.mimetype or '').lower()) or _AUDIO_EXT.get(ext)
            if not mime or len(raw) < 500:
                return _err('Unsupported or empty audio (use m4a, wav, aiff, mp3, aac, ogg or flac)')
            audio = (raw, mime)
    else:
        data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _err('JSON body required')
    text = data.get('text') or ''
    if not isinstance(text, str):
        return _err('text must be a string')
    text = text.strip()
    if not text and not audio:
        return _err('text is required')
    if len(text) > MAX_TEXT:
        return _err(f'text must be at most {MAX_TEXT} characters')
    lang = _lang(data.get('lang'))
    try:
        explicit_meal = _parse_meal(data.get('meal_type'))
    except ValueError:
        return _err('meal_type must be Breakfast, Lunch, Dinner or Snack')
    try:
        d = _parse_date(data.get('date'))
    except ValueError:
        return _err('Invalid date format, use YYYY-MM-DD')
    dry_run = data.get('dry_run', False)
    if not isinstance(dry_run, bool):
        return _err('dry_run must be a boolean')

    uid = g.api_user_id
    _cleanup(uid)

    key = _gemini_key()
    parsed = _ai_parse(text, audio, lang, key) if key else None
    if audio and parsed is None:
        return _err('no_key' if not key else 'Could not understand the audio', 400 if not key else 502)

    if parsed is not None:
        heard = parsed['heard'] or text
        resolved, unresolved = _resolve_ai_items(parsed, lang, uid)
        meal = explicit_meal or parsed['meal'] or detect_meal(heard)
    else:
        heard = text
        meal = explicit_meal or detect_meal(text)
        resolved, unresolved = [], []
        for m in _mentions(text):
            it = _from_cache(m, uid) or _from_db(m, lang)
            if it:
                resolved.append(it)
            else:
                unresolved.append(m['food_text'])
    text = heard

    logged, entries = [], []
    now_t = datetime.now().time().replace(microsecond=0)
    for it in resolved:
        e = FoodEntry(
            food_name=it['food_name'], protein=it['protein'], fat=it['fat'], carbs=it['carbs'],
            calories=it['calories'], meal_type=meal, serving_size=it['serving_size'],
            serving_unit=it['serving_unit'], saved_food_id=it['saved_food_id'],
            entry_date=d, entry_time=now_t, user_id=uid,
        )
        entries.append((e, it))

    log_id = None
    if entries and not dry_run:
        for e, _ in entries:
            db.session.add(e)
        db.session.flush()
        vl = VoiceLog(user_id=uid, text=text, lang=lang, entry_ids=json.dumps([e.id for e, _ in entries]))
        db.session.add(vl)
        db.session.flush()
        log_id = vl.id
    db.session.commit()

    for e, it in entries:
        if dry_run:
            row = {k: it[k] for k in ('food_name', 'protein', 'fat', 'carbs', 'calories',
                                      'serving_size', 'serving_unit', 'saved_food_id')}
            row.update({'id': None, 'meal_type': meal, 'template_id': None,
                        'entry_date': d.isoformat(), 'entry_time': now_t.isoformat()})
        else:
            row = e.to_dict()
        row['source'] = it['source']
        row['phrase'] = it['phrase']
        logged.append(row)

    totals = _totals_for_date(d, uid)
    target = _get_target(d, uid)
    speech = _log_speech(logged, unresolved, totals, target, lang, dry_run)
    body = {'logged': logged, 'unresolved': unresolved, 'totals_today': totals,
            'log_id': log_id, 'dry_run': dry_run, 'heard': text, 'speech': speech}
    return jsonify(body), (201 if logged and not dry_run else 200)


def _log_speech(logged, unresolved, totals, target, lang, dry_run):
    names = _join([r['phrase'] for r in logged], lang)
    kcal = sum(r['calories'] for r in logged)
    missing = _join(unresolved, lang)
    tr = lang == 'tr'
    parts = []
    if logged:
        if dry_run:
            parts.append(f'Eklenecek: {names}, {_num(kcal, lang)} kalori.' if tr
                         else f'I would log {names}, {_num(kcal, lang)} calories.')
        else:
            parts.append(f'Kaydedildi: {names}, {_num(kcal, lang)} kalori.' if tr
                         else f'Logged {names}, {_num(kcal, lang)} calories.')
    if missing:
        parts.append(f'{missing} bulunamadı.' if tr else f"I couldn't find {missing}.")
    if logged and not dry_run:
        parts.append(f'Toplam {_num(target["calories"], lang)} kaloriden {_num(totals["calories"], lang)}.' if tr
                     else f"You're at {_num(totals['calories'], lang)} of {_num(target['calories'], lang)} calories.")
    if not parts:
        parts.append('Hiçbir yiyecek anlaşılamadı.' if tr else "Sorry, I didn't catch any food.")
    return ' '.join(parts)


@voice_bp.route('/status', methods=['GET'])
def status():
    lang = _lang(request.args.get('lang'))
    try:
        d = _parse_date(request.args.get('date'))
    except ValueError:
        return _err('Invalid date format, use YYYY-MM-DD')
    uid = g.api_user_id
    totals = _totals_for_date(d, uid)
    target = _get_target(d, uid)
    remaining = {k: round(target[k] - totals[k], 2) for k in ('protein', 'fat', 'carbs', 'calories')}
    count = _owned(FoodEntry.query, FoodEntry, uid).filter(FoodEntry.entry_date == d).count()
    return jsonify({
        'date': d.isoformat(), 'totals': totals, 'target': target, 'remaining': remaining,
        'entry_count': count, 'speech': _status_speech(d, totals, target, lang),
    })


@voice_bp.route('/entries', methods=['GET'])
def list_entries():
    try:
        d = _parse_date(request.args.get('date'))
    except ValueError:
        return _err('Invalid date format, use YYYY-MM-DD')
    rows = (_owned(FoodEntry.query, FoodEntry, g.api_user_id)
            .filter(FoodEntry.entry_date == d)
            .order_by(FoodEntry.entry_time, FoodEntry.id).all())
    return jsonify({'date': d.isoformat(), 'entries': [e.to_dict() for e in rows]})


def _latest_voice_log(uid):
    cutoff = _utcnow() - timedelta(days=VOICE_LOG_DAYS)
    return (_owned(VoiceLog.query, VoiceLog, uid).filter(VoiceLog.created_at >= cutoff)
            .order_by(VoiceLog.created_at.desc(), VoiceLog.id.desc()).first())


def _voice_log_entries(vl, uid):
    ids = vl.get_entry_ids()
    if not ids:
        return []
    return (_owned(FoodEntry.query, FoodEntry, uid).filter(FoodEntry.id.in_(ids))
            .order_by(FoodEntry.id).all())


@voice_bp.route('/last', methods=['GET'])
def last():
    lang = _lang(request.args.get('lang'))
    uid = g.api_user_id
    vl = _latest_voice_log(uid)
    if vl is None:
        return _err('nothing_logged', 404)
    entries = _voice_log_entries(vl, uid)
    names = _join([_short_name(e.food_name) for e in entries], lang)
    if lang == 'tr':
        speech = f'Son kaydın: {names}.' if entries else 'Son kayıttan hiçbir şey kalmadı.'
    else:
        speech = f'Last time you logged {names}.' if entries else 'Nothing is left from your last log.'
    return jsonify({'log_id': vl.id, 'text': vl.text, 'created_at': vl.created_at.isoformat(),
                    'entries': [e.to_dict() for e in entries], 'speech': speech})


@voice_bp.route('/undo', methods=['POST'])
def undo():
    body = request.get_json(silent=True) if request.is_json else None
    lang = _lang(request.args.get('lang') or (body.get('lang') if isinstance(body, dict) else None))
    uid = g.api_user_id
    vl = _latest_voice_log(uid)
    if vl is None:
        return _err('nothing_logged', 404)
    entries = _voice_log_entries(vl, uid)
    removed = [e.to_dict() for e in entries]
    names = _join([_short_name(e.food_name) for e in entries], lang)
    for e in entries:
        db.session.delete(e)
    db.session.delete(vl)
    db.session.commit()
    if lang == 'tr':
        speech = f'{names} silindi.' if removed else 'Bu kayıtlar zaten silinmiş.'
    else:
        speech = f'Removed {names}.' if removed else 'Those entries were already removed.'
    return jsonify({'removed': removed, 'log_id': vl.id, 'speech': speech})


def _get_owned_entry(entry_id):
    return _owned(FoodEntry.query, FoodEntry, g.api_user_id).filter(FoodEntry.id == entry_id).first()


@voice_bp.route('/entries/<int:entry_id>', methods=['PATCH'])
def patch_entry(entry_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _err('JSON body required')
    e = _get_owned_entry(entry_id)
    if e is None:
        return _err('Not found', 404)
    lang = _lang(data.get('lang'))

    try:
        size = _parse_number(data['serving_size'], 0, 100000) if 'serving_size' in data else None
        if size is not None and size <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return _err('serving_size must be a positive number')
    unit = data.get('serving_unit')
    if unit is not None and (not isinstance(unit, str) or not _UNIT_RE.match(unit.strip())):
        return _err('serving_unit must be 1-20 letters')
    name = data.get('food_name')
    if name is not None and (not isinstance(name, str) or not name.strip() or len(name.strip()) > 200):
        return _err('food_name must be 1-200 characters')
    try:
        meal = _parse_meal(data.get('meal_type'))
    except ValueError:
        return _err('meal_type must be Breakfast, Lunch, Dinner or Snack')
    macros = {}
    for k, hi in (('protein', 10000), ('fat', 10000), ('carbs', 10000), ('calories', 100000)):
        if k in data:
            try:
                macros[k] = _parse_number(data[k], 0, hi)
            except (TypeError, ValueError):
                return _err(f'{k} must be a non-negative number')
    if size is None and unit is None and name is None and meal is None and not macros:
        return _err('No updatable fields given')

    unit = unit.strip() if unit is not None else None
    if size is not None:
        old = e.serving_size
        same_unit = unit is None or unit == e.serving_unit
        if not macros and same_unit and old and old > 0:
            f = size / old
            e.protein = round(e.protein * f, 1)
            e.fat = round(e.fat * f, 1)
            e.carbs = round(e.carbs * f, 1)
            e.calories = round(e.calories * f, 1)
        e.serving_size = size
    if unit is not None:
        e.serving_unit = unit
    if name is not None:
        e.food_name = name.strip()
    if meal is not None:
        e.meal_type = meal
    for k, v in macros.items():
        setattr(e, k, round(v, 1))
    if macros and 'calories' not in macros:
        e.calories = round(e.protein * 4 + e.fat * 9 + e.carbs * 4, 1)
    db.session.commit()
    label = _short_name(e.food_name)
    speech = f'{label} güncellendi.' if lang == 'tr' else f'Updated {label}.'
    return jsonify({'entry': e.to_dict(), 'speech': speech})


@voice_bp.route('/entries/<int:entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    lang = _lang(request.args.get('lang'))
    e = _get_owned_entry(entry_id)
    if e is None:
        return _err('Not found', 404)
    label = _short_name(e.food_name)
    db.session.delete(e)
    db.session.commit()
    speech = f'{label} silindi.' if lang == 'tr' else f'Removed {label}.'
    return jsonify({'deleted': entry_id, 'speech': speech})
