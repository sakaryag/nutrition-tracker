"""tests/test_authz.py — authorization regression tests (AUTH_ENABLED=True).

is_admin means "dietitian" and must never grant global access; global user
management requires a username listed in SUPERADMIN_USERNAMES.
"""
from datetime import date, time

import pytest

from models import db
from models.user import User
from models.food_entry import FoodEntry
from models.nutrition_plan import NutritionPlan
from models.plan_task import PlanTask
from models.user_plan_assignment import UserPlanAssignment
from models.dietitian_access import DietitianAccess
from models.friend_connection import FriendConnection
from models.program_image_upload import ProgramImageUpload


@pytest.fixture
def auth_on(app):
    prev = (app.config.get('AUTH_ENABLED'), app.config.get('SUPERADMIN_USERNAMES'))
    app.config['AUTH_ENABLED'] = True
    app.config['SUPERADMIN_USERNAMES'] = frozenset({'owner'})
    yield
    app.config['AUTH_ENABLED'], app.config['SUPERADMIN_USERNAMES'] = prev


def _user(name, is_admin=False, premium=False):
    u = User(username=name, pw_hash='x', is_admin=is_admin, plan_feature_enabled=premium)
    db.session.add(u)
    db.session.commit()
    return u


def _plan(name, owner_id, **kw):
    p = NutritionPlan(name=name, created_by=owner_id, **kw)
    db.session.add(p)
    db.session.commit()
    return p


def _grant(dietitian, client, allowed=True):
    db.session.add(DietitianAccess(dietitian_id=dietitian.id, client_id=client.id, allowed=allowed))
    db.session.commit()


def _login(client, user):
    with client.session_transaction() as sess:
        sess['user_id'] = user.id


@pytest.fixture
def people(db_session, auth_on):
    return {
        'owner': _user('owner'),
        'diet': _user('diet', is_admin=True),
        'diet2': _user('diet2', is_admin=True),
        'client': _user('client1'),
        'victim': _user('victim'),
    }


# ── Global user management ───────────────────────────────────────────────────

class TestUserManagement:

    def test_dietitian_lists_only_consenting_clients(self, client, people):
        _grant(people['diet'], people['client'])
        _grant(people['diet'], people['victim'], allowed=False)
        _login(client, people['diet'])
        rv = client.get('/api/admin/users')
        assert rv.status_code == 200
        assert [u['username'] for u in rv.get_json()] == ['client1']

    def test_superadmin_lists_all_users(self, client, people):
        _login(client, people['owner'])
        names = {u['username'] for u in client.get('/api/admin/users').get_json()}
        assert {'diet', 'client1', 'victim'} <= names

    def test_member_cannot_list_users(self, client, people):
        _login(client, people['victim'])
        assert client.get('/api/admin/users').status_code == 403

    @pytest.mark.parametrize('payload', [{'is_admin': True}, {'plan_feature_enabled': True}])
    def test_dietitian_cannot_update_users(self, client, people, payload):
        _grant(people['diet'], people['client'])
        _login(client, people['diet'])
        rv = client.put(f"/api/admin/users/{people['client'].id}", json=payload)
        assert rv.status_code == 403
        db.session.refresh(people['client'])
        assert not people['client'].is_admin and not people['client'].plan_feature_enabled

    def test_superadmin_can_update_users(self, client, people):
        _login(client, people['owner'])
        rv = client.put(f"/api/admin/users/{people['victim'].id}", json={'plan_feature_enabled': True})
        assert rv.status_code == 200
        assert rv.get_json()['plan_feature_enabled'] is True

    def test_superadmin_needs_allowlist_not_is_admin(self, client, people, app):
        app.config['SUPERADMIN_USERNAMES'] = frozenset()
        _login(client, people['owner'])
        assert client.put(f"/api/admin/users/{people['victim'].id}", json={}).status_code == 403


class TestAssignPlan:

    def test_dietitian_cannot_assign_without_consent(self, client, people):
        victim = people['victim']
        other = _plan('Victim own plan', victim.id)
        db.session.add(UserPlanAssignment(user_id=victim.id, plan_id=other.id,
                                          start_date=date.today(), is_active=True))
        db.session.commit()
        p = _plan('Diet plan', people['diet'].id)
        _login(client, people['diet'])
        rv = client.post(f'/api/admin/users/{victim.id}/assign-plan', json={'plan_id': p.id})
        assert rv.status_code == 403
        active = UserPlanAssignment.query.filter_by(user_id=victim.id, is_active=True).one()
        assert active.plan_id == other.id
        db.session.refresh(victim)
        assert victim.plan_feature_enabled is False

    def test_dietitian_assigns_to_consenting_client(self, client, people):
        _grant(people['diet'], people['client'])
        p = _plan('Diet plan', people['diet'].id)
        _login(client, people['diet'])
        rv = client.post(f"/api/admin/users/{people['client'].id}/assign-plan", json={'plan_id': p.id})
        assert rv.status_code == 201

    def test_dietitian_cannot_assign_another_dietitians_private_plan(self, client, people):
        _grant(people['diet'], people['client'])
        p = _plan('Private', people['diet2'].id)
        _login(client, people['diet'])
        rv = client.post(f"/api/admin/users/{people['client'].id}/assign-plan", json={'plan_id': p.id})
        assert rv.status_code == 404


