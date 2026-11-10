"""Tests for personal access tokens (/api/tokens) and the voice API (/api/v1)."""
import hashlib
from datetime import date, time

import pytest

from models import db
from models.api_token import ApiToken
from models.food_entry import FoodEntry
from models.saved_food import SavedFood
from models.user import User
from models.voice_log import AiFoodCache, VoiceLog


@pytest.fixture
def auth_on(app):
    prev = app.config.get('AUTH_ENABLED')
    app.config['AUTH_ENABLED'] = True
    yield
    app.config['AUTH_ENABLED'] = prev


@pytest.fixture
def no_server_key(monkeypatch):
    monkeypatch.setattr('utils.gemini.server_key', lambda: '')


@pytest.fixture
def gemini_spy(monkeypatch):
    calls = []

    def fake(prompt, key, **kw):
        calls.append({'prompt': prompt, 'key': key})
        return {'items': [{'phrase': 'flumberries', 'food_name': 'Flumberry', 'grams': 90,
                           'per100': {'protein': 1, 'fat': 0.5, 'carbs': 10, 'calories': 50},
                           'default_grams': 30}]}

    monkeypatch.setattr('utils.gemini.generate_json', fake)
    return calls


def _user(name):
    u = User(username=name, pw_hash='x')
    db.session.add(u)
    db.session.commit()
    return u


def _login(client, user):
    with client.session_transaction() as sess:
        sess['user_id'] = user.id


def _new_token(client, name='alexa'):
    rv = client.post('/api/tokens', json={'name': name})
    assert rv.status_code == 201
    return rv.get_json()


def _bearer(token):
    return {'Authorization': f'Bearer {token}'}


def _food(name='Zorblax bar', **kw):
    f = SavedFood(name=name, protein=10, fat=5, carbs=20, calories=165, source='custom',
                  default_serving=50, serving_unit='g', **kw)
    db.session.add(f)
    db.session.commit()
    return f


def _entry(uid=None, **kw):
    vals = dict(food_name='Rice', protein=10, fat=2, carbs=40, calories=218, serving_size=100,
                serving_unit='g', entry_date=date.today(), entry_time=time(12, 0), user_id=uid)
    vals.update(kw)
    e = FoodEntry(**vals)
    db.session.add(e)
    db.session.commit()
    return e


# ── Token management ─────────────────────────────────────────────────────────

class TestTokens:

    def test_create_list_delete(self, client):
        created = _new_token(client)
        assert created['token'].startswith('nt_')
        assert created['prefix'] == created['token'][:12]

        listed = client.get('/api/tokens').get_json()
        assert len(listed) == 1
        assert 'token' not in listed[0] and 'token_hash' not in listed[0]
        assert listed[0]['name'] == 'alexa'

        assert client.delete(f'/api/tokens/{created["id"]}').status_code == 200
        assert client.get('/api/tokens').get_json() == []

    def test_only_hash_stored(self, client):
        token = _new_token(client)['token']
        row = ApiToken.query.one()
        assert row.token_hash == hashlib.sha256(token.encode()).hexdigest()
        assert token not in (row.token_hash, row.prefix, row.name)

    def test_name_validation_and_limit(self, client):
        assert client.post('/api/tokens', json={}).status_code == 400
        assert client.post('/api/tokens', json={'name': 'x' * 81}).status_code == 400
        for i in range(10):
            _new_token(client, f't{i}')
        assert client.post('/api/tokens', json={'name': 'one too many'}).status_code == 400

    def test_requires_session_when_auth_on(self, client, auth_on):
        assert client.get('/api/tokens').status_code == 401
        assert client.post('/api/tokens', json={'name': 'x'}).status_code == 401

    def test_user_cannot_delete_others_token(self, app, auth_on):
        a, b = _user('alice'), _user('bob')
        ca, cb = app.test_client(), app.test_client()
        _login(ca, a)
        _login(cb, b)
        tok = _new_token(ca)
        assert cb.delete(f'/api/tokens/{tok["id"]}').status_code == 404
        assert cb.get('/api/tokens').get_json() == []
        assert len(ca.get('/api/tokens').get_json()) == 1
        assert ApiToken.query.one().user_id == a.id


