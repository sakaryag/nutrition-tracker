"""Gemini key cookie (per user, encrypted, survives account switching) and dynamic model list."""
import pytest

from models import db
from models.user import User
from utils import gemini as G

KEY_A = 'AIzaSyUserAKey_0000000000000000000000'
KEY_B = 'AIzaSyUserBKey_1111111111111111111111'


@pytest.fixture
def auth_on(app):
    prev = app.config.get('AUTH_ENABLED')
    app.config['AUTH_ENABLED'] = True
    yield
    app.config['AUTH_ENABLED'] = prev


@pytest.fixture(autouse=True)
def no_server_key(monkeypatch):
    monkeypatch.setattr(G, 'server_key', lambda: '')
    G._models_cache.clear()


def _user(name):
    u = User(username=name, pw_hash='x')
    db.session.add(u)
    db.session.commit()
    return u


def _login(client, user):
    with client.session_transaction() as sess:
        sess.clear()
        sess['user_id'] = user.id


def test_save_get_clear_key(client):
    assert client.get('/api/chat/key').get_json()['has_key'] is False
    rv = client.put('/api/chat/key', json={'key': KEY_A})
    assert rv.status_code == 200
    set_cookie = rv.headers.get('Set-Cookie', '')
    assert 'HttpOnly' in set_cookie and KEY_A not in set_cookie
    body = client.get('/api/chat/key').get_json()
    assert body['has_key'] is True and body['hint'].endswith(KEY_A[-4:])
    assert client.delete('/api/chat/key').get_json()['has_key'] is False
    assert client.get('/api/chat/key').get_json()['has_key'] is False


def test_rejects_malformed_key(client):
    assert client.put('/api/chat/key', json={'key': 'not a key'}).status_code == 400
    assert client.put('/api/chat/key', json={'key': 'AIza<script>'}).status_code == 400


def test_key_survives_account_switch(client, auth_on):
    a, b = _user('alice'), _user('bob')
    _login(client, a)
    client.put('/api/chat/key', json={'key': KEY_A})
    _login(client, b)
    assert client.get('/api/chat/key').get_json()['has_key'] is False
    client.put('/api/chat/key', json={'key': KEY_B})
    _login(client, a)
    assert client.get('/api/chat/key').get_json()['hint'].endswith(KEY_A[-4:])
    _login(client, b)
    assert client.get('/api/chat/key').get_json()['hint'].endswith(KEY_B[-4:])


def test_other_users_cookie_not_decryptable(app, auth_on):
    a, b = _user('carol'), _user('dave')
    with app.test_request_context('/'):
        token = G._fernet(a.id).encrypt(KEY_A.encode()).decode()
    with app.test_request_context('/', headers={'Cookie': f'{G.cookie_name(b.id)}={token}'}):
        assert G.cookie_key(b.id) == ''


def test_key_requires_login(client, auth_on):
    assert client.put('/api/chat/key', json={'key': KEY_A}).status_code == 401


def test_models_fallback_without_key(client):
    body = client.get('/api/chat/models').get_json()
    assert body['live'] is False
    assert body['default'] == G.FALLBACK_DEFAULT


def test_models_live_list_sorted_and_filtered(client, monkeypatch):
    payload = {'models': [
        {'name': 'models/gemini-2.0-flash', 'supportedGenerationMethods': ['generateContent']},
        {'name': 'models/gemini-9.1-flash', 'displayName': 'Gemini 9.1 Flash',
         'supportedGenerationMethods': ['generateContent']},
        {'name': 'models/gemini-9.1-flash-lite', 'supportedGenerationMethods': ['generateContent']},
        {'name': 'models/gemini-9.5-pro-preview', 'supportedGenerationMethods': ['generateContent']},
        {'name': 'models/gemini-embedding-001', 'supportedGenerationMethods': ['embedContent']},
        {'name': 'models/gemini-9.1-flash-tts', 'supportedGenerationMethods': ['generateContent']},
        {'name': 'models/text-bison', 'supportedGenerationMethods': ['generateContent']},
    ]}

    class _Resp:
        def __init__(self, data): self._d = data
        def read(self): return __import__('json').dumps(self._d).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr('urllib.request.urlopen', lambda req, timeout=0: _Resp(payload))
    client.put('/api/chat/key', json={'key': KEY_A})
    body = client.get('/api/chat/models').get_json()
    ids = [m['id'] for m in body['models']]
    assert ids == ['gemini-9.1-flash', 'gemini-9.1-flash-lite', 'gemini-2.0-flash', 'gemini-9.5-pro-preview']
    assert body['default'] == 'gemini-9.1-flash' and body['live'] is True

    with client.application.test_request_context('/'):
        assert G.pick_model('gemini-retired-1', KEY_A) == 'gemini-9.1-flash'
        assert G.pick_model('gemini-9.1-flash-lite', KEY_A) == 'gemini-9.1-flash-lite'


def test_pick_model_rejects_path_injection():
    assert G.pick_model('../../v1/evil', '') == G.FALLBACK_DEFAULT
    assert G.pick_model('gemini-x:generateContent?', '') == G.FALLBACK_DEFAULT
