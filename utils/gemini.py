"""Gemini helpers shared by chat, image scan and the voice API.

- Per-user Gemini key kept in an encrypted HttpOnly cookie on the device (never in the DB).
  Each user gets their own cookie, so switching accounts on one device doesn't lose keys,
  and one user's cookie can't be decrypted for another user.
- Dynamic model list fetched from the Gemini API (cached), with a static fallback.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import time
import urllib.error
import urllib.request

from flask import current_app, request, session

API_BASE = 'https://generativelanguage.googleapis.com/v1beta'

FALLBACK_MODELS = ['gemini-3.8-flash', 'gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']
FALLBACK_DEFAULT = FALLBACK_MODELS[0]

# Model ids are interpolated into the request URL, so restrict the charset.
_MODEL_RE = re.compile(r'^gemini-[a-z0-9][a-z0-9.\-]{0,62}$')
_EXCLUDE = ('embedding', 'tts', 'image', 'live', 'audio', 'robotics', 'computer-use', 'aqa')
_MODELS_TTL = 6 * 3600
_models_cache: dict = {}

COOKIE_PREFIX = 'nt_gk_'
COOKIE_MAX_AGE = 400 * 24 * 3600  # Chrome caps cookie lifetime at 400 days


# ---------------------------------------------------------------------------
# Key storage (encrypted per-user cookie)
# ---------------------------------------------------------------------------
def _uid_bytes(uid) -> bytes:
    return str('local' if uid is None else uid).encode()


def _hmac(label: bytes, uid) -> bytes:
    secret = str(current_app.config['SECRET_KEY']).encode()
    return hmac.new(secret, label + b'|' + _uid_bytes(uid), hashlib.sha256).digest()


def cookie_name(uid) -> str:
    return COOKIE_PREFIX + _hmac(b'nt-gemini-cookie-name', uid).hex()[:16]


def _fernet(uid):
    from cryptography.fernet import Fernet
    return Fernet(base64.urlsafe_b64encode(_hmac(b'nt-gemini-cookie-key', uid)))


def _session_uid():
    return session.get('user_id') if current_app.config.get('AUTH_ENABLED') else None


def cookie_key(uid=None) -> str:
    """Decrypt the current user's key cookie; '' if missing/invalid."""
    if uid is None:
        uid = _session_uid()
    raw = request.cookies.get(cookie_name(uid))
    if not raw:
        return ''
    try:
        return _fernet(uid).decrypt(raw.encode()).decode()
    except Exception:
        return ''


def set_key_cookie(response, key: str, uid=None):
    if uid is None:
        uid = _session_uid()
    token = _fernet(uid).encrypt(key.encode()).decode()
    response.set_cookie(
        cookie_name(uid), token, max_age=COOKIE_MAX_AGE, path='/',
        httponly=True, secure=request.is_secure, samesite='Lax',
    )
    return response


def clear_key_cookie(response, uid=None):
    if uid is None:
        uid = _session_uid()
    response.delete_cookie(cookie_name(uid), path='/', httponly=True,
                           secure=request.is_secure, samesite='Lax')
    return response


def key_hint(key: str) -> str:
    return ('\u2026' + key[-4:]) if key else ''


def _token_fernet(token: str):
    from cryptography.fernet import Fernet
    secret = str(current_app.config['SECRET_KEY']).encode()
    raw = hmac.new(secret, b'nt-token-gemini|' + token.encode(), hashlib.sha256).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


def seal_for_token(key: str, token: str) -> str:
    """Encrypt a Gemini key so only a request presenting `token` can decrypt it (DB holds only the hash)."""
    return _token_fernet(token).encrypt(key.encode()).decode()


def open_for_token(blob: str, token: str) -> str:
    if not blob:
        return ''
    try:
        return _token_fernet(token).decrypt(blob.encode()).decode()
    except Exception:
        return ''


def looks_like_key(key: str) -> bool:
    return bool(key) and len(key) <= 200 and bool(re.fullmatch(r'[A-Za-z0-9_.\-]+', key)) \
        and (key.startswith('AIza') or key.startswith('AQ.'))


