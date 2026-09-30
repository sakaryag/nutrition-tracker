"""tests/test_new_routes.py

Coverage for routes not tested in test_api.py or test_family_mode.py:
  water, notes, shared, social feed, social badges, social leaderboard,
  plus auth-guard smoke tests.
"""
import json
from datetime import date, datetime, time

import pytest

from models import db
from models.user import User
from models.food_entry import FoodEntry
from models.friend_connection import FriendConnection
from models.feed_visibility import FeedVisibility


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _make_user(username):
    u = User(username=username, pw_hash="x")
    db.session.add(u)
    db.session.commit()
    return u


def _make_friends(uid_a, uid_b):
    conn = FriendConnection(requester_id=uid_a, recipient_id=uid_b, status="accepted")
    db.session.add(conn)
    db.session.commit()
    return conn


def _make_entry(user_id, food_name="Chicken", meal_type="lunch"):
    e = FoodEntry(
        food_name=food_name,
        protein=30.0, fat=5.0, carbs=0.0, calories=165,
        entry_date=date.today(),
        entry_time=time(12, 0),
        serving_size=150, serving_unit="g",
        meal_type=meal_type,
        user_id=user_id,
    )
    db.session.add(e)
    db.session.commit()
    return e


# ---------------------------------------------------------------------------
# Water
# ---------------------------------------------------------------------------

class TestWaterAPI:
    def test_get_water_empty(self, client, db_session):
        u = _make_user("w_user1")
        _auth(client, u.id)
        rv = client.get(f"/api/water?date={date.today().isoformat()}")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["total_ml"] == 0
        assert "goal_ml" in data
        assert data["logs"] == []

    def test_post_water_creates_log(self, client, db_session):
        u = _make_user("w_user2")
        _auth(client, u.id)
        rv = client.post("/api/water", json={"date": date.today().isoformat(), "amount_ml": 500})
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["amount_ml"] == 500

    def test_post_water_accumulates(self, client, db_session):
        u = _make_user("w_user3")
        _auth(client, u.id)
        today = date.today().isoformat()
        client.post("/api/water", json={"date": today, "amount_ml": 330})
        client.post("/api/water", json={"date": today, "amount_ml": 200})
        rv = client.get(f"/api/water?date={today}")
        assert rv.status_code == 200
        assert rv.get_json()["total_ml"] == 530

    def test_post_water_invalid_amount(self, client, db_session):
        u = _make_user("w_user4")
        _auth(client, u.id)
        rv = client.post("/api/water", json={"date": date.today().isoformat(), "amount_ml": 0})
        assert rv.status_code == 400

    def test_delete_water_log(self, client, db_session):
        u = _make_user("w_user5")
        _auth(client, u.id)
        rv = client.post("/api/water", json={"date": date.today().isoformat(), "amount_ml": 250})
        log_id = rv.get_json()["id"]
        rv2 = client.delete(f"/api/water/{log_id}")
        assert rv2.status_code == 200
        assert rv2.get_json()["deleted"] is True

    def test_water_invalid_date_format(self, client, db_session):
        u = _make_user("w_user6")
        _auth(client, u.id)
        rv = client.get("/api/water?date=not-a-date")
        assert rv.status_code == 400


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

class TestNotesAPI:
    def test_get_note_empty(self, client, db_session):
        u = _make_user("n_user1")
        _auth(client, u.id)
        rv = client.get(f"/api/notes?date={date.today().isoformat()}")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["content"] == ""

    def test_post_note_creates(self, client, db_session):
        u = _make_user("n_user2")
        _auth(client, u.id)
        rv = client.post("/api/notes", json={"date": date.today().isoformat(), "content": "Good day!"})
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["content"] == "Good day!"

    def test_post_note_updates_existing(self, client, db_session):
        u = _make_user("n_user3")
        _auth(client, u.id)
        today = date.today().isoformat()
        client.post("/api/notes", json={"date": today, "content": "First"})
        rv = client.post("/api/notes", json={"date": today, "content": "Updated"})
        assert rv.status_code == 200
        assert rv.get_json()["content"] == "Updated"

    def test_get_note_after_post(self, client, db_session):
        u = _make_user("n_user4")
        _auth(client, u.id)
        today = date.today().isoformat()
        client.post("/api/notes", json={"date": today, "content": "My note"})
        rv = client.get(f"/api/notes?date={today}")
        assert rv.status_code == 200
        assert rv.get_json()["content"] == "My note"

    def test_notes_invalid_date(self, client, db_session):
        u = _make_user("n_user5")
        _auth(client, u.id)
        rv = client.get("/api/notes?date=bad-date")
        assert rv.status_code == 400