# ── Token auth on /api/v1 ────────────────────────────────────────────────────

class TestVoiceAuth:

    def test_missing_and_invalid_token(self, client):
        assert client.get('/api/v1/status').status_code == 401
        rv = client.get('/api/v1/status', headers=_bearer('nt_doesnotexist'))
        assert rv.status_code == 401 and rv.get_json() == {'error': 'invalid_token'}
        assert client.get('/api/v1/status', headers={'Authorization': 'Basic abc'}).status_code == 401

    def test_revoked_and_deleted_token(self, client):
        tok = _new_token(client)
        assert client.get('/api/v1/status', headers=_bearer(tok['token'])).status_code == 200
        row = db.session.get(ApiToken, tok['id'])
        row.revoked = True
        db.session.commit()
        assert client.get('/api/v1/status', headers=_bearer(tok['token'])).status_code == 401
        db.session.delete(row)
        db.session.commit()
        assert client.get('/api/v1/status', headers=_bearer(tok['token'])).status_code == 401

    def test_session_cookie_not_accepted(self, client, auth_on):
        u = _user('carol')
        _login(client, u)
        assert client.get('/api/v1/status').status_code == 401
        assert client.post('/api/v1/log', json={'text': 'an apple'}).status_code == 401

    def test_last_used_updated(self, client):
        tok = _new_token(client)
        client.get('/api/v1/status', headers=_bearer(tok['token']))
        assert db.session.get(ApiToken, tok['id']).last_used_at is not None

    def test_token_maps_to_user(self, app, auth_on):
        a = _user('dave')
        c = app.test_client()
        _login(c, a)
        tok = _new_token(c)['token']
        anon = app.test_client()
        rv = anon.post('/api/v1/log', json={'text': '200 g zorblax bar'}, headers=_bearer(tok))
        # No food in DB and no key → nothing logged, but authenticated.
        assert rv.status_code == 200


# ── /log ─────────────────────────────────────────────────────────────────────

