"""tests/test_dietitian_mode.py — Dietitian Mode: recipes, exchange categories,
plan builder (days/slots/items/guidelines/quotas/versions), slot fulfillment,
and image extraction pipeline (Anthropic calls mocked).
"""
import io
import json
from datetime import date
from unittest.mock import patch

import pytest

from models import db
from models.user import User
from models.nutrition_plan import NutritionPlan
from models.user_plan_assignment import UserPlanAssignment


# ── Module-level fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def admin_user(db_session):
    u = User(username='admin_tester', pw_hash='x')
    u.is_admin = True
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def authed_client(client, admin_user):
    """Client with admin user already in session."""
    with client.session_transaction() as sess:
        sess['user_id'] = admin_user.id
    return client, admin_user


# ── Low-level helpers ─────────────────────────────────────────────────────────

def _mk_plan(name='Test Plan', duration=7):
    p = NutritionPlan(name=name, duration_days=duration, status='draft',
                      is_template=False, locale='en')
    db.session.add(p)
    db.session.commit()
    return p


def _mk_day(plan_id, offset=0, label='Day 1'):
    from models.program_day import ProgramDay
    from datetime import datetime, timezone
    d = ProgramDay(program_id=plan_id, day_offset=offset, label=label,
                   sort_order=offset, created_at=datetime.now(timezone.utc))
    db.session.add(d)
    db.session.commit()
    return d


def _mk_slot(day_id, slot_name='Breakfast'):
    from models.meal_slot import MealSlot
    from datetime import datetime, timezone
    s = MealSlot(day_id=day_id, slot_name=slot_name, sort_order=0,
                 content_pattern='A', is_optional=False,
                 created_at=datetime.now(timezone.utc))
    db.session.add(s)
    db.session.commit()
    return s


# ── Recipe CRUD API ───────────────────────────────────────────────────────────

