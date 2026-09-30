"""tests/test_admin_routes.py

Comprehensive coverage for all /api/admin/* routes.
35+ tests covering:
  - Auth guards (401 for unauthenticated, 403 for non-admin)
  - Plan CRUD
  - Task CRUD
  - User management
  - Plan assignment
  - Program day / meal slot / slot item CRUD
  - Guidelines CRUD
  - Plan versioning
  - Template operations
"""
import pytest
from datetime import date

from models import db
from models.user import User
from models.nutrition_plan import NutritionPlan
from models.plan_task import PlanTask
from models.user_plan_assignment import UserPlanAssignment
from models.program_day import ProgramDay
from models.meal_slot import MealSlot
from models.slot_item import SlotItem
from models.program_guideline import ProgramGuideline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username, is_admin=False):
    u = User(username=username, pw_hash="x", is_admin=is_admin)
    db.session.add(u)
    db.session.commit()
    return u


def _make_plan(name="Test Plan", created_by=None):
    p = NutritionPlan(name=name, created_by=created_by)
    db.session.add(p)
    db.session.commit()
    return p


def _make_day(plan_id, day_offset=0, label="Day 1"):
    from datetime import datetime, timezone
    d = ProgramDay(
        program_id=plan_id,
        day_offset=day_offset,
        label=label,
        sort_order=day_offset,
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(d)
    db.session.commit()
    return d


def _make_slot(day_id, slot_name="Breakfast"):
    from datetime import datetime, timezone
    s = MealSlot(
        day_id=day_id,
        slot_name=slot_name,
        sort_order=0,
        content_pattern="A",
        is_optional=False,
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(s)
    db.session.commit()
    return s


def _auth(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


# ---------------------------------------------------------------------------
# Auth config (AUTH_ENABLED=True) — for auth guard tests
# ---------------------------------------------------------------------------

class AdminAuthConfig:
    TESTING = True
    AUTH_ENABLED = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "admin-test-secret"
    DEFAULT_PROTEIN_TARGET = 150
    DEFAULT_FAT_TARGET = 65
    DEFAULT_CARBS_TARGET = 250
    DEFAULT_CALORIES_TARGET = 2200


@pytest.fixture(scope="class")
def auth_app():
    from app import create_app
    application = create_app(test_config=AdminAuthConfig)
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


# ---------------------------------------------------------------------------
# Auth guard smoke tests — unauthenticated must get 401
# ---------------------------------------------------------------------------

class TestAdminAuthGuards:
    """Every admin route must return 401 for unauthenticated requests."""

    def test_list_plans_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/admin/plans")
        assert rv.status_code == 401

    def test_create_plan_requires_auth(self, auth_client, auth_db):
        rv = auth_client.post("/api/admin/plans", json={"name": "X"})
        assert rv.status_code == 401

    def test_update_plan_requires_auth(self, auth_client, auth_db):
        rv = auth_client.put("/api/admin/plans/1", json={"name": "X"})
        assert rv.status_code == 401

    def test_delete_plan_requires_auth(self, auth_client, auth_db):
        rv = auth_client.delete("/api/admin/plans/1")
        assert rv.status_code == 401

    def test_list_tasks_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/admin/plans/1/tasks")
        assert rv.status_code == 401

    def test_add_task_requires_auth(self, auth_client, auth_db):
        rv = auth_client.post("/api/admin/plans/1/tasks", json={})
        assert rv.status_code == 401

    def test_delete_task_requires_auth(self, auth_client, auth_db):
        rv = auth_client.delete("/api/admin/tasks/1")
        assert rv.status_code == 401

    def test_list_users_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/admin/users")
        assert rv.status_code == 401

    def test_update_user_requires_auth(self, auth_client, auth_db):
        rv = auth_client.put("/api/admin/users/1", json={})
        assert rv.status_code == 401

    def test_assign_plan_requires_auth(self, auth_client, auth_db):
        rv = auth_client.post("/api/admin/users/1/assign-plan", json={})
        assert rv.status_code == 401

    def test_list_days_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/admin/plans/1/days")
        assert rv.status_code == 401

    def test_add_day_requires_auth(self, auth_client, auth_db):
        rv = auth_client.post("/api/admin/plans/1/days", json={})
        assert rv.status_code == 401

    def test_update_day_requires_auth(self, auth_client, auth_db):
        rv = auth_client.put("/api/admin/days/1", json={})
        assert rv.status_code == 401

    def test_delete_day_requires_auth(self, auth_client, auth_db):
        rv = auth_client.delete("/api/admin/days/1")
        assert rv.status_code == 401

    def test_list_slots_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/admin/days/1/slots")
        assert rv.status_code == 401

    def test_add_slot_requires_auth(self, auth_client, auth_db):
        rv = auth_client.post("/api/admin/days/1/slots", json={})
        assert rv.status_code == 401

    def test_list_items_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/admin/slots/1/items")
        assert rv.status_code == 401

    def test_add_item_requires_auth(self, auth_client, auth_db):
        rv = auth_client.post("/api/admin/slots/1/items", json={})
        assert rv.status_code == 401

    def test_list_guidelines_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/admin/plans/1/guidelines")
        assert rv.status_code == 401

    def test_add_guideline_requires_auth(self, auth_client, auth_db):
        rv = auth_client.post("/api/admin/plans/1/guidelines", json={})
        assert rv.status_code == 401

    def test_list_versions_requires_auth(self, auth_client, auth_db):
        rv = auth_client.get("/api/admin/plans/1/versions")
        assert rv.status_code == 401

    def test_save_version_requires_auth(self, auth_client, auth_db):
        rv = auth_client.post("/api/admin/plans/1/versions", json={})
        assert rv.status_code == 401

    def test_promote_to_template_requires_auth(self, auth_client, auth_db):
        rv = auth_client.post("/api/admin/plans/1/promote-to-template", json={})
        assert rv.status_code == 401

    def test_clone_from_template_requires_auth(self, auth_client, auth_db):
        rv = auth_client.post("/api/admin/plans/1/clone-from-template", json={})
        assert rv.status_code == 401


# ---------------------------------------------------------------------------
# Non-admin → 403 (admin-only routes: users management)
# ---------------------------------------------------------------------------

class TestAdminNonAdminForbidden:
    """Non-admin sessions must get 403 on admin-only user management routes."""

    def test_list_users_forbidden_for_non_admin(self, auth_client, auth_db):
        # Fake user_id that either doesn't exist or is not admin → 403
        _auth(auth_client, 99999)
        rv = auth_client.get("/api/admin/users")
        assert rv.status_code == 403

    def test_update_user_forbidden_for_non_admin(self, auth_client, auth_db):
        _auth(auth_client, 99999)
        rv = auth_client.put("/api/admin/users/1", json={})
        assert rv.status_code == 403

    def test_assign_plan_forbidden_for_non_admin(self, auth_client, auth_db):
        _auth(auth_client, 99999)
        rv = auth_client.post("/api/admin/users/1/assign-plan", json={})
        assert rv.status_code == 403


# ---------------------------------------------------------------------------
# Functional tests — AUTH_ENABLED=False (use conftest fixtures)
# ---------------------------------------------------------------------------

class TestAdminPlanCRUD:
    """Plan CRUD via GET/POST/PUT/DELETE /api/admin/plans"""

    def test_list_plans_empty(self, client, db_session):
        rv = client.get("/api/admin/plans")
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_create_plan_returns_201(self, client, db_session):
        rv = client.post("/api/admin/plans", json={"name": "My Plan"})
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["name"] == "My Plan"
        assert "id" in data
        assert data["status"] == "draft"

    def test_create_plan_missing_name_returns_400(self, client, db_session):
        rv = client.post("/api/admin/plans", json={})
        assert rv.status_code == 400
        assert "name" in rv.get_json()["error"]

    def test_create_plan_blank_name_returns_400(self, client, db_session):
        rv = client.post("/api/admin/plans", json={"name": "   "})
        assert rv.status_code == 400

    def test_list_plans_shows_created_plans(self, client, db_session):
        _make_plan("Plan A")
        _make_plan("Plan B")
        rv = client.get("/api/admin/plans")
        assert rv.status_code == 200
        names = [p["name"] for p in rv.get_json()]
        assert "Plan A" in names
        assert "Plan B" in names

    def test_update_plan_name(self, client, db_session):
        p = _make_plan("Original")
        rv = client.put(f"/api/admin/plans/{p.id}", json={"name": "Updated"})
        assert rv.status_code == 200
        assert rv.get_json()["name"] == "Updated"

    def test_update_plan_description(self, client, db_session):
        p = _make_plan("Plan")
        rv = client.put(f"/api/admin/plans/{p.id}", json={"description": "A great plan"})
        assert rv.status_code == 200
        assert rv.get_json()["description"] == "A great plan"

    def test_update_plan_not_found(self, client, db_session):
        rv = client.put("/api/admin/plans/9999", json={"name": "X"})
        assert rv.status_code == 404

    def test_delete_plan(self, client, db_session):
        p = _make_plan("ToDelete")
        rv = client.delete(f"/api/admin/plans/{p.id}")
        assert rv.status_code == 200
        assert rv.get_json()["deleted"] == p.id

    def test_delete_plan_not_found(self, client, db_session):
        rv = client.delete("/api/admin/plans/9999")
        assert rv.status_code == 404

    def test_create_plan_with_duration_days(self, client, db_session):
        rv = client.post("/api/admin/plans", json={"name": "Long Plan", "duration_days": 30})
        assert rv.status_code == 201
        assert rv.get_json()["duration_days"] == 30

    def test_create_plan_as_template(self, client, db_session):
        rv = client.post("/api/admin/plans", json={"name": "Template", "is_template": True})
        assert rv.status_code == 201
        assert rv.get_json()["is_template"] is True

    def test_filter_plans_by_is_template(self, client, db_session):
        _make_plan("Regular")
        p = _make_plan("Template")
        client.put(f"/api/admin/plans/{p.id}", json={"is_template": True})
        rv = client.get("/api/admin/plans?is_template=1")
        assert rv.status_code == 200
        assert all(pl["is_template"] for pl in rv.get_json())


# ---------------------------------------------------------------------------
# Task CRUD
# ---------------------------------------------------------------------------

class TestAdminTaskCRUD:
    """Task CRUD via plans/<id>/tasks and tasks/<id>"""

    def test_list_tasks_empty(self, client, db_session):
        p = _make_plan()
        rv = client.get(f"/api/admin/plans/{p.id}/tasks")
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_add_task_returns_201(self, client, db_session):
        p = _make_plan()
        rv = client.post(f"/api/admin/plans/{p.id}/tasks", json={
            "description": "Eat salad",
            "task_type": "food",
        })
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["description"] == "Eat salad"
        assert data["task_type"] == "food"
        assert data["plan_id"] == p.id

    def test_add_task_missing_description_returns_400(self, client, db_session):
        p = _make_plan()
        rv = client.post(f"/api/admin/plans/{p.id}/tasks", json={"task_type": "food"})
        assert rv.status_code == 400

    def test_add_task_invalid_task_type_returns_400(self, client, db_session):
        p = _make_plan()
        rv = client.post(f"/api/admin/plans/{p.id}/tasks", json={
            "description": "Something",
            "task_type": "invalid_type",
        })
        assert rv.status_code == 400

    def test_add_task_habit_type(self, client, db_session):
        p = _make_plan()
        rv = client.post(f"/api/admin/plans/{p.id}/tasks", json={
            "description": "Walk 30 min",
            "task_type": "habit",
        })
        assert rv.status_code == 201
        assert rv.get_json()["task_type"] == "habit"

    def test_add_task_note_type(self, client, db_session):
        p = _make_plan()
        rv = client.post(f"/api/admin/plans/{p.id}/tasks", json={
            "description": "Write journal",
            "task_type": "note",
        })
        assert rv.status_code == 201

    def test_list_tasks_plan_not_found(self, client, db_session):
        rv = client.get("/api/admin/plans/9999/tasks")
        assert rv.status_code == 404

    def test_add_task_plan_not_found(self, client, db_session):
        rv = client.post("/api/admin/plans/9999/tasks", json={
            "description": "X", "task_type": "food",
        })
        assert rv.status_code == 404

    def test_delete_task(self, client, db_session):
        p = _make_plan()
        resp = client.post(f"/api/admin/plans/{p.id}/tasks", json={
            "description": "Del task", "task_type": "food",
        })
        task_id = resp.get_json()["id"]
        rv = client.delete(f"/api/admin/tasks/{task_id}")
        assert rv.status_code == 200
        assert rv.get_json()["deleted"] == task_id

    def test_delete_task_not_found(self, client, db_session):
        rv = client.delete("/api/admin/tasks/9999")
        assert rv.status_code == 404

    def test_task_with_day_offset_and_food_name(self, client, db_session):
        p = _make_plan()
        rv = client.post(f"/api/admin/plans/{p.id}/tasks", json={
            "description": "Drink protein shake",
            "task_type": "food",
            "food_name": "Whey protein",
            "quantity": 30.0,
            "unit": "g",
            "day_offset": 2,
        })
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["food_name"] == "Whey protein"
        assert data["day_offset"] == 2


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------

class TestAdminUserManagement:
    """User management via users/ and users/<id>"""

    def test_list_users_returns_all(self, client, db_session):
        _make_user("alice")
        _make_user("bob")
        rv = client.get("/api/admin/users")
        assert rv.status_code == 200
        usernames = [u["username"] for u in rv.get_json()]
        assert "alice" in usernames
        assert "bob" in usernames

    def test_list_users_response_shape(self, client, db_session):
        _make_user("charlie")
        rv = client.get("/api/admin/users")
        assert rv.status_code == 200
        u = rv.get_json()[0]
        for key in ("id", "username", "is_admin", "plan_feature_enabled", "active_plan_name"):
            assert key in u, f"Missing key: {key}"

    def test_update_user_plan_feature_enabled(self, client, db_session):
        u = _make_user("diana")
        rv = client.put(f"/api/admin/users/{u.id}", json={"plan_feature_enabled": True})
        assert rv.status_code == 200
        assert rv.get_json()["plan_feature_enabled"] is True

    def test_update_user_is_admin_flag(self, client, db_session):
        u = _make_user("evan")
        rv = client.put(f"/api/admin/users/{u.id}", json={"is_admin": True})
        assert rv.status_code == 200
        assert rv.get_json()["is_admin"] is True

    def test_update_user_not_found(self, client, db_session):
        rv = client.put("/api/admin/users/9999", json={"is_admin": True})
        assert rv.status_code == 404


# ---------------------------------------------------------------------------
# Plan Assignment
# ---------------------------------------------------------------------------

class TestAdminPlanAssignment:
    """Plan assignment via users/<id>/assign-plan"""

    def test_assign_plan_creates_assignment(self, client, db_session):
        u = _make_user("assignee1")
        p = _make_plan("Diet Plan")
        rv = client.post(f"/api/admin/users/{u.id}/assign-plan", json={
            "plan_id": p.id,
            "start_date": date.today().isoformat(),
        })
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["user_id"] == u.id
        assert data["plan_id"] == p.id
        assert data["is_active"] is True

    def test_assign_plan_defaults_to_today(self, client, db_session):
        u = _make_user("assignee_today")
        p = _make_plan("Plan T")
        rv = client.post(f"/api/admin/users/{u.id}/assign-plan", json={"plan_id": p.id})
        assert rv.status_code == 201
        assert rv.get_json()["start_date"] == date.today().isoformat()

    def test_assign_plan_missing_plan_id_returns_400(self, client, db_session):
        u = _make_user("assignee2")
        rv = client.post(f"/api/admin/users/{u.id}/assign-plan", json={})
        assert rv.status_code == 400

    def test_assign_plan_nonexistent_plan_returns_404(self, client, db_session):
        u = _make_user("assignee3")
        rv = client.post(f"/api/admin/users/{u.id}/assign-plan", json={"plan_id": 9999})
        assert rv.status_code == 404

    def test_assign_plan_user_not_found_returns_404(self, client, db_session):
        p = _make_plan("Plan X")
        rv = client.post("/api/admin/users/9999/assign-plan", json={"plan_id": p.id})
        assert rv.status_code == 404

    def test_reassign_plan_deactivates_previous(self, client, db_session):
        u = _make_user("reassignee")
        p1 = _make_plan("Plan 1")
        p2 = _make_plan("Plan 2")
        client.post(f"/api/admin/users/{u.id}/assign-plan", json={"plan_id": p1.id})
        client.post(f"/api/admin/users/{u.id}/assign-plan", json={"plan_id": p2.id})
        active = UserPlanAssignment.query.filter_by(user_id=u.id, is_active=True).all()
        assert len(active) == 1
        assert active[0].plan_id == p2.id


# ---------------------------------------------------------------------------
# Program Day CRUD
# ---------------------------------------------------------------------------

class TestAdminDayCRUD:
    """Program day CRUD via plans/<id>/days and days/<id>"""

    def test_list_days_empty(self, client, db_session):
        p = _make_plan()
        rv = client.get(f"/api/admin/plans/{p.id}/days")
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_add_day_returns_201(self, client, db_session):
        p = _make_plan()
        rv = client.post(f"/api/admin/plans/{p.id}/days", json={"label": "Day 1"})
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["label"] == "Day 1"
        assert data["program_id"] == p.id

    def test_add_day_auto_assigns_offset(self, client, db_session):
        p = _make_plan()
        rv = client.post(f"/api/admin/plans/{p.id}/days", json={})
        assert rv.status_code == 201
        assert rv.get_json()["day_offset"] == 0

    def test_add_day_increments_offset(self, client, db_session):
        p = _make_plan()
        client.post(f"/api/admin/plans/{p.id}/days", json={})
        rv = client.post(f"/api/admin/plans/{p.id}/days", json={})
        assert rv.status_code == 201
        assert rv.get_json()["day_offset"] == 1

    def test_add_day_plan_not_found(self, client, db_session):
        rv = client.post("/api/admin/plans/9999/days", json={})
        assert rv.status_code == 404

    def test_update_day_label(self, client, db_session):
        p = _make_plan()
        d = _make_day(p.id, label="Old Label")
        rv = client.put(f"/api/admin/days/{d.id}", json={"label": "New Label"})
        assert rv.status_code == 200
        assert rv.get_json()["label"] == "New Label"

    def test_update_day_not_found(self, client, db_session):
        rv = client.put("/api/admin/days/9999", json={"label": "X"})
        assert rv.status_code == 404

    def test_delete_day(self, client, db_session):
        p = _make_plan()
        d = _make_day(p.id)
        rv = client.delete(f"/api/admin/days/{d.id}")
        assert rv.status_code == 200
        assert rv.get_json()["deleted"] == d.id

    def test_delete_day_not_found(self, client, db_session):
        rv = client.delete("/api/admin/days/9999")
        assert rv.status_code == 404

    def test_copy_day(self, client, db_session):
        p = _make_plan()
        d = _make_day(p.id, label="Source Day")
        rv = client.post(f"/api/admin/days/{d.id}/copy", json={})
        assert rv.status_code == 201
        data = rv.get_json()
        assert "Source Day" in data["label"]
        assert data["program_id"] == p.id

    def test_copy_day_not_found(self, client, db_session):
        rv = client.post("/api/admin/days/9999/copy", json={})
        assert rv.status_code == 404


# ---------------------------------------------------------------------------
# Meal Slot CRUD
# ---------------------------------------------------------------------------

class TestAdminSlotCRUD:
    """Meal slot CRUD via days/<id>/slots and slots/<id>"""

    def test_list_slots_empty(self, client, db_session):
        p = _make_plan()
        d = _make_day(p.id)
        rv = client.get(f"/api/admin/days/{d.id}/slots")
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_add_slot_returns_201(self, client, db_session):
        p = _make_plan()
        d = _make_day(p.id)
        rv = client.post(f"/api/admin/days/{d.id}/slots", json={"slot_name": "Breakfast"})
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["slot_name"] == "Breakfast"
        assert data["day_id"] == d.id

    def test_add_slot_missing_slot_name_returns_400(self, client, db_session):
        p = _make_plan()
        d = _make_day(p.id)
        rv = client.post(f"/api/admin/days/{d.id}/slots", json={})
        assert rv.status_code == 400
        assert "slot_name" in rv.get_json()["error"]

    def test_add_slot_day_not_found(self, client, db_session):
        rv = client.post("/api/admin/days/9999/slots", json={"slot_name": "Lunch"})
        assert rv.status_code == 404

    def test_update_slot_name(self, client, db_session):
        p = _make_plan()
        d = _make_day(p.id)
        s = _make_slot(d.id, "Breakfast")
        rv = client.put(f"/api/admin/slots/{s.id}", json={"slot_name": "Lunch"})
        assert rv.status_code == 200
        assert rv.get_json()["slot_name"] == "Lunch"

    def test_update_slot_not_found(self, client, db_session):
        rv = client.put("/api/admin/slots/9999", json={"slot_name": "X"})
        assert rv.status_code == 404

    def test_delete_slot(self, client, db_session):
        p = _make_plan()
        d = _make_day(p.id)
        s = _make_slot(d.id)
        rv = client.delete(f"/api/admin/slots/{s.id}")
        assert rv.status_code == 200
        assert rv.get_json()["deleted"] == s.id

    def test_delete_slot_not_found(self, client, db_session):
        rv = client.delete("/api/admin/slots/9999")
        assert rv.status_code == 404


# ---------------------------------------------------------------------------
# Slot Item CRUD
# ---------------------------------------------------------------------------

class TestAdminSlotItemCRUD:
    """Slot item CRUD via slots/<id>/items and slot-items/<id>"""

    def test_list_items_empty(self, client, db_session):
        p = _make_plan()
        d = _make_day(p.id)
        s = _make_slot(d.id)
        rv = client.get(f"/api/admin/slots/{s.id}/items")
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_add_item_free_text_returns_201(self, client, db_session):
        p = _make_plan()
        d = _make_day(p.id)
        s = _make_slot(d.id)
        rv = client.post(f"/api/admin/slots/{s.id}/items", json={
            "food_name_override": "Chicken breast",
            "quantity": 150,
            "unit": "g",
            "protein": 30.0,
            "fat": 5.0,
            "carbs": 0.0,
            "calories": 165.0,
        })
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["food_name_override"] == "Chicken breast"
        assert data["protein"] == 30.0
        assert data["slot_id"] == s.id

    def test_add_item_minimal_payload(self, client, db_session):
        p = _make_plan()
        d = _make_day(p.id)
        s = _make_slot(d.id)
        rv = client.post(f"/api/admin/slots/{s.id}/items", json={})
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["protein"] == 0.0

    def test_add_item_slot_not_found(self, client, db_session):
        rv = client.post("/api/admin/slots/9999/items", json={})
        assert rv.status_code == 404

    def test_update_item_macros(self, client, db_session):
        p = _make_plan()
        d = _make_day(p.id)
        s = _make_slot(d.id)
        resp = client.post(f"/api/admin/slots/{s.id}/items", json={
            "protein": 6.0, "fat": 5.0, "carbs": 0.5, "calories": 72.0,
        })
        item_id = resp.get_json()["id"]
        rv = client.put(f"/api/admin/slot-items/{item_id}", json={"protein": 8.0})
        assert rv.status_code == 200
        assert rv.get_json()["protein"] == 8.0

    def test_update_item_not_found(self, client, db_session):
        rv = client.put("/api/admin/slot-items/9999", json={"protein": 1.0})
        assert rv.status_code == 404

    def test_delete_item(self, client, db_session):
        p = _make_plan()
        d = _make_day(p.id)
        s = _make_slot(d.id)
        resp = client.post(f"/api/admin/slots/{s.id}/items", json={})
        item_id = resp.get_json()["id"]
        rv = client.delete(f"/api/admin/slot-items/{item_id}")
        assert rv.status_code == 200
        assert rv.get_json()["deleted"] == item_id

    def test_delete_item_not_found(self, client, db_session):
        rv = client.delete("/api/admin/slot-items/9999")
        assert rv.status_code == 404


# ---------------------------------------------------------------------------
# Guideline CRUD
# ---------------------------------------------------------------------------

class TestAdminGuidelineCRUD:
    """Guideline CRUD via plans/<id>/guidelines and guidelines/<id>"""

    def test_list_guidelines_empty(self, client, db_session):
        p = _make_plan()
        rv = client.get(f"/api/admin/plans/{p.id}/guidelines")
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_add_guideline_returns_201(self, client, db_session):
        p = _make_plan()
        rv = client.post(f"/api/admin/plans/{p.id}/guidelines", json={
            "rule_text": "Avoid processed sugar",
            "guideline_type": "general",
        })
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["rule_text"] == "Avoid processed sugar"
        assert data["program_id"] == p.id

    def test_add_guideline_missing_rule_text_returns_400(self, client, db_session):
        p = _make_plan()
        rv = client.post(f"/api/admin/plans/{p.id}/guidelines", json={})
        assert rv.status_code == 400
        assert "rule_text" in rv.get_json()["error"]

    def test_add_guideline_plan_not_found(self, client, db_session):
        rv = client.post("/api/admin/plans/9999/guidelines", json={"rule_text": "X"})
        assert rv.status_code == 404

    def test_update_guideline(self, client, db_session):
        p = _make_plan()
        resp = client.post(f"/api/admin/plans/{p.id}/guidelines", json={
            "rule_text": "Drink water", "guideline_type": "general",
        })
        gid = resp.get_json()["id"]
        rv = client.put(f"/api/admin/guidelines/{gid}", json={"rule_text": "Drink 2L water"})
        assert rv.status_code == 200
        assert rv.get_json()["rule_text"] == "Drink 2L water"

    def test_update_guideline_not_found(self, client, db_session):
        rv = client.put("/api/admin/guidelines/9999", json={"rule_text": "X"})
        assert rv.status_code == 404

    def test_delete_guideline(self, client, db_session):
        p = _make_plan()
        resp = client.post(f"/api/admin/plans/{p.id}/guidelines", json={
            "rule_text": "No sugar", "guideline_type": "general",
        })
        gid = resp.get_json()["id"]
        rv = client.delete(f"/api/admin/guidelines/{gid}")
        assert rv.status_code == 200
        assert rv.get_json()["deleted"] == gid

    def test_delete_guideline_not_found(self, client, db_session):
        rv = client.delete("/api/admin/guidelines/9999")
        assert rv.status_code == 404


# ---------------------------------------------------------------------------
# Plan Versioning
# ---------------------------------------------------------------------------

class TestAdminVersioning:
    """Plan versioning via plans/<id>/versions"""

    def test_list_versions_empty(self, client, db_session):
        p = _make_plan()
        rv = client.get(f"/api/admin/plans/{p.id}/versions")
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_list_versions_plan_not_found(self, client, db_session):
        rv = client.get("/api/admin/plans/9999/versions")
        assert rv.status_code == 404

    def test_save_version_returns_201(self, client, db_session):
        p = _make_plan("Versioned Plan")
        rv = client.post(f"/api/admin/plans/{p.id}/versions", json={
            "change_summary": "Initial version",
        })
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["version_number"] == 1
        assert data["program_id"] == p.id

    def test_save_multiple_versions_increments_number(self, client, db_session):
        p = _make_plan("Multi-version Plan")
        client.post(f"/api/admin/plans/{p.id}/versions", json={"change_summary": "v1"})
        rv = client.post(f"/api/admin/plans/{p.id}/versions", json={"change_summary": "v2"})
        assert rv.status_code == 201
        assert rv.get_json()["version_number"] == 2

    def test_get_specific_version(self, client, db_session):
        p = _make_plan("Plan with versions")
        client.post(f"/api/admin/plans/{p.id}/versions", json={"change_summary": "First"})
        rv = client.get(f"/api/admin/plans/{p.id}/versions/1")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["version_number"] == 1
        assert "snapshot_json" in data

    def test_get_version_not_found(self, client, db_session):
        p = _make_plan()
        rv = client.get(f"/api/admin/plans/{p.id}/versions/999")
        assert rv.status_code == 404


# ---------------------------------------------------------------------------
# Template operations
# ---------------------------------------------------------------------------

class TestAdminTemplateOps:
    """promote-to-template and clone-from-template"""

    def test_promote_to_template(self, client, db_session):
        p = _make_plan("Working Plan")
        assert p.is_template is False
        rv = client.post(f"/api/admin/plans/{p.id}/promote-to-template", json={})
        assert rv.status_code == 200
        assert rv.get_json()["is_template"] is True

    def test_promote_to_template_not_found(self, client, db_session):
        rv = client.post("/api/admin/plans/9999/promote-to-template", json={})
        assert rv.status_code == 404

    def test_clone_from_template(self, client, db_session):
        source = _make_plan("Source Template")
        client.post(f"/api/admin/plans/{source.id}/promote-to-template", json={})
        rv = client.post(f"/api/admin/plans/{source.id}/clone-from-template", json={
            "name": "Cloned Plan",
        })
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["name"] == "Cloned Plan"
        assert data["is_template"] is False
        assert data["parent_template_id"] == source.id

    def test_clone_from_template_default_name(self, client, db_session):
        source = _make_plan("My Template")
        rv = client.post(f"/api/admin/plans/{source.id}/clone-from-template", json={})
        assert rv.status_code == 201
        assert "copy" in rv.get_json()["name"].lower()

    def test_clone_not_found(self, client, db_session):
        rv = client.post("/api/admin/plans/9999/clone-from-template", json={})
        assert rv.status_code == 404