class TestDietitianFlow:

    def test_invite_then_consent_then_visible(self, client, people):
        diet, c = people['diet'], people['client']
        _login(client, diet)
        rv = client.post('/api/dietitian/invite', json={'username': 'client1'})
        assert rv.status_code == 201
        assert rv.get_json()['access_granted'] is False
        assert client.get('/api/admin/users').get_json() == []

        _login(client, c)
        assert client.put(f'/api/dietitian/access/{diet.id}', json={'allowed': True}).status_code == 200

        _login(client, diet)
        assert [u['id'] for u in client.get('/api/admin/users').get_json()] == [c.id]

    def test_invite_requires_dietitian(self, client, people):
        _login(client, people['victim'])
        assert client.post('/api/dietitian/invite', json={'username': 'client1'}).status_code == 403

    def test_invite_rejects_system_user(self, client, people):
        _user('__system__', is_admin=True)
        _login(client, people['diet'])
        assert client.post('/api/dietitian/invite', json={'username': '__system__'}).status_code == 404

    def test_client_data_requires_consent(self, client, people):
        diet, victim = people['diet'], people['victim']
        p = _plan('P', diet.id)
        db.session.add(UserPlanAssignment(user_id=victim.id, plan_id=p.id, start_date=date.today(),
                                          is_active=True, assigned_by=diet.id))
        db.session.commit()
        _grant(diet, victim, allowed=False)
        _login(client, diet)
        assert client.get(f'/api/dietitian/clients/{victim.id}/data').status_code == 403


# ── Registration / login ─────────────────────────────────────────────────────

class TestRegistration:

    def test_dietitian_signup_is_pending_until_approved(self, client, people):
        rv = client.post('/register', data={'username': 'newdiet', 'password': 'secret123',
                                            'confirm': 'secret123', 'role': 'dietitian'})
        assert rv.status_code == 302
        u = User.query.filter_by(username='newdiet').one()
        assert u.is_admin is False and u.plan_feature_enabled is False
        assert u.dietitian_status == 'pending'
        assert client.get('/api/admin/users').status_code == 403
        assert client.put(f"/api/admin/users/{u.id}", json={'is_admin': True}).status_code == 403
        assert client.post(f"/api/admin/dietitian-requests/{u.id}/approve").status_code == 403

    def test_role_switch_requests_approval(self, client, people):
        _login(client, people['victim'])
        rv = client.put('/api/dietitian/role', json={'role': 'dietitian'})
        assert rv.get_json()['role'] == 'member'
        db.session.refresh(people['victim'])
        assert people['victim'].is_admin is False
        assert people['victim'].dietitian_status == 'pending'

    def test_superadmin_approves_and_rejects(self, client, people):
        a = _user('reqa')
        b = _user('reqb')
        a.dietitian_status = b.dietitian_status = 'pending'
        db.session.commit()
        _login(client, people['owner'])
        names = [r['username'] for r in client.get('/api/admin/dietitian-requests').get_json()]
        assert names == ['reqa', 'reqb']
        assert client.post(f'/api/admin/dietitian-requests/{a.id}/approve').status_code == 200
        assert client.post(f'/api/admin/dietitian-requests/{b.id}/reject').status_code == 200
        db.session.refresh(a)
        db.session.refresh(b)
        assert a.is_admin and a.plan_feature_enabled and a.dietitian_status is None
        assert not b.is_admin and b.dietitian_status == 'rejected'

    def test_dietitian_cannot_review_requests(self, client, people):
        _login(client, people['diet'])
        assert client.get('/api/admin/dietitian-requests').status_code == 403

    def test_reserved_username_cannot_register(self, client, people):
        rv = client.post('/register', data={'username': '__system__', 'password': 'secret123',
                                            'confirm': 'secret123'})
        assert rv.status_code == 200
        assert User.query.filter_by(username='__system__').first() is None

    def test_email_username_cannot_register(self, client, people):
        rv = client.post('/register', data={'username': 'victim@gmail.com', 'password': 'secret123',
                                            'confirm': 'secret123'})
        assert rv.status_code == 200
        assert User.query.filter_by(username='victim@gmail.com').first() is None

    def test_system_user_cannot_login(self, client, people):
        u = User(username='__system__', is_admin=True)
        u.set_pw('!!system-seed-only!!')
        db.session.add(u)
        db.session.commit()
        rv = client.post('/login', data={'username': '__system__', 'password': '!!system-seed-only!!'})
        assert rv.status_code == 200
        assert b'Invalid' in rv.data
        with client.session_transaction() as sess:
            assert 'user_id' not in sess


