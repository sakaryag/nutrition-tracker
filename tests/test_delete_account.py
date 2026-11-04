import re
from datetime import date, time

import pytest

from models import db
from models.user import User
from models.food_entry import FoodEntry
from models.water_log import WaterLog
from models.friend_connection import FriendConnection
from models.meal_template import MealTemplate
from models.meal_template_item import MealTemplateItem


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


def _token(client):
    html = client.get('/delete-account').get_data(as_text=True)
    m = re.search(r'name="token" value="([^"]+)"', html)
    assert m, 'delete form token missing'
    return m.group(1)


def test_page_public_when_logged_out(client, auth_on):
    resp = client.get('/delete-account')
    assert resp.status_code == 200
    assert b'How to delete your account' in resp.data


def test_delete_removes_user_and_data(client, auth_on):
    alice = _make_user('alice')
    bob = _make_user('bob')
    db.session.add_all([
        FoodEntry(food_name='Egg', protein=6, fat=5, carbs=1, calories=70,
                  entry_date=date(2026, 1, 1), entry_time=time(8), user_id=alice.id),
        FoodEntry(food_name='Rice', protein=3, fat=0, carbs=28, calories=130,
                  entry_date=date(2026, 1, 1), entry_time=time(12), user_id=bob.id),
        WaterLog(user_id=alice.id, log_date=date(2026, 1, 1), amount_ml=250),
        FriendConnection(requester_id=alice.id, recipient_id=bob.id, status='accepted'),
    ])
    tpl = MealTemplate(name='Breakfast', user_id=alice.id)
    tpl.items.append(MealTemplateItem(food_name='Egg', protein=6, fat=5, carbs=1, calories=70,
                                      serving_size=1, serving_unit='piece'))
    db.session.add(tpl)
    db.session.commit()
    alice_id, bob_id = alice.id, bob.id

    _login(client, alice_id)
    resp = client.post('/delete-account', data={'token': _token(client), 'confirm': 'DELETE'})
    assert resp.status_code == 200
    assert b'permanently deleted' in resp.data

    db.session.expire_all()
    assert db.session.get(User, alice_id) is None
    assert FoodEntry.query.filter_by(user_id=alice_id).count() == 0
    assert WaterLog.query.filter_by(user_id=alice_id).count() == 0
    assert FriendConnection.query.count() == 0
    assert MealTemplate.query.filter_by(user_id=alice_id).count() == 0
    assert MealTemplateItem.query.count() == 0
    assert db.session.get(User, bob_id) is not None
    assert FoodEntry.query.filter_by(user_id=bob_id).count() == 1
    with client.session_transaction() as sess:
        assert 'user_id' not in sess


def test_delete_requires_confirmation_word(client, auth_on):
    u = _make_user('carol')
    _login(client, u.id)
    resp = client.post('/delete-account', data={'token': _token(client), 'confirm': 'nope'})
    assert resp.status_code == 400
    assert db.session.get(User, u.id) is not None


def test_delete_rejects_missing_token(client, auth_on):
    u = _make_user('dave')
    _login(client, u.id)
    resp = client.post('/delete-account', data={'token': 'forged', 'confirm': 'DELETE'})
    assert resp.status_code == 400
    assert db.session.get(User, u.id) is not None
