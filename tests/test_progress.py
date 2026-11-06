import re
from datetime import date, timedelta

import pytest

from models import db
from models.user import User
from models.weight_log import WeightLog, BodyGoal
from routes.progress import bmi_for, bmi_category, progress_pct


@pytest.fixture
def auth_on(app):
    app.config['AUTH_ENABLED'] = True
    yield
    app.config['AUTH_ENABLED'] = False


def _make_user(name):
    u = User(username=name)
    u.set_pw('secret123')
    db.session.add(u)
    db.session.commit()
    return u


def _login(client, uid):
    with client.session_transaction() as sess:
        sess['user_id'] = uid


def _days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()


# --- pure helpers ---

def test_bmi_and_category():
    assert bmi_for(54, 172) == 18.3
    assert bmi_category(18.3) == 'underweight'
    assert bmi_category(18.5) == 'healthy'
    assert bmi_category(24.9) == 'healthy'
    assert bmi_category(25) == 'overweight'
    assert bmi_category(29.9) == 'overweight'
    assert bmi_category(30) == 'obese'
    assert bmi_for(70, None) is None
    assert bmi_category(None) is None


def test_progress_pct_loss_and_gain():
    assert progress_pct(80, 72, 60) == 40
    assert progress_pct(80, 85, 60) == 0          # moved away -> clamped
    assert progress_pct(80, 55, 60) == 100        # overshoot -> clamped
    assert progress_pct(50, 55, 60) == 50         # gain goal
    assert progress_pct(50, 48, 60) == 0
    assert progress_pct(70, 70, 70) == 100
    assert progress_pct(None, 70, 60) is None
    assert progress_pct(80, 72, None) is None


# --- API ---

def test_get_empty(client):
    data = client.get('/api/progress').get_json()
    assert data['logs'] == []
    assert data['current_weight_kg'] is None
    assert data['progress_pct'] is None
    assert data['bmi'] is None


def test_upsert_same_day(client):
    r1 = client.post('/api/progress/weight', json={'weight_kg': 72.4})
    assert r1.status_code == 201
    r2 = client.post('/api/progress/weight', json={'weight_kg': 71.9})
    assert r2.status_code == 200
    assert r2.get_json()['id'] == r1.get_json()['id']
    assert WeightLog.query.count() == 1
    assert WeightLog.query.first().weight_kg == 71.9


@pytest.mark.parametrize('body', [
    {},
    {'weight_kg': 'abc'},
    {'weight_kg': 19.9},
    {'weight_kg': 400.1},
    {'weight_kg': True},
    {'weight_kg': 70, 'date': '2026/01/01'},
    {'weight_kg': 70, 'date': 'not-a-date'},
])
def test_weight_validation(client, body):
    assert client.post('/api/progress/weight', json=body).status_code == 400


def test_weight_future_date_rejected(client):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert client.post('/api/progress/weight', json={'weight_kg': 70, 'date': tomorrow}).status_code == 400


@pytest.mark.parametrize('body', [
    {},
    {'goal_weight_kg': 10},
    {'goal_weight_kg': 'x'},
    {'height_cm': 79},
    {'height_cm': 251},
])
def test_goal_validation(client, body):
    assert client.put('/api/progress/goal', json=body).status_code == 400


def test_full_progress_loss(client):
    client.post('/api/progress/weight', json={'weight_kg': 80, 'date': _days_ago(20)})
    client.post('/api/progress/weight', json={'weight_kg': 72, 'date': _days_ago(1)})
    r = client.put('/api/progress/goal', json={'goal_weight_kg': 60, 'height_cm': 172})
    assert r.status_code == 200
    data = client.get('/api/progress').get_json()
    assert data['start_weight_kg'] == 80
    assert data['current_weight_kg'] == 72
    assert data['progress_pct'] == 40
    assert data['progress_status'] == 'good'
    assert data['bmi'] == 24.3
    assert data['bmi_category'] == 'healthy'
    assert [l['weight_kg'] for l in data['logs']] == [80, 72]


def test_full_progress_gain(client):
    client.post('/api/progress/weight', json={'weight_kg': 50, 'date': _days_ago(5)})
    client.post('/api/progress/weight', json={'weight_kg': 52, 'date': _days_ago(0)})
    client.put('/api/progress/goal', json={'goal_weight_kg': 60})
    data = client.get('/api/progress').get_json()
    assert data['progress_pct'] == 20
    assert data['progress_status'] == 'on_track'
    assert data['bmi'] is None  # no height yet


def test_range_filter(client):
    client.post('/api/progress/weight', json={'weight_kg': 80, 'date': _days_ago(60)})
    client.post('/api/progress/weight', json={'weight_kg': 78, 'date': _days_ago(20)})
    client.post('/api/progress/weight', json={'weight_kg': 76, 'date': _days_ago(2)})
    assert len(client.get('/api/progress?range=week').get_json()['logs']) == 1
    assert len(client.get('/api/progress?range=month').get_json()['logs']) == 2
    data = client.get('/api/progress?range=all').get_json()
    assert len(data['logs']) == 3
    # start weight is the first log ever, independent of the range
    assert client.get('/api/progress?range=week').get_json()['start_weight_kg'] == 80
    assert client.get('/api/progress?range=bogus').status_code == 400


def test_delete_own_log(client):
    log_id = client.post('/api/progress/weight', json={'weight_kg': 70}).get_json()['id']
    assert client.delete(f'/api/progress/weight/{log_id}').status_code == 200
    assert client.delete(f'/api/progress/weight/{log_id}').status_code == 404


def test_requires_auth(client, auth_on):
    assert client.get('/api/progress').status_code == 401
    assert client.post('/api/progress/weight', json={'weight_kg': 70}).status_code == 401


def test_user_isolation_and_delete_ownership(client, auth_on):
    alice = _make_user('alice_p')
    bob = _make_user('bob_p')
    _login(client, alice.id)
    log_id = client.post('/api/progress/weight', json={'weight_kg': 70}).get_json()['id']
    client.put('/api/progress/goal', json={'goal_weight_kg': 60, 'height_cm': 170})

    _login(client, bob.id)
    assert client.delete(f'/api/progress/weight/{log_id}').status_code == 404
    data = client.get('/api/progress').get_json()
    assert data['logs'] == []
    assert data['goal_weight_kg'] is None
    assert db.session.get(WeightLog, log_id) is not None


def test_account_deletion_removes_weight_data(client, auth_on):
    alice = _make_user('alice_del')
    bob = _make_user('bob_del')
    db.session.add_all([
        WeightLog(user_id=alice.id, log_date=date.today(), weight_kg=70),
        BodyGoal(user_id=alice.id, goal_weight_kg=60, height_cm=170),
        WeightLog(user_id=bob.id, log_date=date.today(), weight_kg=80),
    ])
    db.session.commit()
    alice_id, bob_id = alice.id, bob.id

    _login(client, alice_id)
    html = client.get('/delete-account').get_data(as_text=True)
    token = re.search(r'name="token" value="([^"]+)"', html).group(1)
    resp = client.post('/delete-account', data={'token': token, 'confirm': 'DELETE'})
    assert resp.status_code == 200

    db.session.expire_all()
    assert WeightLog.query.filter_by(user_id=alice_id).count() == 0
    assert BodyGoal.query.filter_by(user_id=alice_id).count() == 0
    assert WeightLog.query.filter_by(user_id=bob_id).count() == 1


def test_progress_page_renders(client):
    resp = client.get('/progress')
    assert resp.status_code == 200
    assert b'pg-chart' in resp.data