def server_key() -> str:
    """GEMINI_API_KEY from env or .env (server-wide fallback, e.g. self-hosted)."""
    key = os.environ.get('GEMINI_API_KEY', '').strip()
    if key:
        return key
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    try:
        with open(os.path.normpath(env_path), encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or '=' not in line:
                    continue
                k, _, v = line.partition('=')
                if k.strip() == 'GEMINI_API_KEY':
                    return v.strip()
    except OSError:
        pass
    return ''


def resolve_key(explicit: str = '') -> str:
    """Explicit key (legacy body/form field) > device cookie > server key."""
    return (explicit or '').strip() or cookie_key() or server_key()


# ---------------------------------------------------------------------------
# Dynamic model list
# ---------------------------------------------------------------------------
def _version(model_id: str) -> float:
    m = re.match(r'gemini-(\d+(?:\.\d+)?)', model_id)
    return float(m.group(1)) if m else 0.0


def _tier(model_id: str) -> int:
    # Prefer flash (balanced) > flash-lite (fast) > pro (slow/costly) for a food logger.
    if 'flash-lite' in model_id:
        return 1
    if 'flash' in model_id:
        return 0
    return 2


def _sort_key(m: dict):
    return (m['preview'], -_version(m['id']), _tier(m['id']), m['id'])


def _label(model_id: str, display: str, preview: bool) -> str:
    name = display or model_id
    return name + (' (preview)' if preview and 'preview' not in name.lower() else '')


def _fallback_list() -> list:
    return [{'id': m, 'label': m, 'preview': False} for m in FALLBACK_MODELS]


def list_models(key: str, timeout: float = 6) -> list:
    """Return [{id, label, preview}] of text-capable Gemini models, newest first."""
    if not key:
        return _fallback_list()
    cache_id = hashlib.sha256(key.encode()).hexdigest()[:16]
    hit = _models_cache.get(cache_id)
    if hit and time.time() - hit[0] < _MODELS_TTL:
        return hit[1]

    models = []
    page_token = ''
    try:
        for _ in range(5):
            url = f'{API_BASE}/models?pageSize=1000' + (f'&pageToken={page_token}' if page_token else '')
            req = urllib.request.Request(url, headers={'x-goog-api-key': key})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            for m in data.get('models', []):
                mid = (m.get('name') or '').removeprefix('models/')
                if not _MODEL_RE.match(mid):
                    continue
                if 'generateContent' not in (m.get('supportedGenerationMethods') or []):
                    continue
                if any(x in mid for x in _EXCLUDE):
                    continue
                preview = 'preview' in mid or 'exp' in mid
                models.append({'id': mid, 'label': _label(mid, m.get('displayName', ''), preview),
                               'preview': preview})
            page_token = data.get('nextPageToken') or ''
            if not page_token or not re.fullmatch(r'[A-Za-z0-9_\-=]+', page_token):
                break
    except Exception:
        return hit[1] if hit else _fallback_list()

    if not models:
        return _fallback_list()
    models.sort(key=_sort_key)
    _models_cache[cache_id] = (time.time(), models)
    return models


def cached_models(key: str):
    if not key:
        return None
    hit = _models_cache.get(hashlib.sha256(key.encode()).hexdigest()[:16])
    return hit[1] if hit else None


def default_model(models: list) -> str:
    for m in models:
        if not m['preview'] and _tier(m['id']) == 0:
            return m['id']
    return models[0]['id'] if models else FALLBACK_DEFAULT


def pick_model(requested: str, key: str) -> str:
    """Validate a client-requested model; unknown/retired ids fall back to the default."""
    requested = (requested or '').strip()
    models = cached_models(key)
    if models:
        if requested and any(m['id'] == requested for m in models):
            return requested
        return default_model(models)
    return requested if _MODEL_RE.match(requested) else FALLBACK_DEFAULT


# ---------------------------------------------------------------------------
# One-shot JSON generation (used by the voice API)
# ---------------------------------------------------------------------------
def _post_generate(model: str, body: dict, key: str, timeout: float) -> str:
    req = urllib.request.Request(
        f'{API_BASE}/models/{model}:generateContent', data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', 'x-goog-api-key': key}, method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        parts = data['candidates'][0]['content'].get('parts') or []
        return ''.join(p.get('text', '') for p in parts)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Gemini {e.code}') from None
    except Exception as e:
        raise RuntimeError(f'Gemini error: {type(e).__name__}') from None


def generate_text(prompt: str, key: str, model: str = '', system: str = '',
                  timeout: float = 8, max_tokens: int = 1024) -> str:
    """Single generateContent call, no retries (voice clients need fast answers)."""
    model = pick_model(model, key)
    body = {
        'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
        'generationConfig': {'maxOutputTokens': max_tokens, 'responseMimeType': 'application/json'},
    }
    if system:
        body['systemInstruction'] = {'parts': [{'text': system}]}
    return _post_generate(model, body, key, timeout)


def transcribe(audio: bytes, mime: str, key: str, lang: str = 'en', model: str = '',
               timeout: float = 25) -> str:
    """Speech-to-text for a short voice note (Turkish or English)."""
    likely = 'Turkish' if lang == 'tr' else 'English or Turkish'
    prompt = (f'Transcribe this short voice note verbatim. The speaker most likely speaks {likely}; '
              'keep the original language and write numbers as digits. It is usually about food '
              'and portions. Return only the transcript text without quotes or commentary. '
              'If there is no intelligible speech, return nothing.')
    body = {
        'contents': [{'role': 'user', 'parts': [
            {'inlineData': {'mimeType': mime, 'data': base64.b64encode(audio).decode()}},
            {'text': prompt},
        ]}],
        'generationConfig': {'maxOutputTokens': 512, 'temperature': 0},
    }
    return _post_generate(pick_model(model, key), body, key, timeout).strip().strip('"')


def generate_json(prompt: str, key: str, **kw):
    text = generate_text(prompt, key, **kw).strip()
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
    return json.loads(text)


def generate_json_parts(parts: list, key: str, model: str = '', system: str = '',
                        timeout: float = 15, max_tokens: int = 2048):
    """generateContent with arbitrary parts (e.g. inline audio + text), JSON response."""
    body = {
        'contents': [{'role': 'user', 'parts': parts}],
        'generationConfig': {'maxOutputTokens': max_tokens, 'responseMimeType': 'application/json',
                             'temperature': 0.1},
    }
    if system:
        body['systemInstruction'] = {'parts': [{'text': system}]}
    text = _post_generate(pick_model(model, key), body, key, timeout).strip()
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
    return json.loads(text)