# ── Plan ownership ───────────────────────────────────────────────────────────

class TestPlanOwnership:

    def test_update_and_delete_foreign_plan_forbidden(self, client, people):
        p = _plan('Victim plan', people['victim'].id)
        _login(client, people['diet'])
        assert client.put(f'/api/admin/plans/{p.id}', json={'name': 'pwned'}).status_code == 403
        assert client.delete(f'/api/admin/plans/{p.id}').status_code == 403
        assert db.session.get(NutritionPlan, p.id).name == 'Victim plan'

    def test_foreign_plan_tasks_forbidden(self, client, people):
        p = _plan('Victim plan', people['victim'].id)
        t = PlanTask(plan_id=p.id, description='secret', task_type='food')
        db.session.add(t)
        db.session.commit()
        _login(client, people['diet'])
        assert client.get(f'/api/admin/plans/{p.id}/tasks').status_code == 403
        assert client.post(f'/api/admin/plans/{p.id}/tasks',
                           json={'description': 'x', 'task_type': 'food'}).status_code == 403
        assert client.delete(f'/api/admin/tasks/{t.id}').status_code == 403

    def test_owner_can_edit_own_plan(self, client, people):
        p = _plan('Mine', people['diet'].id)
        _login(client, people['diet'])
        assert client.put(f'/api/admin/plans/{p.id}', json={'name': 'Renamed'}).status_code == 200
        assert client.get(f'/api/admin/plans/{p.id}/tasks').status_code == 200

    def test_unowned_plan_only_editable_by_superadmin(self, client, people):
        p = _plan('Orphan', None)
        _login(client, people['diet'])
        assert client.put(f'/api/admin/plans/{p.id}', json={'name': 'x'}).status_code == 403
        assert client.post(f'/api/admin/plans/{p.id}/days', json={}).status_code == 403
        _login(client, people['owner'])
        assert client.put(f'/api/admin/plans/{p.id}', json={'name': 'x'}).status_code == 200

    def test_dietitian_list_plans_hides_foreign_private(self, client, people):
        _plan('Foreign private', people['diet2'].id)
        _plan('Foreign public', people['diet2'].id, is_public=True)
        _plan('Mine', people['diet'].id)
        _login(client, people['diet'])
        names = {p['name'] for p in client.get('/api/admin/plans').get_json()}
        assert names == {'Foreign public', 'Mine'}

    def test_clone_foreign_private_plan_forbidden(self, client, people):
        private = _plan('Private', people['diet2'].id)
        public = _plan('Public', people['diet2'].id, is_public=True, is_template=True)
        _login(client, people['diet'])
        assert client.post(f'/api/admin/plans/{private.id}/clone-from-template', json={}).status_code == 404
        assert client.post(f'/api/admin/plans/{public.id}/clone-from-template', json={}).status_code == 201

    def test_self_assign_foreign_private_plan_forbidden(self, client, people):
        p = _plan('Private', people['diet2'].id)
        _login(client, people['victim'])
        assert client.post('/api/plans/self-assign', json={'plan_id': p.id}).status_code == 404

    def test_templates_listing_hides_foreign_private(self, client, people):
        _plan('Private tpl', people['diet2'].id, is_template=True)
        _plan('Public tpl', people['diet2'].id, is_template=True, is_public=True)
        _login(client, people['victim'])
        names = {p['name'] for p in client.get('/api/plans/templates').get_json()}
        assert names == {'Public tpl'}

    def test_fulfill_slot_of_unassigned_plan_forbidden(self, client, people):
        from datetime import datetime, timezone
        from models.program_day import ProgramDay
        from models.meal_slot import MealSlot
        p = _plan('P', people['diet2'].id)
        day = ProgramDay(program_id=p.id, day_offset=0, label='D', sort_order=0,
                         created_at=datetime.now(timezone.utc))
        db.session.add(day)
        db.session.commit()
        slot = MealSlot(day_id=day.id, slot_name='B', sort_order=0, created_at=datetime.now(timezone.utc))
        db.session.add(slot)
        db.session.commit()
        _login(client, people['victim'])
        rv = client.post('/api/plans/fulfill-slot', json={'slot_id': slot.id, 'date': date.today().isoformat()})
        assert rv.status_code == 403