class TestLog:

    def test_db_match_without_gemini(self, client, no_server_key, gemini_spy):
        food = _food()
        tok = _new_token(client)['token']
        rv = client.post('/api/v1/log', json={'text': '200 g zorblax bar', 'meal_type': 'lunch'},
                         headers=_bearer(tok))
        assert rv.status_code == 201, rv.get_json()
        body = rv.get_json()
        assert gemini_spy == []
        assert len(body['logged']) == 1
        item = body['logged'][0]
        assert item['source'] == 'db'
        assert item['saved_food_id'] == food.id
        assert item['protein'] == 20 and item['calories'] == 330
        assert item['meal_type'] == 'Lunch'
        assert body['totals_today']['calories'] == 330
        assert body['speech']
        vl = VoiceLog.query.one()
        assert vl.get_entry_ids() == [item['id']]
        assert body['log_id'] == vl.id

    def test_unresolved_without_key(self, client, no_server_key, gemini_spy):
        tok = _new_token(client)['token']
        rv = client.post('/api/v1/log', json={'text': '3 flumberries'}, headers=_bearer(tok))
        assert rv.status_code == 200
        body = rv.get_json()
        assert body['logged'] == [] and body['unresolved']
        assert "couldn't find" in body['speech']
        assert gemini_spy == []
        assert FoodEntry.query.count() == 0 and VoiceLog.query.count() == 0

    def test_ai_then_cache(self, client, monkeypatch, gemini_spy):
        monkeypatch.setattr('utils.gemini.server_key', lambda: 'AIzaServerKey123')
        tok = _new_token(client)['token']
        rv = client.post('/api/v1/log', json={'text': '3 flumberries'}, headers=_bearer(tok))
        assert rv.status_code == 201, rv.get_json()
        item = rv.get_json()['logged'][0]
        assert item['source'] == 'ai' and item['food_name'] == 'Flumberry'
        assert item['calories'] == 45
        assert len(gemini_spy) == 1 and gemini_spy[0]['key'] == 'AIzaServerKey123'
        assert AiFoodCache.query.count() == 1

        rv = client.post('/api/v1/log', json={'text': '3 flumberries'}, headers=_bearer(tok))
        assert rv.status_code == 201
        item = rv.get_json()['logged'][0]
        assert item['source'] == 'cache'
        assert item['calories'] == 45  # 3 × 30 g default × 50 kcal/100 g
        assert len(gemini_spy) == 1
        assert AiFoodCache.query.count() == 1

    def test_gemini_failure_is_unresolved(self, client, monkeypatch):
        monkeypatch.setattr('utils.gemini.server_key', lambda: 'AIzaServerKey123')

        def boom(*a, **kw):
            raise RuntimeError('Gemini 500')
        monkeypatch.setattr('utils.gemini.generate_json', boom)
        tok = _new_token(client)['token']
        rv = client.post('/api/v1/log', json={'text': '3 flumberries'}, headers=_bearer(tok))
        assert rv.status_code == 200 and rv.get_json()['logged'] == []

    def test_dry_run_does_not_save(self, client, no_server_key):
        _food()
        tok = _new_token(client)['token']
        rv = client.post('/api/v1/log', json={'text': '200 g zorblax bar', 'dry_run': True},
                         headers=_bearer(tok))
        assert rv.status_code == 200
        body = rv.get_json()
        assert len(body['logged']) == 1 and body['logged'][0]['id'] is None
        assert body['log_id'] is None
        assert FoodEntry.query.count() == 0 and VoiceLog.query.count() == 0

    def test_bad_gemini_header_ignored(self, client, no_server_key, gemini_spy):
        tok = _new_token(client)['token']
        headers = {**_bearer(tok), 'X-Gemini-Key': 'AIza bad key!'}
        rv = client.post('/api/v1/log', json={'text': '3 flumberries'}, headers=headers)
        assert rv.status_code == 200 and gemini_spy == []
        assert 'AIza bad key!' not in rv.get_data(as_text=True)

    def test_good_gemini_header_used(self, client, no_server_key, gemini_spy):
        tok = _new_token(client)['token']
        headers = {**_bearer(tok), 'X-Gemini-Key': 'AIzaUserKey_456'}
        rv = client.post('/api/v1/log', json={'text': '3 flumberries'}, headers=headers)
        assert rv.status_code == 201
        assert gemini_spy[0]['key'] == 'AIzaUserKey_456'
        assert 'AIzaUserKey_456' not in rv.get_data(as_text=True)

    @pytest.mark.parametrize('payload', [
        {}, {'text': ''}, {'text': 'x' * 501}, {'text': 5},
        {'text': 'apple', 'date': '2026-13-40'}, {'text': 'apple', 'meal_type': 'brunchy'},
        {'text': 'apple', 'dry_run': 'yes'},
    ])
    def test_validation(self, client, no_server_key, payload):
        tok = _new_token(client)['token']
        rv = client.post('/api/v1/log', json=payload, headers=_bearer(tok))
        assert rv.status_code == 400 and 'error' in rv.get_json()


# ── status / entries / last / undo ───────────────────────────────────────────

class TestReadAndUndo:

    def test_status(self, client):
        _entry(calories=1450, protein=90)
        tok = _new_token(client)['token']
        body = client.get('/api/v1/status', headers=_bearer(tok)).get_json()
        assert body['totals']['calories'] == 1450
        assert body['target']['calories'] == 2200
        assert body['remaining']['calories'] == 750
        assert body['entry_count'] == 1
        assert '1,450 of 2,200' in body['speech'] and '750 calories left' in body['speech']
        tr = client.get('/api/v1/status?lang=tr', headers=_bearer(tok)).get_json()
        assert '1.450' in tr['speech']
        assert client.get('/api/v1/status?date=bad', headers=_bearer(tok)).status_code == 400

    def test_entries_list(self, client):
        _entry()
        _entry(entry_date=date(2020, 1, 1))
        tok = _new_token(client)['token']
        body = client.get('/api/v1/entries', headers=_bearer(tok)).get_json()
        assert len(body['entries']) == 1

    def test_last_and_undo(self, client, no_server_key):
        _food()
        tok = _new_token(client)['token']
        assert client.get('/api/v1/last', headers=_bearer(tok)).status_code == 404
        assert client.post('/api/v1/undo', headers=_bearer(tok)).status_code == 404

        logged = client.post('/api/v1/log', json={'text': '200 g zorblax bar'},
                             headers=_bearer(tok)).get_json()
        last = client.get('/api/v1/last', headers=_bearer(tok)).get_json()
        assert last['log_id'] == logged['log_id']
        assert [e['id'] for e in last['entries']] == [logged['logged'][0]['id']]

        rv = client.post('/api/v1/undo', headers=_bearer(tok))
        assert rv.status_code == 200
        assert rv.get_json()['speech'].startswith('Removed')
        assert FoodEntry.query.count() == 0 and VoiceLog.query.count() == 0
        assert client.get('/api/v1/last', headers=_bearer(tok)).status_code == 404