# ---------------------------------------------------------------------------
# Shared entries
# ---------------------------------------------------------------------------

class TestSharedAPI:
    def test_get_incoming_empty(self, client, db_session):
        u = _make_user("sh_user1")
        _auth(client, u.id)
        rv = client.get("/api/shared/incoming")
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_post_share_to_friend(self, client, db_session):
        sender = _make_user("sh_sender")
        recip = _make_user("sh_recip")
        _make_friends(sender.id, recip.id)
        entry = _make_entry(sender.id)
        _auth(client, sender.id)
        rv = client.post("/api/shared", json={
            "entry_id": entry.id,
            "friend_ids": [recip.id],
        })
        assert rv.status_code == 201
        data = rv.get_json()
        assert len(data["shared"]) == 1
        assert data["shared"][0]["friend_id"] == recip.id

    def test_post_share_non_friend_silently_skipped(self, client, db_session):
        sender = _make_user("sh_sender2")
        stranger = _make_user("sh_stranger")
        entry = _make_entry(sender.id)
        _auth(client, sender.id)
        rv = client.post("/api/shared", json={
            "entry_id": entry.id,
            "friend_ids": [stranger.id],
        })
        assert rv.status_code == 201
        # stranger is not a friend — silently skipped
        assert rv.get_json()["shared"] == []

    def test_post_share_missing_entry_id(self, client, db_session):
        u = _make_user("sh_user3")
        _auth(client, u.id)
        rv = client.post("/api/shared", json={"friend_ids": [99]})
        assert rv.status_code == 400

    def test_post_share_missing_friend_ids(self, client, db_session):
        u = _make_user("sh_user4")
        _auth(client, u.id)
        entry = _make_entry(u.id)
        rv = client.post("/api/shared", json={"entry_id": entry.id})
        assert rv.status_code == 400

    def test_get_incoming_shows_shared_entry(self, client, db_session):
        sender = _make_user("sh_sender3")
        recip = _make_user("sh_recip2")
        _make_friends(sender.id, recip.id)
        entry = _make_entry(sender.id, food_name="Pizza")
        # Share as sender
        with client.session_transaction() as sess:
            sess["user_id"] = sender.id
        client.post("/api/shared", json={"entry_id": entry.id, "friend_ids": [recip.id]})
        # Check as recipient
        _auth(client, recip.id)
        rv = client.get("/api/shared/incoming")
        assert rv.status_code == 200
        items = rv.get_json()
        assert len(items) == 1
        assert "Pizza" in items[0]["entry"]["food_name"]


# ---------------------------------------------------------------------------
# Social feed
# ---------------------------------------------------------------------------

class TestSocialFeedAPI:
    def test_feed_empty_when_no_friends(self, client, db_session):
        u = _make_user("sf_user1")
        _auth(client, u.id)
        rv = client.get("/api/social/feed")
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_feed_excludes_friend_with_feed_hidden(self, client, db_session):
        u = _make_user("sf_user2")
        friend = _make_user("sf_friend1")
        _make_friends(u.id, friend.id)
        # Friend has show_in_feed=False (default)
        _auth(client, u.id)
        rv = client.get("/api/social/feed")
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_feed_shows_friend_with_feed_enabled(self, client, db_session):
        u = _make_user("sf_user3")
        friend = _make_user("sf_friend2")
        _make_friends(u.id, friend.id)
        # Enable friend's feed
        vis = FeedVisibility(
            user_id=friend.id,
            show_in_feed=True, show_calories=True, show_macros=True,
        )
        db.session.add(vis)
        db.session.commit()
        _auth(client, u.id)
        rv = client.get("/api/social/feed")
        assert rv.status_code == 200
        feed = rv.get_json()
        assert any(f["username"] == "sf_friend2" for f in feed)


