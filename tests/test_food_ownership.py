"""Custom food ownership and dietitian invite listing (AUTH_ENABLED=True)."""
from datetime import date, time

import pytest

from models import db
from models.user import User
from models.saved_food import SavedFood
from models.food_entry import FoodEntry
from models.recipe import Recipe
from models.dietitian_access import DietitianAccess


@pytest.fixture
def auth_on(app):
    prev = (app.config.get('AUTH_ENABLED'), app.config.get('SUPERADMIN_USERNAMES'))
    app.config['AUTH_ENABLED'] = True
    app.config['SUPERADMIN_USERNAMES'] = frozenset({'owner'})
    yield
    app.config['AUTH_ENABLED'], app.config['SUPERADMIN_USERNAMES'] = prev


def _user(name, is_admin=False):
    u = User(username=name, pw_hash='x', is_admin=is_admin)
    db.session.add(u)
    db.session.commit()
    return u


def _food(name, owner_id=None, **kw):
    f = SavedFood(name=name, protein=10, fat=5, carbs=20, calories=165, source='custom',
                  owner_id=owner_id, **kw)
    db.session.add(f)
    db.session.commit()
    return f


def _login(client, user):
    with client.session_transaction() as sess:
        sess['user_id'] = user.id


@pytest.fixture
def people(db_session, auth_on):
    return {'owner': _user('owner'), 'alice': _user('alice'), 'bob': _user('bob'),
            'diet': _user('diet', is_admin=True)}


class TestFoodOwnership:

    def test_owner_can_edit(self, client, people):
        f = _food('Alice bar', people['alice'].id)
        _login(client, people['alice'])
        assert client.put(f'/api/foods/{f.id}', json={'protein': 12}).status_code == 200

    def test_other_user_cannot_edit_or_delete(self, client, people):
        f = _food('Alice bar', people['alice'].id)
        _login(client, people['bob'])
        assert client.put(f'/api/foods/{f.id}', json={'protein': 99}).status_code == 403
        assert client.delete(f'/api/foods/{f.id}').status_code == 403
        db.session.refresh(f)
        assert f.protein == 10 and not f.is_archived

    def test_superadmin_can_edit(self, client, people):
        f = _food('Alice bar', people['alice'].id)
        _login(client, people['owner'])
        assert client.put(f'/api/foods/{f.id}', json={'protein': 11}).status_code == 200

    def test_legacy_unowned_food_is_read_only(self, client, people):
        f = _food('Legacy food')
        _login(client, people['alice'])
        assert client.put(f'/api/foods/{f.id}', json={'protein': 1}).status_code == 403

    def test_clone_is_owned_by_caller(self, client, people):
        f = _food('Legacy food')
        _login(client, people['bob'])
        rv = client.post(f'/api/foods/{f.id}/clone')
        assert rv.status_code == 201
        body = rv.get_json()
        assert body['owner_id'] == people['bob'].id and body['can_edit'] is True

    def test_create_sets_owner(self, client, people):
        _login(client, people['alice'])
        rv = client.post('/api/foods', json={'name': 'Mine', 'protein': 1, 'fat': 1, 'carbs': 1})
        assert rv.status_code == 201
        assert rv.get_json()['owner_id'] == people['alice'].id

    def test_entry_edit_does_not_mutate_others_food(self, client, people):
        f = _food('Alice bar', people['alice'].id)
        e = FoodEntry(food_name='Alice bar', protein=10, fat=5, carbs=20, calories=165,
                      entry_date=date(2026, 1, 1), entry_time=time(9), user_id=people['bob'].id,
                      saved_food_id=f.id, meal_type='Snack')
        db.session.add(e)
        db.session.commit()
        _login(client, people['bob'])
        assert client.put(f'/api/entries/{e.id}', json={'protein': 50}).status_code == 200
        db.session.refresh(f)
        assert f.protein == 10

    def test_recipe_save_as_food_does_not_overwrite_others(self, client, people):
        f = _food('Soup', people['alice'].id, food_type='meal')
        r = Recipe(name='Soup', owner_id=people['bob'].id, servings=1,
                   total_protein=1, total_fat=1, total_carbs=1, total_calories=17)
        db.session.add(r)
        db.session.commit()
        _login(client, people['bob'])
        rv = client.post(f'/api/recipes/{r.id}/save-as-food')
        assert rv.status_code in (200, 201)
        db.session.refresh(f)
        assert f.protein == 10
        assert SavedFood.query.filter_by(name='Soup', owner_id=people['bob'].id).count() == 1

    def test_backfill_assigns_single_referencing_user(self, app, people):
        from app import _patch_saved_food_owner
        solo = _food('Solo')
        shared = _food('Shared')
        for uid, fid in ((people['alice'].id, solo.id), (people['alice'].id, shared.id),
                         (people['bob'].id, shared.id)):
            db.session.add(FoodEntry(food_name='x', protein=1, fat=1, carbs=1, calories=17,
                                     entry_date=date(2026, 1, 1), entry_time=time(9),
                                     user_id=uid, saved_food_id=fid))
        db.session.commit()
        _patch_saved_food_owner(app)
        db.session.expire_all()
        assert db.session.get(SavedFood, solo.id).owner_id == people['alice'].id
        assert db.session.get(SavedFood, shared.id).owner_id is None


class TestInvites:

    def test_invites_scoped_to_dietitian(self, client, people):
        diet2 = _user('diet2', is_admin=True)
        db.session.add_all([
            DietitianAccess(dietitian_id=people['diet'].id, client_id=people['alice'].id, allowed=False),
            DietitianAccess(dietitian_id=diet2.id, client_id=people['bob'].id, allowed=True),
        ])
        db.session.commit()
        _login(client, people['diet'])
        rv = client.get('/api/dietitian/invites')
        assert rv.status_code == 200
        assert [i['username'] for i in rv.get_json()] == ['alice']

    def test_non_dietitian_cannot_list_invites(self, client, people):
        _login(client, people['alice'])
        assert client.get('/api/dietitian/invites').status_code in (401, 403)