class TestRecipeAPI:

    def test_list_recipes_empty(self, authed_client):
        client, _ = authed_client
        resp = client.get('/api/recipes')
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_create_recipe(self, authed_client):
        client, _ = authed_client
        resp = client.post('/api/recipes', json={
            'name': 'Avocado Toast',
            'prep_notes': 'Toast the bread first.',
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'Avocado Toast'
        assert data['prep_notes'] == 'Toast the bread first.'
        assert data['id'] is not None

    def test_create_recipe_requires_name(self, authed_client):
        client, _ = authed_client
        resp = client.post('/api/recipes', json={'prep_notes': 'No name here'})
        assert resp.status_code == 400

    def test_create_recipe_with_turkish_name(self, authed_client):
        client, _ = authed_client
        resp = client.post('/api/recipes', json={
            'name': 'Chicken Salad',
            'name_tr': 'Tavuk Salatası',
        })
        assert resp.status_code == 201
        assert resp.get_json()['name_tr'] == 'Tavuk Salatası'

    def test_list_recipes_shows_created(self, authed_client):
        client, _ = authed_client
        client.post('/api/recipes', json={'name': 'Recipe Alpha'})
        client.post('/api/recipes', json={'name': 'Recipe Beta'})
        resp = client.get('/api/recipes')
        names = [r['name'] for r in resp.get_json()]
        assert 'Recipe Alpha' in names
        assert 'Recipe Beta' in names

    def test_list_recipes_search(self, authed_client):
        client, _ = authed_client
        client.post('/api/recipes', json={'name': 'Egg Omelette'})
        client.post('/api/recipes', json={'name': 'Pancakes'})
        resp = client.get('/api/recipes?q=omelette')
        results = resp.get_json()
        assert len(results) == 1
        assert results[0]['name'] == 'Egg Omelette'

    def test_get_recipe(self, authed_client):
        client, _ = authed_client
        r = client.post('/api/recipes', json={'name': 'Soup'}).get_json()
        resp = client.get(f'/api/recipes/{r["id"]}')
        assert resp.status_code == 200
        assert resp.get_json()['name'] == 'Soup'

    def test_get_recipe_not_found(self, authed_client):
        client, _ = authed_client
        assert client.get('/api/recipes/9999').status_code == 404

    def test_update_recipe_name(self, authed_client):
        client, _ = authed_client
        r = client.post('/api/recipes', json={'name': 'Old Name'}).get_json()
        resp = client.put(f'/api/recipes/{r["id"]}', json={'name': 'New Name'})
        assert resp.status_code == 200
        assert resp.get_json()['name'] == 'New Name'

    def test_update_recipe_prep_notes(self, authed_client):
        client, _ = authed_client
        r = client.post('/api/recipes', json={'name': 'Salad'}).get_json()
        resp = client.put(f'/api/recipes/{r["id"]}', json={'prep_notes': 'Toss well.'})
        assert resp.status_code == 200
        assert resp.get_json()['prep_notes'] == 'Toss well.'

    def test_delete_recipe(self, authed_client):
        client, _ = authed_client
        r = client.post('/api/recipes', json={'name': 'To Delete'}).get_json()
        resp = client.delete(f'/api/recipes/{r["id"]}')
        assert resp.status_code == 200
        assert resp.get_json()['deleted'] == r['id']
        assert client.get(f'/api/recipes/{r["id"]}').status_code == 404

    def test_archived_recipe_hidden_from_list(self, authed_client):
        client, _ = authed_client
        r = client.post('/api/recipes', json={'name': 'Archived'}).get_json()
        client.put(f'/api/recipes/{r["id"]}', json={'is_archived': True})
        names = [x['name'] for x in client.get('/api/recipes').get_json()]
        assert 'Archived' not in names


# ── Exchange Category CRUD API ────────────────────────────────────────────────

class TestExchangeCategoryAPI:

    def test_list_empty(self, authed_client):
        client, _ = authed_client
        assert client.get('/api/exchange-categories').get_json() == []

    def test_create_category(self, authed_client):
        client, _ = authed_client
        resp = client.post('/api/exchange-categories', json={
            'name': 'Protein Group',
            'description': 'High-protein foods',
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'Protein Group'

    def test_create_requires_name(self, authed_client):
        client, _ = authed_client
        assert client.post('/api/exchange-categories', json={'description': 'oops'}).status_code == 400

    def test_create_duplicate_name_rejected(self, authed_client):
        client, _ = authed_client
        client.post('/api/exchange-categories', json={'name': 'Carbs'})
        assert client.post('/api/exchange-categories', json={'name': 'Carbs'}).status_code == 409

    def test_list_shows_created(self, authed_client):
        client, _ = authed_client
        client.post('/api/exchange-categories', json={'name': 'Fats'})
        client.post('/api/exchange-categories', json={'name': 'Vegetables'})
        names = [c['name'] for c in client.get('/api/exchange-categories').get_json()]
        assert 'Fats' in names
        assert 'Vegetables' in names

    def test_search_filter(self, authed_client):
        client, _ = authed_client
        client.post('/api/exchange-categories', json={'name': 'Whole Grains'})
        client.post('/api/exchange-categories', json={'name': 'Leafy Greens'})
        results = client.get('/api/exchange-categories?q=grain').get_json()
        assert len(results) == 1
        assert results[0]['name'] == 'Whole Grains'

    def test_get_category(self, authed_client):
        client, _ = authed_client
        c = client.post('/api/exchange-categories', json={'name': 'Dairy'}).get_json()
        resp = client.get(f'/api/exchange-categories/{c["id"]}')
        assert resp.status_code == 200
        assert resp.get_json()['name'] == 'Dairy'

    def test_get_not_found(self, authed_client):
        client, _ = authed_client
        assert client.get('/api/exchange-categories/9999').status_code == 404

    def test_update_name(self, authed_client):
        client, _ = authed_client
        c = client.post('/api/exchange-categories', json={'name': 'OldCat'}).get_json()
        resp = client.put(f'/api/exchange-categories/{c["id"]}', json={'name': 'NewCat'})
        assert resp.status_code == 200
        assert resp.get_json()['name'] == 'NewCat'

    def test_delete_category(self, authed_client):
        client, _ = authed_client
        c = client.post('/api/exchange-categories', json={'name': 'ToDelete'}).get_json()
        resp = client.delete(f'/api/exchange-categories/{c["id"]}')
        assert resp.status_code == 200
        assert resp.get_json()['deleted'] == c['id']
        assert client.get(f'/api/exchange-categories/{c["id"]}').status_code == 404

    def test_create_with_members(self, authed_client):
        client, _ = authed_client
        resp = client.post('/api/exchange-categories', json={
            'name': 'Lean Meats',
            'members': [
                {'food_name_override': 'Chicken Breast', 'equivalent_qty': 100, 'equivalent_unit': 'g'},
            ],
        })
        assert resp.status_code == 201
        assert resp.get_json()['name'] == 'Lean Meats'


# ── Admin Plan Builder API ────────────────────────────────────────────────────

class TestAdminPlanAPI:

    def test_create_plan(self, client):
        resp = client.post('/api/admin/plans', json={'name': 'Mediterranean Diet'})
        assert resp.status_code == 201
        assert resp.get_json()['name'] == 'Mediterranean Diet'

    def test_create_plan_requires_name(self, client):
        assert client.post('/api/admin/plans', json={}).status_code == 400

    def test_list_plans(self, client):
        client.post('/api/admin/plans', json={'name': 'Plan A'})
        client.post('/api/admin/plans', json={'name': 'Plan B'})
        names = [p['name'] for p in client.get('/api/admin/plans').get_json()]
        assert 'Plan A' in names
        assert 'Plan B' in names

    def test_update_plan(self, client):
        p = client.post('/api/admin/plans', json={'name': 'Old'}).get_json()
        resp = client.put(f'/api/admin/plans/{p["id"]}', json={'name': 'Updated', 'status': 'active'})
        assert resp.status_code == 200
        assert resp.get_json()['name'] == 'Updated'

    def test_delete_plan(self, client, db_session):
        p = _mk_plan()
        resp = client.delete(f'/api/admin/plans/{p.id}')
        assert resp.status_code == 200
        assert resp.get_json()['deleted'] == p.id

    def test_list_templates_only(self, client):
        client.post('/api/admin/plans', json={'name': 'Template', 'is_template': True})
        client.post('/api/admin/plans', json={'name': 'Normal'})
        names = [p['name'] for p in client.get('/api/admin/plans?is_template=1').get_json()]
        assert 'Template' in names
        assert 'Normal' not in names


class TestPlanDaysAPI:

    def test_add_day(self, client, db_session):
        plan = _mk_plan()
        resp = client.post(f'/api/admin/plans/{plan.id}/days', json={'label': 'Monday'})
        assert resp.status_code == 201
        assert resp.get_json()['label'] == 'Monday'

    def test_list_days(self, client, db_session):
        plan = _mk_plan()
        _mk_day(plan.id, 0, 'Day 1')
        _mk_day(plan.id, 1, 'Day 2')
        resp = client.get(f'/api/admin/plans/{plan.id}/days')
        assert resp.status_code == 200
        assert len(resp.get_json()) == 2

    def test_update_day(self, client, db_session):
        plan = _mk_plan()
        day = _mk_day(plan.id, 0, 'Old Label')
        resp = client.put(f'/api/admin/days/{day.id}', json={'label': 'New Label'})
        assert resp.status_code == 200
        assert resp.get_json()['label'] == 'New Label'

    def test_delete_day(self, client, db_session):
        plan = _mk_plan()
        day = _mk_day(plan.id)
        resp = client.delete(f'/api/admin/days/{day.id}')
        assert resp.status_code == 200
        assert resp.get_json()['deleted'] == day.id

    def test_plan_not_found_returns_404(self, client):
        assert client.get('/api/admin/plans/9999/days').status_code == 404

    def test_auto_increment_day_offset(self, client, db_session):
        plan = _mk_plan()
        d0 = client.post(f'/api/admin/plans/{plan.id}/days', json={}).get_json()
        d1 = client.post(f'/api/admin/plans/{plan.id}/days', json={}).get_json()
        assert d0['day_offset'] == 0
        assert d1['day_offset'] == 1


class TestPlanSlotsAPI:

    def test_add_slot(self, client, db_session):
        plan = _mk_plan()
        day = _mk_day(plan.id)
        resp = client.post(f'/api/admin/days/{day.id}/slots', json={
            'slot_name': 'Breakfast', 'content_pattern': 'A',
        })
        assert resp.status_code == 201
        assert resp.get_json()['slot_name'] == 'Breakfast'

    def test_add_slot_requires_name(self, client, db_session):
        plan = _mk_plan()
        day = _mk_day(plan.id)
        assert client.post(f'/api/admin/days/{day.id}/slots', json={}).status_code == 400

    def test_list_slots(self, client, db_session):
        plan = _mk_plan()
        day = _mk_day(plan.id)
        _mk_slot(day.id, 'Breakfast')
        _mk_slot(day.id, 'Lunch')
        names = [s['slot_name'] for s in client.get(f'/api/admin/days/{day.id}/slots').get_json()]
        assert 'Breakfast' in names
        assert 'Lunch' in names

    def test_update_slot(self, client, db_session):
        plan = _mk_plan()
        day = _mk_day(plan.id)
        slot = _mk_slot(day.id, 'Old Slot')
        resp = client.put(f'/api/admin/slots/{slot.id}', json={'slot_name': 'New Slot', 'is_optional': True})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['slot_name'] == 'New Slot'
        assert data['is_optional'] is True

    def test_delete_slot(self, client, db_session):
        plan = _mk_plan()
        day = _mk_day(plan.id)
        slot = _mk_slot(day.id, 'Snack')
        resp = client.delete(f'/api/admin/slots/{slot.id}')
        assert resp.status_code == 200
        assert resp.get_json()['deleted'] == slot.id

    def test_add_slot_item(self, client, db_session):
        plan = _mk_plan()
        day = _mk_day(plan.id)
        slot = _mk_slot(day.id, 'Dinner')
        resp = client.post(f'/api/admin/slots/{slot.id}/items', json={
            'food_name_override': 'Grilled Fish', 'quantity': 150, 'unit': 'g',
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['food_name_override'] == 'Grilled Fish'
        assert data['quantity'] == 150.0

    def test_delete_slot_item(self, client, db_session):
        plan = _mk_plan()
        day = _mk_day(plan.id)
        slot = _mk_slot(day.id)
        item = client.post(f'/api/admin/slots/{slot.id}/items', json={
            'food_name_override': 'Egg', 'quantity': 50, 'unit': 'g',
        }).get_json()
        resp = client.delete(f'/api/admin/slot-items/{item["id"]}')
        assert resp.status_code == 200
        assert resp.get_json()['deleted'] == item['id']


class TestPlanGuidelinesAPI:

    def test_add_guideline(self, client, db_session):
        plan = _mk_plan()
        resp = client.post(f'/api/admin/plans/{plan.id}/guidelines', json={
            'rule_text': 'Eat 5 portions of vegetables per day.',
            'guideline_type': 'general',
        })
        assert resp.status_code == 201
        assert resp.get_json()['rule_text'] == 'Eat 5 portions of vegetables per day.'

    def test_add_guideline_requires_rule_text(self, client, db_session):
        plan = _mk_plan()
        assert client.post(f'/api/admin/plans/{plan.id}/guidelines',
                           json={'guideline_type': 'general'}).status_code == 400

    def test_list_guidelines(self, client, db_session):
        plan = _mk_plan()
        client.post(f'/api/admin/plans/{plan.id}/guidelines', json={'rule_text': 'Rule 1'})
        client.post(f'/api/admin/plans/{plan.id}/guidelines', json={'rule_text': 'Rule 2'})
        assert len(client.get(f'/api/admin/plans/{plan.id}/guidelines').get_json()) == 2

    def test_update_guideline(self, client, db_session):
        plan = _mk_plan()
        g = client.post(f'/api/admin/plans/{plan.id}/guidelines', json={'rule_text': 'Old'}).get_json()
        resp = client.put(f'/api/admin/guidelines/{g["id"]}', json={'rule_text': 'New'})
        assert resp.status_code == 200
        assert resp.get_json()['rule_text'] == 'New'

    def test_delete_guideline(self, client, db_session):
        plan = _mk_plan()
        g = client.post(f'/api/admin/plans/{plan.id}/guidelines', json={'rule_text': 'Delete me'}).get_json()
        resp = client.delete(f'/api/admin/guidelines/{g["id"]}')
        assert resp.status_code == 200
        assert resp.get_json()['deleted'] == g['id']


class TestPlanVersionsAPI:

    def test_save_version(self, client, db_session):
        plan = _mk_plan()
        resp = client.post(f'/api/admin/plans/{plan.id}/versions', json={'change_summary': 'Initial'})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['version_number'] == 1
        assert data['change_summary'] == 'Initial'

    def test_version_numbers_increment(self, client, db_session):
        plan = _mk_plan()
        client.post(f'/api/admin/plans/{plan.id}/versions', json={})
        resp = client.post(f'/api/admin/plans/{plan.id}/versions', json={})
        assert resp.get_json()['version_number'] == 2

    def test_list_versions(self, client, db_session):
        plan = _mk_plan()
        client.post(f'/api/admin/plans/{plan.id}/versions', json={})
        client.post(f'/api/admin/plans/{plan.id}/versions', json={})
        assert len(client.get(f'/api/admin/plans/{plan.id}/versions').get_json()) == 2


class TestPlanCloneTemplate:

    def test_promote_to_template(self, client, db_session):
        plan = _mk_plan()
        resp = client.post(f'/api/admin/plans/{plan.id}/promote-to-template')
        assert resp.status_code == 200
        assert resp.get_json()['is_template'] is True

    def test_clone_from_template(self, client, db_session):
        source = _mk_plan('Source Template')
        source.is_template = True
        db.session.commit()
        resp = client.post(f'/api/admin/plans/{source.id}/clone-from-template', json={'name': 'Clone'})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'Clone'
        assert data['is_template'] is False
        assert data['id'] != source.id


# ── Plan Assignment + Fulfillment ─────────────────────────────────────────────

class TestPlanFulfillmentAPI:

    def _setup(self, db_session, client):
        user = User(username='patient_test', pw_hash='x')
        db.session.add(user)
        db.session.commit()
        plan = _mk_plan('Patient Plan', duration=14)
        day = _mk_day(plan.id, 0, 'Day 1')
        slot = _mk_slot(day.id, 'Breakfast')
        assignment = UserPlanAssignment(
            user_id=user.id,
            plan_id=plan.id,
            start_date=date.today(),
            is_active=True,
        )
        db.session.add(assignment)
        db.session.commit()
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        return user, slot

    def test_fulfill_slot(self, client, db_session):
        _, slot = self._setup(db_session, client)
        resp = client.post('/api/plans/fulfill-slot', json={
            'slot_id': slot.id,
            'date': date.today().isoformat(),
        })
        assert resp.status_code == 201
        assert resp.get_json()['status'] == 'fulfilled'

    def test_fulfill_slot_missing_fields(self, client, db_session):
        self._setup(db_session, client)
        assert client.post('/api/plans/fulfill-slot', json={'slot_id': 1}).status_code == 400

    def test_toggle_fulfillment_off(self, client, db_session):
        _, slot = self._setup(db_session, client)
        today = date.today().isoformat()
        client.post('/api/plans/fulfill-slot', json={'slot_id': slot.id, 'date': today})
        resp = client.post('/api/plans/fulfill-slot', json={'slot_id': slot.id, 'date': today})
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'unfulfilled'

    def test_fulfillment_status_endpoint(self, client, db_session):
        _, slot = self._setup(db_session, client)
        today = date.today().isoformat()
        client.post('/api/plans/fulfill-slot', json={'slot_id': slot.id, 'date': today})
        resp = client.get(f'/api/plans/fulfillment-status?date={today}')
        assert resp.status_code == 200
        assert 'slots' in resp.get_json()
        fulfilled = [s for s in resp.get_json()['slots'] if s.get('is_fulfilled')]
        assert len(fulfilled) >= 1

    def test_my_assignment_rich_no_assignment(self, client, db_session):
        user = User(username='no_plan_user', pw_hash='x')
        db.session.add(user)
        db.session.commit()
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
        resp = client.get('/api/plans/my-assignment/rich')
        assert resp.status_code == 200
        assert resp.get_json()['assignment'] is None

    def test_my_assignment_rich_returns_days_and_slots(self, client, db_session):
        _, slot = self._setup(db_session, client)
        resp = client.get('/api/plans/my-assignment/rich')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['assignment'] is not None
        assert len(data['days']) == 1
        assert data['days'][0]['slots'][0]['slot_name'] == 'Breakfast'


# ── Image Extraction Pipeline ─────────────────────────────────────────────────

_MOCK_EXTRACTION = {
    'plan_name': 'Test Diet',
    'duration_days': 1,
    'days': [{
        'day_offset': 0,
        'label': 'Day 1',
        'label_tr': None,
        'notes': None,
        'slots': [{
            'slot_name': 'Breakfast',
            'slot_name_tr': 'Kahvaltı',
            'content_pattern': 'A',
            'is_optional': False,
            'items': [{
                'food_name': 'Eggs',
                'food_name_tr': 'Yumurta',
                'quantity': 2.0,
                'unit': 'piece',
                'notes': None,
            }],
        }],
    }],
}


class TestImageExtractionAPI:

    def _upload(self, client):
        """Upload a fake image. Returns the upload record dict."""
        data = {'file': (io.BytesIO(b'fake-png-data'), 'test.png')}
        resp = client.post(
            '/api/admin/plans/upload-image',
            data=data,
            content_type='multipart/form-data',
        )
        assert resp.status_code == 201, resp.data
        return resp.get_json()

    def _set_draft_ready(self, upload_id, plan_id=None):
        """Helper: directly mark upload as draft_ready with extracted JSON."""
        from models.program_image_upload import ProgramImageUpload
        row = db.session.get(ProgramImageUpload, upload_id)
        row.extraction_status = 'draft_ready'
        row.extracted_json = json.dumps(_MOCK_EXTRACTION)
        if plan_id:
            row.program_id = plan_id
        db.session.commit()

    def test_upload_image_success(self, authed_client):
        client, _ = authed_client
        upload = self._upload(client)
        assert upload['extraction_status'] == 'pending'
        assert upload['original_filename'] == 'test.png'

    def test_upload_image_no_file(self, authed_client):
        client, _ = authed_client
        resp = client.post('/api/admin/plans/upload-image', data={},
                           content_type='multipart/form-data')
        assert resp.status_code == 400

    def test_upload_status_pending(self, authed_client):
        client, _ = authed_client
        upload = self._upload(client)
        resp = client.get(f'/api/admin/plans/upload-status/{upload["id"]}')
        assert resp.status_code == 200
        assert resp.get_json()['extraction_status'] == 'pending'

    def test_upload_status_not_found(self, authed_client):
        client, _ = authed_client
        assert client.get('/api/admin/plans/upload-status/9999').status_code == 404

    def test_process_image_returns_202(self, authed_client, db_session):
        client, _ = authed_client
        upload = self._upload(client)
        with patch('utils.image_extractor.extract_diet_plan', return_value=_MOCK_EXTRACTION):
            resp = client.post(f'/api/admin/plans/process-image/{upload["id"]}')
        assert resp.status_code == 202

    def test_process_image_idempotent_already_processing(self, authed_client, db_session):
        from models.program_image_upload import ProgramImageUpload
        client, _ = authed_client
        upload = self._upload(client)
        row = db.session.get(ProgramImageUpload, upload['id'])
        row.extraction_status = 'processing'
        db.session.commit()
        resp = client.post(f'/api/admin/plans/process-image/{upload["id"]}')
        assert resp.status_code == 202
        assert resp.get_json()['message'] == 'Already processing'

    def test_process_image_skips_when_draft_ready(self, authed_client, db_session):
        client, _ = authed_client
        upload = self._upload(client)
        self._set_draft_ready(upload['id'])
        resp = client.post(f'/api/admin/plans/process-image/{upload["id"]}')
        assert resp.status_code == 200
        assert 'extracted' in resp.get_json()

    def test_upload_status_returns_extracted_json(self, authed_client, db_session):
        client, _ = authed_client
        upload = self._upload(client)
        self._set_draft_ready(upload['id'])
        resp = client.get(f'/api/admin/plans/upload-status/{upload["id"]}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['extraction_status'] == 'draft_ready'
        assert data['extracted']['plan_name'] == 'Test Diet'
        assert len(data['extracted']['days']) == 1

    def test_apply_extraction_creates_rows(self, authed_client, db_session):
        from models.program_image_upload import ProgramImageUpload
        client, _ = authed_client
        plan = _mk_plan('Apply Test Plan')
        upload = self._upload(client)
        self._set_draft_ready(upload['id'], plan_id=plan.id)
        resp = client.post(
            f'/api/admin/plans/apply-extraction/{upload["id"]}',
            json={'replace': True},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['days_created'] == 1
        assert data['slots_created'] == 1
        assert data['items_created'] == 1

    def test_apply_extraction_not_found(self, authed_client):
        client, _ = authed_client
        assert client.post('/api/admin/plans/apply-extraction/9999', json={}).status_code == 404

    def test_apply_extraction_requires_draft_ready(self, authed_client, db_session):
        client, _ = authed_client
        upload = self._upload(client)
        # Status is still 'pending' — should return 400
        resp = client.post(
            f'/api/admin/plans/apply-extraction/{upload["id"]}',
            json={'replace': True},
        )
        assert resp.status_code == 400