# ---------------------------------------------------------------------------
# Social badges
# ---------------------------------------------------------------------------

class TestSocialBadgesAPI:
    def test_get_badges_empty(self, client, db_session):
        u = _make_user("bg_user1")
        _auth(client, u.id)
        rv = client.get("/api/social/badges")
        assert rv.status_code == 200
        assert isinstance(rv.get_json(), list)

    def test_badges_response_shape(self, client, db_session):
        from models.user_badge import UserBadge
        u = _make_user("bg_user2")
        badge = UserBadge(user_id=u.id, badge_key="7_day_streak", earned_at=datetime.utcnow())
        db.session.add(badge)
        db.session.commit()
        _auth(client, u.id)
        rv = client.get("/api/social/badges")
        assert rv.status_code == 200
        badges = rv.get_json()
        assert any(b["badge_key"] == "7_day_streak" for b in badges)
        if badges:
            keys = badges[0].keys()
            assert "badge_key" in keys
            assert "earned_at" in keys


# ---------------------------------------------------------------------------
# Social leaderboard
# ---------------------------------------------------------------------------

class TestSocialLeaderboardAPI:
    def test_leaderboard_includes_self(self, client, db_session):
        u = _make_user("lb_user1")
        _auth(client, u.id)
        rv = client.get("/api/social/leaderboard")
        assert rv.status_code == 200
        data = rv.get_json()
        assert "scores" in data
        assert any(s["is_me"] for s in data["scores"])

    def test_leaderboard_response_shape(self, client, db_session):
        u = _make_user("lb_user2")
        _auth(client, u.id)
        rv = client.get("/api/social/leaderboard")
        assert rv.status_code == 200
        data = rv.get_json()
        assert "week" in data
        assert "my_rank" in data
        assert "total_participants" in data


# ---------------------------------------------------------------------------
# Auth guard smoke tests (need AUTH_ENABLED=True)
# ---------------------------------------------------------------------------

class AuthConfig:
    TESTING = True
    AUTH_ENABLED = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test-auth-secret"
    DEFAULT_PROTEIN_TARGET = 150
    DEFAULT_FAT_TARGET = 65
    DEFAULT_CARBS_TARGET = 250
    DEFAULT_CALORIES_TARGET = 2200


@pytest.fixture(scope="class")
def auth_app():
    from app import create_app
    application = create_app(test_config=AuthConfig)
    with application.app_context():
        db.drop_all()
        db.create_all()
    yield application


@pytest.fixture
def auth_db(auth_app):
    with auth_app.app_context():
        db.create_all()
        yield db
        db.session.rollback()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture
def auth_client(auth_app):
    return auth_app.test_client()


class TestAuthGuards:
    def test_water_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/water")
        assert rv.status_code == 401

    def test_notes_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/notes")
        assert rv.status_code == 401

    def test_shared_incoming_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/shared/incoming")
        assert rv.status_code == 401

    def test_social_feed_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/social/feed")
        assert rv.status_code == 401

    def test_game_score_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/game/score")
        assert rv.status_code == 401

    def test_plans_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/plans/my-assignment")
        assert rv.status_code == 401
    def test_post_shared_requires_auth(self, auth_client, auth_db):
        rv = auth_client.post("/api/shared", json={})
        assert rv.status_code == 401

    def test_social_feed_visibility_get_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/social/feed/visibility")
        assert rv.status_code == 401

    def test_social_feed_visibility_put_requires_auth(self, auth_client, auth_db):
        rv = auth_client.put("/api/social/feed/visibility", json={})
        assert rv.status_code == 401

    def test_social_badges_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/social/badges")
        assert rv.status_code == 401

    def test_game_leaderboard_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/game/leaderboard")
        assert rv.status_code == 401

    def test_plans_complete_task_requires_auth(self, auth_client, auth_db):
        rv = auth_client.post("/api/plans/complete-task", json={})
        assert rv.status_code == 401

    def test_plans_progress_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/plans/progress")
        assert rv.status_code == 401