import json


class TestEntries:

    def test_create_entry(self, client):
        resp = client.post('/api/entries', json={
            'food_name': 'Test Chicken',
            'protein': 30, 'fat': 5, 'carbs': 0,
            'meal_type': 'Lunch',
            'serving_size': 150, 'serving_unit': 'g',
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['food_name'] == 'Test Chicken'
        assert data['protein'] == 30
        assert data['food_auto_saved'] is True

    def test_auto_calories(self, client):
        resp = client.post('/api/entries', json={
            'food_name': 'Auto Cal Food',
            'protein': 10, 'fat': 10, 'carbs': 10,
            'meal_type': 'Snack',
            'serving_size': 100, 'serving_unit': 'g',
        })
        data = resp.get_json()
        assert data['calories'] == (10 * 4) + (10 * 9) + (10 * 4)

    def test_list_entries_by_date(self, client):
        client.post('/api/entries', json={
            'food_name': 'Morning Oats',
            'protein': 5, 'fat': 3, 'carbs': 30,
            'meal_type': 'Breakfast',
            'serving_size': 100, 'serving_unit': 'g',
            'entry_date': '2026-01-15',
        })
        resp = client.get('/api/entries?date=2026-01-15')
        assert resp.status_code == 200
        entries = resp.get_json()
        assert len(entries) == 1
        assert entries[0]['food_name'] == 'Morning Oats'

    def test_update_entry(self, client):
        resp = client.post('/api/entries', json={
            'food_name': 'Rice',
            'protein': 3, 'fat': 0.5, 'carbs': 28,
            'meal_type': 'Lunch',
            'serving_size': 100, 'serving_unit': 'g',
        })
        entry_id = resp.get_json()['id']
        resp2 = client.put(f'/api/entries/{entry_id}', json={'protein': 6})
        assert resp2.status_code == 200
        assert resp2.get_json()['protein'] == 6

    def test_delete_entry(self, client):
        resp = client.post('/api/entries', json={
            'food_name': 'To Delete',
            'protein': 1, 'fat': 1, 'carbs': 1,
            'meal_type': 'Snack',
            'serving_size': 50, 'serving_unit': 'g',
        })
        entry_id = resp.get_json()['id']
        resp2 = client.delete(f'/api/entries/{entry_id}')
        assert resp2.status_code == 200
        assert resp2.get_json()['deleted'] == entry_id

    def test_recent_entries(self, client):
        for name in ['Food A', 'Food B']:
            client.post('/api/entries', json={
                'food_name': name,
                'protein': 10, 'fat': 5, 'carbs': 20,
                'meal_type': 'Lunch',
                'serving_size': 100, 'serving_unit': 'g',
            })
        resp = client.get('/api/entries/recent')
        assert resp.status_code == 200
        names = [e['food_name'] for e in resp.get_json()]
        assert 'Food A' in names
        assert 'Food B' in names

    def test_auto_save_no_duplicate(self, client):
        for _ in range(2):
            client.post('/api/entries', json={
                'food_name': 'Unique Food',
                'protein': 5, 'fat': 2, 'carbs': 10,
                'meal_type': 'Snack',
                'serving_size': 100, 'serving_unit': 'g',
            })
        resp = client.get('/api/foods?q=Unique+Food')
        foods = resp.get_json()
        custom = [f for f in foods if f['source'] == 'custom' and f['name'] == 'Unique Food']
        assert len(custom) == 1


class TestSummary:

    def test_daily_summary(self, client):
        client.post('/api/entries', json={
            'food_name': 'Sum Test',
            'protein': 20, 'fat': 10, 'carbs': 30,
            'meal_type': 'Lunch',
            'serving_size': 100, 'serving_unit': 'g',
            'entry_date': '2026-03-01',
        })
        resp = client.get('/api/summary?date=2026-03-01')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['totals']['protein'] == 20
        assert data['totals']['fat'] == 10
        assert data['totals']['carbs'] == 30
        assert 'target' in data
        assert 'remaining' in data

    def test_range_summary(self, client):
        for day in ['2026-03-01', '2026-03-02']:
            client.post('/api/entries', json={
                'food_name': 'Range Food',
                'protein': 10, 'fat': 5, 'carbs': 15,
                'meal_type': 'Dinner',
                'serving_size': 100, 'serving_unit': 'g',
                'entry_date': day,
            })
        resp = client.get('/api/summary/range?start=2026-03-01&end=2026-03-02')
        assert resp.status_code == 200
        rows = resp.get_json()
        assert len(rows) == 2

    def test_empty_day_summary(self, client):
        resp = client.get('/api/summary?date=2020-01-01')
        data = resp.get_json()
        assert data['totals']['protein'] == 0


class TestTargets:

    def test_get_default_targets(self, client):
        resp = client.get('/api/targets')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['protein'] == 150

    def test_set_targets(self, client):
        resp = client.post('/api/targets', json={
            'protein': 200, 'fat': 70, 'carbs': 300, 'calories': 2500,
        })
        assert resp.status_code == 201
        resp2 = client.get('/api/targets')
        assert resp2.get_json()['protein'] == 200

    def test_tdee_calculator(self, client):
        resp = client.post('/api/targets/calculate', json={
            'gender': 'male', 'age': 30, 'weight_kg': 80,
            'height_cm': 180, 'activity_level': 'moderate',
            'goal': 'maintain', 'preset': 'balanced',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'bmr' in data
        assert 'tdee' in data
        assert data['protein'] > 0


class TestFoods:

    def test_create_custom_food(self, client):
        resp = client.post('/api/foods', json={
            'name': 'My Smoothie',
            'protein': 15, 'fat': 5, 'carbs': 30,
            'default_serving': 300, 'serving_unit': 'ml',
        })
        assert resp.status_code == 201
        assert resp.get_json()['source'] == 'custom'

    def test_search_foods(self, client):
        client.post('/api/foods', json={
            'name': 'Banana Shake',
            'protein': 8, 'fat': 2, 'carbs': 40,
        })
        resp = client.get('/api/foods?q=banana')
        assert resp.status_code == 200
        foods = resp.get_json()
        assert any(f['name'] == 'Banana Shake' for f in foods)

    def test_source_filter(self, client):
        client.post('/api/foods', json={
            'name': 'Custom Only Food',
            'protein': 5, 'fat': 2, 'carbs': 10,
        })
        resp = client.get('/api/foods?q=&source=custom')
        foods = resp.get_json()
        assert all(f['source'] == 'custom' for f in foods)

    def test_update_custom_food(self, client):
        resp = client.post('/api/foods', json={
            'name': 'Editable Food',
            'protein': 10, 'fat': 5, 'carbs': 20,
        })
        fid = resp.get_json()['id']
        resp2 = client.put(f'/api/foods/{fid}', json={'protein': 25})
        assert resp2.status_code == 200
        assert resp2.get_json()['protein'] == 25

    def test_delete_custom_food(self, client):
        resp = client.post('/api/foods', json={
            'name': 'Delete Me',
            'protein': 1, 'fat': 1, 'carbs': 1,
        })
        fid = resp.get_json()['id']
        resp2 = client.delete(f'/api/foods/{fid}')
        assert resp2.status_code == 200
        resp3 = client.get('/api/foods?q=Delete+Me')
        assert len(resp3.get_json()) == 0

    def test_clone_food(self, client):
        from models.saved_food import SavedFood
        from models import db
        usda = SavedFood(
            name='USDA Egg', source='usda', usda_fdc_id=99999,
            protein=6, fat=5, carbs=0.5, calories=70,
            default_serving=50, serving_unit='g',
        )
        db.session.add(usda)
        db.session.commit()
        resp = client.post(f'/api/foods/{usda.id}/clone')
        assert resp.status_code == 201
        clone = resp.get_json()
        assert clone['source'] == 'custom'
        assert clone['name'] == 'USDA Egg'

    def test_cannot_edit_usda(self, client):
        from models.saved_food import SavedFood
        from models import db
        usda = SavedFood(
            name='USDA Rice', source='usda', usda_fdc_id=88888,
            protein=3, fat=0.5, carbs=28, calories=130,
            default_serving=100, serving_unit='g',
        )
        db.session.add(usda)
        db.session.commit()
        resp = client.put(f'/api/foods/{usda.id}', json={'protein': 999})
        assert resp.status_code == 403


class TestExport:

    def test_csv_export(self, client):
        client.post('/api/entries', json={
            'food_name': 'Export Food',
            'protein': 10, 'fat': 5, 'carbs': 20,
            'meal_type': 'Lunch',
            'serving_size': 100, 'serving_unit': 'g',
            'entry_date': '2026-06-01',
        })
        resp = client.get('/api/export?start=2026-06-01&end=2026-06-01')
        assert resp.status_code == 200
        assert 'text/csv' in resp.content_type
        assert b'Export Food' in resp.data


class TestPages:

    def test_dashboard_page(self, client):
        resp = client.get('/')
        assert resp.status_code == 200
        assert b'NutriTrack' in resp.data

    def test_history_page(self, client):
        resp = client.get('/history')
        assert resp.status_code == 200

    def test_foods_page(self, client):
        resp = client.get('/foods')
        assert resp.status_code == 200

    def test_settings_page(self, client):
        resp = client.get('/settings')
        assert resp.status_code == 200

class TestAuth:

    def test_login_page_redirects_when_disabled(self, client):
        resp = client.get('/login')
        assert resp.status_code == 302

    def test_register_page_redirects_when_disabled(self, client):
        resp = client.get('/register')
        assert resp.status_code == 302

    def test_auth_enabled_blocks_api(self, app, client):
        app.config['AUTH_ENABLED'] = True
        try:
            resp = client.get('/api/entries')
            assert resp.status_code == 401
        finally:
            app.config['AUTH_ENABLED'] = False

    def test_auth_enabled_redirects_pages(self, app, client):
        app.config['AUTH_ENABLED'] = True
        try:
            resp = client.get('/')
            assert resp.status_code == 302
            assert '/login' in resp.headers.get('Location', '')
        finally:
            app.config['AUTH_ENABLED'] = False

    def test_register_login_logout_flow(self, app, client):
        app.config['AUTH_ENABLED'] = True
        try:
            resp = client.post('/register', data={
                'username': 'testuser',
                'password': 'secret123',
                'confirm': 'secret123',
            }, follow_redirects=False)
            assert resp.status_code == 302

            resp2 = client.get('/')
            assert resp2.status_code == 200

            client.get('/logout')

            resp3 = client.get('/')
            assert resp3.status_code == 302

            resp4 = client.post('/login', data={
                'username': 'testuser',
                'password': 'secret123',
            }, follow_redirects=False)
            assert resp4.status_code == 302

            resp5 = client.get('/')
            assert resp5.status_code == 200
        finally:
            app.config['AUTH_ENABLED'] = False

    def test_register_duplicate_username(self, app, client):
        app.config['AUTH_ENABLED'] = True
        try:
            client.post('/register', data={
                'username': 'dupuser',
                'password': 'secret123',
                'confirm': 'secret123',
            })
            client.get('/logout')
            resp = client.post('/register', data={
                'username': 'dupuser',
                'password': 'other456',
                'confirm': 'other456',
            })
            assert resp.status_code == 200
            assert b'already taken' in resp.data
        finally:
            app.config['AUTH_ENABLED'] = False

    def test_login_wrong_password(self, app, client):
        app.config['AUTH_ENABLED'] = True
        try:
            client.post('/register', data={
                'username': 'wrongpw',
                'password': 'correct1',
                'confirm': 'correct1',
            })
            client.get('/logout')
            resp = client.post('/login', data={
                'username': 'wrongpw',
                'password': 'incorrect',
            })
            assert resp.status_code == 200
            assert b'Invalid' in resp.data
        finally:
            app.config['AUTH_ENABLED'] = False

class TestMealTemplates:

    def _template_payload(self):
        return {
            'name': 'Breakfast Combo',
            'meal_type': 'Breakfast',
            'items': [
                {
                    'food_name': 'Scrambled Eggs',
                    'protein': 12, 'fat': 10, 'carbs': 1,
                    'calories': 142,
                    'serving_size': 100, 'serving_unit': 'g',
                },
                {
                    'food_name': 'Toast',
                    'protein': 4, 'fat': 1, 'carbs': 20,
                    'calories': 105,
                    'serving_size': 30, 'serving_unit': 'g',
                },
            ],
        }

    def test_create_template(self, client):
        resp = client.post('/api/meal-templates', json=self._template_payload())
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'Breakfast Combo'
        assert data['meal_type'] == 'Breakfast'
        assert len(data['items']) == 2
        names = [i['food_name'] for i in data['items']]
        assert 'Scrambled Eggs' in names
        assert 'Toast' in names

    def test_list_templates(self, client):
        client.post('/api/meal-templates', json=self._template_payload())
        resp = client.get('/api/meal-templates')
        assert resp.status_code == 200
        templates = resp.get_json()
        assert any(t['name'] == 'Breakfast Combo' for t in templates)

    def test_log_template(self, client):
        create_resp = client.post('/api/meal-templates', json=self._template_payload())
        tid = create_resp.get_json()['id']
        log_resp = client.post(f'/api/meal-templates/{tid}/log', json={'date': '2026-04-01'})
        assert log_resp.status_code == 201
        log_data = log_resp.get_json()
        assert log_data['logged'] == 2
        assert log_data['template'] == 'Breakfast Combo'
        assert len(log_data['entries']) == 2
        entries_resp = client.get('/api/entries?date=2026-04-01')
        assert entries_resp.status_code == 200
        entries = entries_resp.get_json()
        entry_names = [e['food_name'] for e in entries]
        assert 'Scrambled Eggs' in entry_names
        assert 'Toast' in entry_names

    def test_update_template(self, client):
        create_resp = client.post('/api/meal-templates', json=self._template_payload())
        tid = create_resp.get_json()['id']
        update_resp = client.put(f'/api/meal-templates/{tid}', json={'name': 'Morning Meal'})
        assert update_resp.status_code == 200
        assert update_resp.get_json()['name'] == 'Morning Meal'
        get_resp = client.get(f'/api/meal-templates/{tid}')
        assert get_resp.get_json()['name'] == 'Morning Meal'

    def test_delete_template(self, client):
        create_resp = client.post('/api/meal-templates', json=self._template_payload())
        tid = create_resp.get_json()['id']
        del_resp = client.delete(f'/api/meal-templates/{tid}')
        assert del_resp.status_code == 200
        assert del_resp.get_json()['deleted'] == tid
        get_resp = client.get(f'/api/meal-templates/{tid}')
        assert get_resp.status_code == 404

    def test_create_empty_items_rejected(self, client):
        resp = client.post('/api/meal-templates', json={
            'name': 'Empty Template',
            'meal_type': 'Lunch',
            'items': [
                {'food_name': '', 'protein': 10, 'fat': 5, 'carbs': 20,
                 'serving_size': 100, 'serving_unit': 'g'},
                {'food_name': '  ', 'protein': 5, 'fat': 2, 'carbs': 10,
                 'serving_size': 50, 'serving_unit': 'g'},
            ],
        })
        data = resp.get_json()
        assert len(data['items']) == 0