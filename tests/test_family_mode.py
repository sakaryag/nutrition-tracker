"""tests/test_family_mode.py — Family Mode: friends, social feed, game scoring, badges."""
import json
from datetime import date, timedelta

import pytest

from models import db
from models.user import User
from models.food_entry import FoodEntry
from models.daily_target import DailyTarget
from models.friend_connection import FriendConnection
from models.feed_visibility import FeedVisibility
from models.user_badge import UserBadge
from utils.game_engine import (
    calculate_daily_score,
    calculate_weekly_score,
    get_user_streak,
    check_and_award_badges,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def user_a(db_session):
    u = User(username='alice', pw_hash='x')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def user_b(db_session):
    u = User(username='bob', pw_hash='x')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def target_a(db_session, user_a):
    t = DailyTarget(
        user_id=user_a.id,
        effective_from=date(2020, 1, 1),
        protein=150, fat=65, carbs=250, calories=2200,
        water_goal_ml=2500,
    )
    db.session.add(t)
    db.session.commit()
    return t


def _add_entry(user_id, d, protein=150, fat=65, carbs=250, calories=2200):
    from datetime import time as dtime
    e = FoodEntry(
        food_name='Test', protein=protein, fat=fat, carbs=carbs, calories=calories,
        entry_date=d, entry_time=dtime(12, 0), serving_size=100, serving_unit='g',
        meal_type='Lunch', user_id=user_id,
    )
    db.session.add(e)
    db.session.commit()
    return e


# ── Friend connection API ─────────────────────────────────────────────────────

class TestFriendAPI:
    def test_send_friend_request(self, client, user_a, user_b):
        with client.session_transaction() as sess:
            sess['user_id'] = user_a.id
        rv = client.post('/api/friends/request',
                         data=json.dumps({'username': 'bob'}),
                         content_type='application/json')
        assert rv.status_code == 201
        data = rv.get_json()
        assert data['status'] == 'pending'

    def test_send_request_unknown_user(self, client, user_a):
        with client.session_transaction() as sess:
            sess['user_id'] = user_a.id
        rv = client.post('/api/friends/request',
                         data=json.dumps({'username': 'nobody'}),
                         content_type='application/json')
        assert rv.status_code == 404

    def test_send_request_to_self(self, client, user_a):
        with client.session_transaction() as sess:
            sess['user_id'] = user_a.id
        rv = client.post('/api/friends/request',
                         data=json.dumps({'username': 'alice'}),
                         content_type='application/json')
        assert rv.status_code == 400

    def test_accept_request(self, client, user_a, user_b):
        conn = FriendConnection(requester_id=user_a.id, recipient_id=user_b.id, status='pending')
        db.session.add(conn)
        db.session.commit()
        with client.session_transaction() as sess:
            sess['user_id'] = user_b.id
        rv = client.put(f'/api/friends/requests/{conn.id}/accept')
        assert rv.status_code == 200
        assert rv.get_json()['status'] == 'accepted'

    def test_decline_request(self, client, user_a, user_b):
        conn = FriendConnection(requester_id=user_a.id, recipient_id=user_b.id, status='pending')
        db.session.add(conn)
        db.session.commit()
        with client.session_transaction() as sess:
            sess['user_id'] = user_b.id
        rv = client.put(f'/api/friends/requests/{conn.id}/decline')
        assert rv.status_code == 200
        assert rv.get_json()['status'] == 'declined'

    def test_list_friends(self, client, user_a, user_b):
        conn = FriendConnection(requester_id=user_a.id, recipient_id=user_b.id, status='accepted')
        db.session.add(conn)
        db.session.commit()
        with client.session_transaction() as sess:
            sess['user_id'] = user_a.id
        rv = client.get('/api/friends')
        assert rv.status_code == 200
        data = rv.get_json()
        assert any(f['username'] == 'bob' for f in data)

    def test_remove_friend(self, client, user_a, user_b):
        conn = FriendConnection(requester_id=user_a.id, recipient_id=user_b.id, status='accepted')
        db.session.add(conn)
        db.session.commit()
        with client.session_transaction() as sess:
            sess['user_id'] = user_a.id
        rv = client.delete(f'/api/friends/{user_b.id}')
        assert rv.status_code == 200
        assert rv.get_json()['deleted'] is True


# ── Feed visibility API ───────────────────────────────────────────────────────

class TestFeedVisibility:
    def test_get_default_visibility(self, client, user_a):
        with client.session_transaction() as sess:
            sess['user_id'] = user_a.id
        rv = client.get('/api/social/feed/visibility')
        assert rv.status_code == 200
        data = rv.get_json()
        assert data['show_in_feed'] is False

    def test_update_visibility(self, client, user_a):
        with client.session_transaction() as sess:
            sess['user_id'] = user_a.id
        rv = client.put('/api/social/feed/visibility',
                        data=json.dumps({'show_in_feed': True, 'show_calories': True, 'show_macros': False}),
                        content_type='application/json')
        assert rv.status_code == 200
        data = rv.get_json()
        assert data['show_in_feed'] is True
        assert data['show_macros'] is False


# ── Game engine ───────────────────────────────────────────────────────────────

class TestGameEngine:
    def test_no_entries_score_zero(self, db_session, user_a, target_a):
        result = calculate_daily_score(user_a.id, date.today())
        assert result['total'] == 0

    def test_perfect_score(self, db_session, user_a, target_a):
        _add_entry(user_a.id, date.today(), protein=150, fat=65, carbs=250, calories=2200)
        result = calculate_daily_score(user_a.id, date.today())
        assert result['base'] == 100
        assert result['breakdown']['protein_pts'] == 25
        assert result['breakdown']['fat_pts'] == 25
        assert result['breakdown']['carbs_pts'] == 25
        assert result['breakdown']['calories_pts'] == 25

    def test_partial_score(self, db_session, user_a, target_a):
        _add_entry(user_a.id, date.today(), protein=150, fat=65, carbs=10, calories=1000)
        result = calculate_daily_score(user_a.id, date.today())
        assert result['breakdown']['protein_pts'] == 25
        assert result['breakdown']['fat_pts'] == 25
        assert result['breakdown']['carbs_pts'] == 0
        assert result['breakdown']['calories_pts'] == 0
        assert result['base'] == 50

    def test_weekly_score(self, db_session, user_a, target_a):
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        _add_entry(user_a.id, monday, protein=150, fat=65, carbs=250, calories=2200)
        result = calculate_weekly_score(user_a.id, monday)
        assert result['total'] >= 100

    def test_streak_empty(self, db_session, user_a):
        streak = get_user_streak(user_a.id)
        assert streak == 0

    def test_streak_two_days(self, db_session, user_a, target_a):
        today = date.today()
        _add_entry(user_a.id, today)
        _add_entry(user_a.id, today - timedelta(days=1))
        streak = get_user_streak(user_a.id)
        assert streak == 2


# ── Badge evaluation ──────────────────────────────────────────────────────────

class TestBadges:
    def test_no_badges_by_default(self, db_session, user_a):
        newly = check_and_award_badges(user_a.id)
        assert newly == []

    def test_streak_7_badge(self, db_session, user_a, target_a):
        today = date.today()
        for i in range(7):
            _add_entry(user_a.id, today - timedelta(days=i))
        newly = check_and_award_badges(user_a.id)
        assert '7_day_streak' in newly

    def test_badge_not_awarded_twice(self, db_session, user_a, target_a):
        today = date.today()
        for i in range(7):
            _add_entry(user_a.id, today - timedelta(days=i))
        check_and_award_badges(user_a.id)
        newly2 = check_and_award_badges(user_a.id)
        assert '7_day_streak' not in newly2

    def test_game_score_api(self, client, user_a, target_a):
        with client.session_transaction() as sess:
            sess['user_id'] = user_a.id
        rv = client.get('/api/game/score')
        assert rv.status_code == 200
        data = rv.get_json()
        assert 'score' in data
        assert 'breakdown' in data

    def test_leaderboard_api(self, client, user_a, target_a):
        with client.session_transaction() as sess:
            sess['user_id'] = user_a.id
        rv = client.get('/api/game/leaderboard')
        assert rv.status_code == 200
        data = rv.get_json()
        assert 'scores' in data
        assert any(s['is_me'] for s in data['scores'])