class TestUploads:

    def _upload(self, owner, plan=None, status='draft_ready'):
        up = ProgramImageUpload(uploaded_by=owner.id, file_path='/nonexistent', original_filename='x.png',
                                mime_type='image/png', extraction_status=status,
                                extracted_json='{"days": []}', program_id=plan.id if plan else None)
        db.session.add(up)
        db.session.commit()
        return up

    def test_foreign_upload_not_accessible(self, client, people):
        p = _plan('Victim plan', people['diet2'].id)
        up = self._upload(people['diet2'], p)
        _login(client, people['diet'])
        assert client.get(f'/api/admin/plans/upload-status/{up.id}').status_code == 404
        assert client.post(f'/api/admin/plans/process-image/{up.id}').status_code == 404
        assert client.post(f'/api/admin/plans/confirm-extraction/{up.id}').status_code == 404
        assert client.post(f'/api/admin/plans/apply-extraction/{up.id}', json={}).status_code == 404
        assert db.session.get(ProgramImageUpload, up.id).extraction_status == 'draft_ready'

    def test_own_upload_accessible(self, client, people):
        up = self._upload(people['diet'])
        _login(client, people['diet'])
        assert client.get(f'/api/admin/plans/upload-status/{up.id}').status_code == 200


# ── Per-user data ────────────────────────────────────────────────────────────

class TestUserData:

    def test_export_only_contains_own_entries(self, client, people):
        me = _user('exporter', premium=True)
        for uid, name in ((me.id, 'MyFood'), (people['victim'].id, 'VictimFood')):
            db.session.add(FoodEntry(food_name=name, protein=1, fat=1, carbs=1, calories=17,
                                     entry_date=date(2026, 6, 1), entry_time=time(12, 0), user_id=uid))
        db.session.commit()
        _login(client, me)
        rv = client.get('/api/export?start=2026-06-01&end=2026-06-01')
        assert rv.status_code == 200
        assert b'MyFood' in rv.data
        assert b'VictimFood' not in rv.data

    def test_log_single_template_belongs_to_user(self, client, people):
        me = people['victim']
        _login(client, me)
        tpl = client.post('/api/meal-templates', json={'name': 'Combo', 'items': [
            {'food_name': 'Egg', 'protein': 6, 'fat': 5, 'carbs': 1}]}).get_json()
        rv = client.post(f"/api/meal-templates/{tpl['id']}/log-single", json={'date': '2026-06-02'})
        assert rv.status_code == 201
        assert db.session.get(FoodEntry, rv.get_json()['entry']['id']).user_id == me.id


# ── Social ───────────────────────────────────────────────────────────────────

class TestSocial:

    def test_blocked_user_cannot_remove_block(self, client, people):
        blocker, blocked = people['client'], people['victim']
        conn = FriendConnection(requester_id=blocker.id, recipient_id=blocked.id, status='blocked')
        db.session.add(conn)
        db.session.commit()
        _login(client, blocked)
        assert client.delete(f'/api/friends/{blocker.id}').status_code == 404
        assert db.session.get(FriendConnection, conn.id).status == 'blocked'
        _login(client, blocker)
        assert client.delete(f'/api/friends/{blocked.id}').status_code == 200

    def test_react_requires_friendship(self, client, people):
        me = _user('reactor', premium=True)
        _login(client, me)
        rv = client.post(f"/api/social/feed/{people['victim'].id}/2026-01-15/react", json={'emoji': '👏'})
        assert rv.status_code == 404
        db.session.add(FriendConnection(requester_id=me.id, recipient_id=people['victim'].id,
                                        status='accepted'))
        db.session.commit()
        rv = client.post(f"/api/social/feed/{people['victim'].id}/2026-01-15/react", json={'emoji': '👏'})
        assert rv.status_code == 200


# ── AUTH_ENABLED=false keeps single-user behaviour ───────────────────────────

class TestAuthDisabled:

    def test_admin_users_still_available(self, client, db_session):
        _user('someone')
        rv = client.get('/api/admin/users')
        assert rv.status_code == 200
        assert any(u['username'] == 'someone' for u in rv.get_json())

    def test_orphan_plan_editable(self, client, db_session):
        p = _plan('Local', None)
        assert client.put(f'/api/admin/plans/{p.id}', json={'name': 'Edited'}).status_code == 200
