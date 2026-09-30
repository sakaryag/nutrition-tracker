"""Tests for /api/recipes — Recipe Builder (PR15)."""
import pytest


class TestRecipeCRUD:

    def test_create_recipe_minimal(self, client):
        resp = client.post('/api/recipes', json={'name': 'My Salad'})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'My Salad'
        assert data['servings'] == 1
        assert data['ingredients'] == []
        assert data['total_protein'] == 0
        assert data['ingredient_count'] == 0

    def test_create_recipe_missing_name(self, client):
        resp = client.post('/api/recipes', json={'prep_notes': 'Mix everything'})
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_list_recipes(self, client):
        client.post('/api/recipes', json={'name': 'Recipe A'})
        client.post('/api/recipes', json={'name': 'Recipe B'})
        resp = client.get('/api/recipes')
        assert resp.status_code == 200
        names = [r['name'] for r in resp.get_json()]
        assert 'Recipe A' in names
        assert 'Recipe B' in names

    def test_get_recipe(self, client):
        create_resp = client.post('/api/recipes', json={
            'name': 'Fetch Me', 'prep_notes': 'Some notes', 'servings': 2,
        })
        rid = create_resp.get_json()['id']
        resp = client.get(f'/api/recipes/{rid}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['name'] == 'Fetch Me'
        assert data['servings'] == 2
        assert data['prep_notes'] == 'Some notes'

    def test_get_recipe_not_found(self, client):
        resp = client.get('/api/recipes/99999')
        assert resp.status_code == 404

    def test_update_recipe(self, client):
        create_resp = client.post('/api/recipes', json={'name': 'Old Name', 'servings': 1})
        rid = create_resp.get_json()['id']
        resp = client.put(f'/api/recipes/{rid}', json={'name': 'New Name', 'servings': 4})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['name'] == 'New Name'
        assert data['servings'] == 4

    def test_delete_recipe(self, client):
        create_resp = client.post('/api/recipes', json={'name': 'To Delete'})
        rid = create_resp.get_json()['id']
        del_resp = client.delete(f'/api/recipes/{rid}')
        assert del_resp.status_code == 200
        assert del_resp.get_json()['deleted'] == rid
        # Confirm it's gone
        assert client.get(f'/api/recipes/{rid}').status_code == 404

    def test_create_recipe_with_ingredients(self, client):
        # Create a food first
        food_resp = client.post('/api/foods', json={
            'name': 'Chicken Breast',
            'protein': 31.0, 'fat': 3.6, 'carbs': 0.0,
            'calories': 165, 'default_serving': 100, 'serving_unit': 'g',
        })
        food_id = food_resp.get_json()['id']

        resp = client.post('/api/recipes', json={
            'name': 'Chicken Bowl',
            'servings': 2,
            'ingredients': [
                {'saved_food_id': food_id, 'quantity': 200, 'unit': 'g'},
            ],
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['ingredient_count'] == 1
        assert data['total_protein'] == pytest.approx(62.0, abs=0.5)
        assert data['total_fat'] == pytest.approx(7.2, abs=0.5)

    def test_update_recipe_ingredients(self, client):
        # Create food and recipe
        food_resp = client.post('/api/foods', json={
            'name': 'Rice', 'protein': 2.7, 'fat': 0.3, 'carbs': 28.0, 'calories': 130,
        })
        food_id = food_resp.get_json()['id']
        create_resp = client.post('/api/recipes', json={'name': 'Rice Dish'})
        rid = create_resp.get_json()['id']

        # Add ingredient via PUT
        put_resp = client.put(f'/api/recipes/{rid}', json={
            'ingredients': [{'saved_food_id': food_id, 'quantity': 100, 'unit': 'g'}],
        })
        assert put_resp.status_code == 200
        data = put_resp.get_json()
        assert data['ingredient_count'] == 1
        assert data['total_carbs'] == pytest.approx(28.0, abs=0.5)

    def test_search_recipes(self, client):
        client.post('/api/recipes', json={'name': 'Greek Salad'})
        client.post('/api/recipes', json={'name': 'Caesar Salad'})
        client.post('/api/recipes', json={'name': 'Omelette'})

        resp = client.get('/api/recipes?q=salad')
        assert resp.status_code == 200
        names = [r['name'] for r in resp.get_json()]
        assert 'Greek Salad' in names
        assert 'Caesar Salad' in names
        assert 'Omelette' not in names


class TestRecipeActions:

    def _make_recipe_with_food(self, client):
        """Helper: create a food and a recipe with one ingredient."""
        food_resp = client.post('/api/foods', json={
            'name': 'Test Protein',
            'protein': 25.0, 'fat': 5.0, 'carbs': 2.0,
            'calories': 153, 'default_serving': 100, 'serving_unit': 'g',
        })
        food_id = food_resp.get_json()['id']
        recipe_resp = client.post('/api/recipes', json={
            'name': 'Test Recipe',
            'servings': 1,
            'ingredients': [{'saved_food_id': food_id, 'quantity': 200, 'unit': 'g'}],
        })
        return recipe_resp.get_json()['id']

    def test_log_recipe_today(self, client):
        rid = self._make_recipe_with_food(client)
        resp = client.post(f'/api/recipes/{rid}/log', json={})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['logged'] == 1
        assert data['recipe'] == 'Test Recipe'
        assert len(data['entries']) == 1
        assert data['entries'][0]['protein'] == pytest.approx(50.0, abs=0.5)

    def test_log_recipe_to_date(self, client):
        rid = self._make_recipe_with_food(client)
        resp = client.post(f'/api/recipes/{rid}/log', json={'date': '2026-07-04', 'meal_type': 'Breakfast'})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['logged'] == 1
        assert data['entries'][0]['entry_date'] == '2026-07-04'
        assert data['entries'][0]['meal_type'] == 'Breakfast'

    def test_log_recipe_not_found(self, client):
        resp = client.post('/api/recipes/99999/log', json={})
        assert resp.status_code == 404

    def test_save_recipe_as_food(self, client):
        food_resp = client.post('/api/foods', json={
            'name': 'Ingredient X', 'protein': 20.0, 'fat': 4.0, 'carbs': 10.0, 'calories': 156,
        })
        food_id = food_resp.get_json()['id']
        recipe_resp = client.post('/api/recipes', json={
            'name': 'Unique Dish 999',
            'ingredients': [{'saved_food_id': food_id, 'quantity': 100, 'unit': 'g'}],
        })
        rid = recipe_resp.get_json()['id']

        resp = client.post(f'/api/recipes/{rid}/save-as-food', json={})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['created'] is True
        food = data['food']
        assert food['name'] == 'Unique Dish 999'
        assert food['source'] == 'custom'
        assert food['protein'] == pytest.approx(20.0, abs=0.5)

    def test_save_recipe_as_food_updates_existing(self, client):
        """Saving the same recipe twice should update, not duplicate."""
        food_resp = client.post('/api/foods', json={
            'name': 'Ingredient Y', 'protein': 10.0, 'fat': 2.0, 'carbs': 5.0, 'calories': 78,
        })
        food_id = food_resp.get_json()['id']
        recipe_resp = client.post('/api/recipes', json={
            'name': 'Update Test Dish',
            'ingredients': [{'saved_food_id': food_id, 'quantity': 100, 'unit': 'g'}],
        })
        rid = recipe_resp.get_json()['id']

        # First save
        r1 = client.post(f'/api/recipes/{rid}/save-as-food', json={})
        assert r1.status_code == 201
        assert r1.get_json()['created'] is True

        # Second save — same recipe name, same custom food: should update
        r2 = client.post(f'/api/recipes/{rid}/save-as-food', json={})
        assert r2.status_code == 200
        assert r2.get_json()['updated'] is True

    def test_save_recipe_as_food_not_found(self, client):
        resp = client.post('/api/recipes/99999/save-as-food', json={})
        assert resp.status_code == 404

    def test_created_at_in_response(self, client):
        resp = client.post('/api/recipes', json={'name': 'Timestamped'})
        data = resp.get_json()
        assert data['created_at'] is not None

    def test_description_alias(self, client):
        """description field in POST body maps to prep_notes."""
        resp = client.post('/api/recipes', json={
            'name': 'Alias Test', 'description': 'Mix it up',
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['prep_notes'] == 'Mix it up'
        assert data['description'] == 'Mix it up'


# ---------------------------------------------------------------------------
# Auth guard tests — unauthenticated requests must get 401
# ---------------------------------------------------------------------------

class RecipesAuthConfig:
    TESTING = True
    AUTH_ENABLED = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'recipes-auth-test-secret'
    DEFAULT_PROTEIN_TARGET = 150
    DEFAULT_FAT_TARGET = 65
    DEFAULT_CARBS_TARGET = 250
    DEFAULT_CALORIES_TARGET = 2200


@pytest.fixture(scope='class')
def recipes_auth_app():
    from app import create_app
    from models import db as _db
    application = create_app(test_config=RecipesAuthConfig)
    with application.app_context():
        _db.drop_all()
        _db.create_all()
    yield application


@pytest.fixture
def recipes_auth_db(recipes_auth_app):
    from models import db as _db
    with recipes_auth_app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture
def recipes_auth_client(recipes_auth_app):
    return recipes_auth_app.test_client()


class TestRecipesAuthGuards:
    """All recipe routes must return 401 for unauthenticated requests when AUTH_ENABLED."""

    def test_list_requires_auth(self, recipes_auth_client, recipes_auth_db):
        assert recipes_auth_client.get('/api/recipes').status_code == 401

    def test_create_requires_auth(self, recipes_auth_client, recipes_auth_db):
        assert recipes_auth_client.post('/api/recipes', json={'name': 'X'}).status_code == 401

    def test_get_requires_auth(self, recipes_auth_client, recipes_auth_db):
        assert recipes_auth_client.get('/api/recipes/1').status_code == 401

    def test_update_requires_auth(self, recipes_auth_client, recipes_auth_db):
        assert recipes_auth_client.put('/api/recipes/1', json={}).status_code == 401

    def test_delete_requires_auth(self, recipes_auth_client, recipes_auth_db):
        assert recipes_auth_client.delete('/api/recipes/1').status_code == 401

    def test_log_requires_auth(self, recipes_auth_client, recipes_auth_db):
        assert recipes_auth_client.post('/api/recipes/1/log', json={}).status_code == 401

    def test_save_as_food_requires_auth(self, recipes_auth_client, recipes_auth_db):
        assert recipes_auth_client.post('/api/recipes/1/save-as-food', json={}).status_code == 401


# ---------------------------------------------------------------------------
# Ownership isolation — user B must not access user A's recipes
# ---------------------------------------------------------------------------

class TestRecipeOwnership:

    def _login(self, client, app, username, password='pw1234'):
        from models import db as _db
        from models.user import User
        with app.app_context():
            user = User(username=username)
            user.set_pw(password)
            _db.session.add(user)
            _db.session.commit()
            uid = user.id
        with client.session_transaction() as sess:
            sess['user_id'] = uid
        return uid

    def test_user_b_cannot_get_user_a_recipe(self, recipes_auth_client, recipes_auth_app, recipes_auth_db):
        client_a = recipes_auth_app.test_client()
        client_b = recipes_auth_app.test_client()
        self._login(client_a, recipes_auth_app, 'alice')
        self._login(client_b, recipes_auth_app, 'bob')

        create_resp = client_a.post('/api/recipes', json={'name': 'Alice Secret Recipe'})
        assert create_resp.status_code == 201
        rid = create_resp.get_json()['id']

        assert client_b.get(f'/api/recipes/{rid}').status_code == 404

    def test_user_b_cannot_update_user_a_recipe(self, recipes_auth_client, recipes_auth_app, recipes_auth_db):
        client_a = recipes_auth_app.test_client()
        client_b = recipes_auth_app.test_client()
        self._login(client_a, recipes_auth_app, 'alice2')
        self._login(client_b, recipes_auth_app, 'bob2')

        rid = client_a.post('/api/recipes', json={'name': 'Alice Recipe 2'}).get_json()['id']
        assert client_b.put(f'/api/recipes/{rid}', json={'name': 'Hacked'}).status_code == 404

    def test_user_b_cannot_delete_user_a_recipe(self, recipes_auth_client, recipes_auth_app, recipes_auth_db):
        client_a = recipes_auth_app.test_client()
        client_b = recipes_auth_app.test_client()
        self._login(client_a, recipes_auth_app, 'alice3')
        self._login(client_b, recipes_auth_app, 'bob3')

        rid = client_a.post('/api/recipes', json={'name': 'Alice Recipe 3'}).get_json()['id']
        assert client_b.delete(f'/api/recipes/{rid}').status_code == 404

    def test_user_b_cannot_log_user_a_recipe(self, recipes_auth_client, recipes_auth_app, recipes_auth_db):
        client_a = recipes_auth_app.test_client()
        client_b = recipes_auth_app.test_client()
        self._login(client_a, recipes_auth_app, 'alice4')
        self._login(client_b, recipes_auth_app, 'bob4')

        rid = client_a.post('/api/recipes', json={'name': 'Alice Recipe 4'}).get_json()['id']
        assert client_b.post(f'/api/recipes/{rid}/log', json={}).status_code == 404