# ── PATCH / DELETE ───────────────────────────────────────────────────────────

class TestEditDelete:

    def test_patch_rescales(self, client):
        e = _entry(protein=10, fat=2, carbs=40, calories=200, serving_size=100)
        tok = _new_token(client)['token']
        rv = client.patch(f'/api/v1/entries/{e.id}', json={'serving_size': 150}, headers=_bearer(tok))
        assert rv.status_code == 200
        out = rv.get_json()['entry']
        assert out['serving_size'] == 150
        assert out['protein'] == 15 and out['carbs'] == 60 and out['calories'] == 300

    def test_patch_macros_recompute_calories(self, client):
        e = _entry()
        tok = _new_token(client)['token']
        rv = client.patch(f'/api/v1/entries/{e.id}', json={'protein': 20, 'fat': 10, 'carbs': 30},
                          headers=_bearer(tok))
        assert rv.get_json()['entry']['calories'] == 20 * 4 + 10 * 9 + 30 * 4

    def test_patch_zero_old_size_no_crash(self, client):
        e = _entry(serving_size=0)
        tok = _new_token(client)['token']
        rv = client.patch(f'/api/v1/entries/{e.id}', json={'serving_size': 50}, headers=_bearer(tok))
        assert rv.status_code == 200 and rv.get_json()['entry']['calories'] == 218

    @pytest.mark.parametrize('payload', [
        {}, {'serving_size': -1}, {'serving_size': 'abc'}, {'protein': True},
        {'calories': float('inf')}, {'meal_type': 'brunchy'}, {'food_name': ''},
        {'serving_unit': 'g; drop'},
    ])
    def test_patch_validation(self, client, payload):
        e = _entry()
        tok = _new_token(client)['token']
        rv = client.patch(f'/api/v1/entries/{e.id}', json=payload, headers=_bearer(tok))
        assert rv.status_code == 400

    def test_ownership(self, app, auth_on):
        a, b = _user('erin'), _user('frank')
        ca = app.test_client()
        _login(ca, a)
        tok = _new_token(ca)['token']
        theirs = _entry(uid=b.id)
        mine = _entry(uid=a.id)
        anon = app.test_client()
        assert anon.patch(f'/api/v1/entries/{theirs.id}', json={'serving_size': 1},
                          headers=_bearer(tok)).status_code == 404
        assert anon.delete(f'/api/v1/entries/{theirs.id}', headers=_bearer(tok)).status_code == 404
        assert db.session.get(FoodEntry, theirs.id) is not None
        assert anon.delete(f'/api/v1/entries/{mine.id}', headers=_bearer(tok)).status_code == 200
        assert db.session.get(FoodEntry, mine.id) is None

    def test_local_token_only_sees_null_user_entries(self, client):
        u = _user('gina')
        other = _entry(uid=u.id)
        tok = _new_token(client)['token']
        assert client.delete(f'/api/v1/entries/{other.id}', headers=_bearer(tok)).status_code == 404


def test_delete_user_data_removes_voice_rows(app, auth_on):
    from routes.auth import delete_user_data
    u = _user('hank')
    db.session.add_all([
        ApiToken(user_id=u.id, name='t', token_hash='a' * 64, prefix='nt_x'),
        VoiceLog(user_id=u.id, text='x', lang='en', entry_ids='[]'),
        AiFoodCache(user_id=u.id, phrase='x', food_name='X', protein=1, fat=1, carbs=1,
                    calories=17, default_grams=100),
    ])
    db.session.commit()
    delete_user_data(u.id)
    db.session.commit()
    assert ApiToken.query.count() == 0 and VoiceLog.query.count() == 0 and AiFoodCache.query.count() == 0
