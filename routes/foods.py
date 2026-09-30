import base64
import csv
import io
import json
import re
import urllib.request
import urllib.error

from flask import Blueprint, jsonify, request, current_app, session
from sqlalchemy import case, or_
from models import db
from models.saved_food import SavedFood
from rapidfuzz import fuzz, process as rfprocess

foods_bp = Blueprint('foods', __name__, url_prefix='/api/foods')


@foods_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


@foods_bp.route('/barcode', methods=['GET'])
def barcode_lookup():
    code = request.args.get('code', '').strip()
    if not code:
        return jsonify({'found': False, 'message': 'code is required'}), 400
    if not code.isdigit() or not (6 <= len(code) <= 14):
        return jsonify({'found': False, 'message': 'Invalid barcode'}), 400
    try:
        url = f'https://world.openfoodfacts.org/api/v2/product/{code}.json'
        req = urllib.request.Request(url, headers={'User-Agent': 'NutriTrack/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if data.get('status') != 1:
            return jsonify({'found': False, 'message': 'Product not found'})
        product = data.get('product', {})
        name = product.get('product_name', '').strip()
        if not name:
            return jsonify({'found': False, 'message': 'Product has no name'})
        nutriments = product.get('nutriments', {})
        protein = nutriments.get('proteins_100g')
        fat = nutriments.get('fat_100g')
        carbs = nutriments.get('carbohydrates_100g')
        if protein is None or fat is None or carbs is None:
            return jsonify({'found': False, 'message': 'Incomplete nutrition data'})
        kcal = nutriments.get('energy-kcal_100g')
        if kcal is None:
            energy_kj = nutriments.get('energy_100g')
            kcal = round(energy_kj / 4.184, 1) if energy_kj is not None else round(
                float(protein) * 4 + float(fat) * 9 + float(carbs) * 4, 1
            )
        return jsonify({
            'found': True,
            'name': name,
            'protein': round(float(protein), 1),
            'fat': round(float(fat), 1),
            'carbs': round(float(carbs), 1),
            'calories': round(float(kcal), 1),
            'barcode': code,
        })
    except Exception:
        return jsonify({'found': False, 'message': 'Lookup failed'})


_ALLOWED_MIME = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}


@foods_bp.route('/image', methods=['POST'])
def image_lookup():
    api_key = request.form.get('api_key', '').strip()
    if not api_key:
        return jsonify({'found': False, 'message': 'Anthropic API key required — add yours in Settings'})
    if 'image' not in request.files:
        return jsonify({'found': False, 'message': 'image file is required'}), 400
    img = request.files['image']
    mime = (img.content_type or '').split(';')[0].strip()
    if mime not in _ALLOWED_MIME:
        return jsonify({'found': False, 'message': 'Unsupported image format (use JPEG, PNG, GIF or WebP)'}), 400
    img_bytes = img.read(10 * 1024 * 1024 + 1)
    if len(img_bytes) > 10 * 1024 * 1024:
        return jsonify({'found': False, 'message': 'Image too large (max 10 MB)'}), 400
    lang = request.form.get('lang', 'en').strip()
    _vision_models = {'claude-haiku-4-5-20251001', 'claude-sonnet-4-5'}
    model = request.form.get('model', '').strip()
    if model not in _vision_models:
        model = 'claude-haiku-4-5-20251001'
    b64 = base64.b64encode(img_bytes).decode('utf-8')
    if lang == 'tr':
        prompt = (
            'Bu yemek fotoğrafını analiz et. Görünen tüm yiyecekleri belirle ve porsiyonları tahmin et. '
            'SADECE geçerli JSON döndür, markdown veya açıklama olmadan:\n'
            '{"items": [{"food_name": "Tavuk göğsü", "estimated_grams": 180, '
            '"protein": 31.0, "fat": 3.6, "carbs": 0.0, "calories": 165.0}]}\n'
            'Kurallar:\n'
            '- makrolar estimated_grams toplamı içindir (100g başına değil)\n'
            '- estimated_grams görünen porsiyondur\n'
            '- birden fazla yiyecek varsa her biri için ayrı öğe\n'
            '- Türkçe yiyecek adları kullan'
        )
    else:
        prompt = (
            'Analyse this food photo. Identify all visible foods and estimate portions. '
            'Return ONLY valid JSON, no markdown, no explanation:\n'
            '{"items": [{"food_name": "Chicken breast", "estimated_grams": 180, '
            '"protein": 31.0, "fat": 3.6, "carbs": 0.0, "calories": 165.0}]}\n'
            'Rules:\n'
            '- macros are per estimated_grams total (not per 100g)\n'
            '- estimated_grams is the visible portion\n'
            '- if multiple foods, one item per food\n'
            '- use English food names'
        )
    try:
        payload = json.dumps({
            'model': model,
            'max_tokens': 1024,
            'messages': [{
                'role': 'user',
                'content': [
                    {'type': 'image', 'source': {'type': 'base64', 'media_type': mime, 'data': b64}},
                    {'type': 'text', 'text': prompt},
                ],
            }],
        }).encode()
        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            if e.code == 401:
                return jsonify({'found': False, 'message': 'Invalid API key'})
            try:
                msg = json.loads(body).get('error', {}).get('message', body)
            except Exception:
                msg = body
            return jsonify({'found': False, 'message': f'Anthropic {e.code}: {msg}'})
        text = data['content'][0]['text']
        text = re.sub(r'^```(?:json)?\s*', '', text.strip())
        text = re.sub(r'\s*```$', '', text.strip())
        parsed = json.loads(text)
        items = parsed.get('items', [])
        if not isinstance(items, list) or len(items) == 0:
            return jsonify({'found': False, 'message': 'No food items recognised'})
        clean = []
        for it in items:
            try:
                clean.append({
                    'food_name': str(it.get('food_name', '')),
                    'estimated_grams': int(round(float(it.get('estimated_grams', 100)))),
                    'protein': round(float(it.get('protein', 0)), 1),
                    'fat': round(float(it.get('fat', 0)), 1),
                    'carbs': round(float(it.get('carbs', 0)), 1),
                    'calories': round(float(it.get('calories', 0)), 1),
                })
            except (TypeError, ValueError):
                continue
        if not clean:
            return jsonify({'found': False, 'message': 'No food items recognised'})
        usage = data.get('usage', {})
        return jsonify({
            'found': True,
            'items': clean,
            'usage': {
                'input_tokens': usage.get('input_tokens', 0),
                'output_tokens': usage.get('output_tokens', 0),
                'model': model,
            },
        })
    except Exception:
        return jsonify({'found': False, 'message': 'Recognition failed'})


def _fetch_openfoodfacts(q: str) -> list:
    """Search OpenFoodFacts and return a list of SavedFood-like dicts.
    Returns [] on any error (network, timeout, bad data).
    Saves new entries to saved_food with source='openfoodfacts'.
    """
    try:
        url = (
            f'https://search.openfoodfacts.org/search'
            f'?q={urllib.request.quote(q)}&json=true&page_size=5'
        )
        req = urllib.request.Request(url, headers={'User-Agent': 'NutriTrack/1.0'})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception:
        return []

    results = []
    for product in (data.get('products') or data.get('hits') or []):
        name = (product.get('product_name') or '').strip()
        if not name:
            continue
        nutriments = product.get('nutriments') or {}
        protein = nutriments.get('proteins_100g')
        fat = nutriments.get('fat_100g')
        carbs = nutriments.get('carbohydrates_100g')
        # Skip entries with missing macros
        if protein is None or fat is None or carbs is None:
            continue
        try:
            protein = round(float(protein), 1)
            fat = round(float(fat), 1)
            carbs = round(float(carbs), 1)
        except (TypeError, ValueError):
            continue
        # Skip entries with zero macros (bad data)
        if protein + fat + carbs == 0:
            continue
        kcal_raw = nutriments.get('energy-kcal_100g')
        if kcal_raw is not None:
            try:
                kcal = round(float(kcal_raw), 1)
            except (TypeError, ValueError):
                kcal = round(protein * 4 + fat * 9 + carbs * 4, 1)
        else:
            kcal = round(protein * 4 + fat * 9 + carbs * 4, 1)
        fiber_raw = nutriments.get('fiber_100g')
        fiber = round(float(fiber_raw), 1) if fiber_raw is not None else None

        # Check for existing record (case-insensitive) before inserting
        existing = (
            SavedFood.query
            .filter(SavedFood.name.ilike(name))
            .filter_by(is_archived=False)
            .first()
        )
        if existing:
            d = existing.to_dict()
            d['source'] = existing.source
            results.append(d)
        else:
            food = SavedFood(
                name=name,
                protein=protein,
                fat=fat,
                carbs=carbs,
                calories=kcal,
                fiber=fiber,
                default_serving=100.0,
                serving_unit='g',
                food_type='ingredient',
                source='openfoodfacts',
                is_archived=False,
            )
            db.session.add(food)
            try:
                db.session.commit()
                d = food.to_dict()
                d['source'] = 'openfoodfacts'
                results.append(d)
            except Exception:
                db.session.rollback()

    return results


@foods_bp.route('', methods=['GET'])
def search_foods():
    q = request.args.get('q', '').strip()
    source = request.args.get('source', '').strip()
    food_type = request.args.get('food_type', '').strip()
    query = SavedFood.query.filter_by(is_archived=False)
    if source:
        query = query.filter_by(source=source)
    if food_type:
        query = query.filter_by(food_type=food_type)

    lang = request.args.get('lang', 'en').strip()
    name_col = SavedFood.name_tr if lang == 'tr' else SavedFood.name

    if q:
        # Search both English and Turkish columns so "süt" and "milk" both work
        query = query.filter(
            or_(SavedFood.name.ilike(f'%{q}%'), SavedFood.name_tr.ilike(f'%{q}%'))
        )
        relevance = case(
            (name_col.ilike(q),           0),
            (name_col.ilike(f'{q}%'),     1),
            (name_col.ilike(f'% {q}%'),   2),
            (name_col.ilike(f'%,{q}%'),   2),
            else_=3,
        )
        type_order = case((SavedFood.food_type == 'ingredient', 0), else_=1)
        foods = query.order_by(relevance, type_order, name_col).limit(50).all()
    else:
        type_order = case((SavedFood.food_type == 'ingredient', 0), else_=1)
        foods = query.order_by(type_order, name_col).limit(50).all()

    # Fuzzy search supplement: when LIKE produces < 5 results and query is 3+ chars,
    # pull candidates starting with the same letter and rank by WRatio similarity.
    # This runs only in the `if q:` branch because `foods` is empty when q is blank.
    if q and len(q) >= 3 and len(foods) < 5:
        try:
            candidates = (
                SavedFood.query
                .filter(SavedFood.is_archived == False)  # noqa: E712
                .filter(SavedFood.name.ilike(q[0] + '%'))
                .limit(200)
                .all()
            )
            if candidates:
                cand_names = [f.name for f in candidates]
                fuzzy_matches = rfprocess.extract(
                    q, cand_names, scorer=fuzz.WRatio, limit=10, score_cutoff=60
                )
                existing_ids = {f.id for f in foods}
                fuzzy_extras = [
                    candidates[m[2]]
                    for m in fuzzy_matches
                    if candidates[m[2]].id not in existing_ids
                ]
                foods = list(foods) + fuzzy_extras[:10]
        except Exception:
            pass  # fuzzy failure must never break primary results

    local_results = [f.to_dict() for f in foods]

    # OpenFoodFacts fallback: only when local results are sparse and query is meaningful
    if q and len(q) >= 3 and len(local_results) < 3 and not source and not current_app.testing:
        off_results = _fetch_openfoodfacts(q)
        # Deduplicate by name (case-insensitive), local results take priority
        local_names = {r['name'].lower() for r in local_results}
        for r in off_results:
            if r['name'].lower() not in local_names:
                local_results.append(r)
                local_names.add(r['name'].lower())

    return jsonify(local_results)


@foods_bp.route('', methods=['POST'])
def create_food():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    try:
        protein = float(data['protein'])
        fat = float(data['fat'])
        carbs = float(data['carbs'])
    except (KeyError, TypeError, ValueError):
        return jsonify({'error': 'protein, fat, and carbs are required numeric fields'}), 400
    raw_cal = data.get('calories')
    calories = float(raw_cal) if raw_cal is not None else (protein * 4) + (fat * 9) + (carbs * 4)
    brand = data.get('brand', '')
    fiber = data.get('fiber')
    sugar = data.get('sugar')
    default_serving = data.get('default_serving', 100)
    serving_unit = data.get('serving_unit', 'g')
    food_type = data.get('food_type', 'ingredient')
    if food_type not in ('ingredient', 'meal'):
        food_type = 'ingredient'
    g_per_unit = data.get('g_per_unit')
    food = SavedFood(
        name=name,
        brand=brand.strip() if brand else None,
        protein=protein, fat=fat, carbs=carbs, calories=calories,
        fiber=float(fiber) if fiber is not None else None,
        sugar=float(sugar) if sugar is not None else None,
        default_serving=float(default_serving),
        serving_unit=serving_unit,
        food_type=food_type,
        source='custom',
        is_archived=False,
        g_per_unit=float(g_per_unit) if g_per_unit is not None else None,
    )
    db.session.add(food)
    db.session.commit()
    return jsonify(food.to_dict()), 201


@foods_bp.route('/<int:food_id>', methods=['PUT'])
def update_food(food_id: int):
    food = db.session.get(SavedFood, food_id)
    if food is None:
        return jsonify({'error': 'Food not found'}), 404
    if food.source == 'usda':
        return jsonify({'error': 'USDA foods cannot be edited. Clone the food first.'}), 403
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        food.name = data['name']
    if 'brand' in data:
        food.brand = data['brand']
    if 'protein' in data:
        food.protein = float(data['protein'])
    if 'fat' in data:
        food.fat = float(data['fat'])
    if 'carbs' in data:
        food.carbs = float(data['carbs'])
    if 'calories' in data and data['calories'] is not None:
        food.calories = float(data['calories'])
    elif 'protein' in data or 'fat' in data or 'carbs' in data:
        if 'calories' not in data:
            food.calories = (food.protein * 4) + (food.fat * 9) + (food.carbs * 4)
    if 'fiber' in data:
        food.fiber = float(data['fiber']) if data['fiber'] is not None else None
    if 'sugar' in data:
        food.sugar = float(data['sugar']) if data['sugar'] is not None else None
    if 'default_serving' in data:
        food.default_serving = float(data['default_serving'])
    if 'serving_unit' in data:
        food.serving_unit = data['serving_unit']
    if 'food_type' in data and data['food_type'] in ('ingredient', 'meal'):
        food.food_type = data['food_type']
    if 'g_per_unit' in data:
        food.g_per_unit = float(data['g_per_unit']) if data['g_per_unit'] is not None else None
    db.session.commit()
    return jsonify(food.to_dict())


@foods_bp.route('/<int:food_id>', methods=['DELETE'])
def delete_food(food_id: int):
    food = db.session.get(SavedFood, food_id)
    if food is None:
        return jsonify({'error': 'Food not found'}), 404
    if food.source == 'usda':
        return jsonify({'error': 'USDA foods cannot be deleted. Clone the food first.'}), 403
    food.is_archived = True
    db.session.commit()
    return jsonify({'archived': food_id})


@foods_bp.route('/<int:food_id>/clone', methods=['POST'])
def clone_food(food_id: int):
    food = db.session.get(SavedFood, food_id)
    if food is None:
        return jsonify({'error': 'Food not found'}), 404
    clone = SavedFood(
        name=food.name, brand=food.brand, category=food.category,
        protein=food.protein, fat=food.fat, carbs=food.carbs, calories=food.calories,
        fiber=food.fiber, sugar=food.sugar,
        default_serving=food.default_serving, serving_unit=food.serving_unit,
        food_type=food.food_type, source='custom', is_archived=False,
    )
    db.session.add(clone)
    db.session.commit()
    return jsonify(clone.to_dict()), 201


@foods_bp.route('/import', methods=['POST'])
def import_foods_csv():
    """Bulk-import custom foods from a CSV file upload.

    Expects multipart/form-data with a 'file' field (CSV).
    Required columns: name, protein, fat, carbs
    Optional columns: calories, serving_size, serving_unit
    Returns: { imported: N, skipped: N, errors: [...] }
    """
    if 'file' not in request.files:
        return jsonify({'error': 'file is required'}), 400
    upload = request.files['file']
    if not upload.filename:
        return jsonify({'error': 'No file selected'}), 400

    # Decode — try UTF-8 with BOM first, fall back to latin-1
    raw_bytes = upload.read()
    content = None
    for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            content = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if content is None:
        return jsonify({'error': 'Cannot decode file. Use UTF-8 encoding.'}), 400

    try:
        reader = csv.DictReader(io.StringIO(content))
        fieldnames = reader.fieldnames
    except Exception:
        return jsonify({'error': 'Invalid CSV format'}), 400

    if not fieldnames:
        return jsonify({'error': 'Empty or invalid CSV file'}), 400

    # Normalise header names (strip whitespace, lowercase)
    norm_fields = {h.strip().lower() for h in fieldnames}
    required_cols = {'name', 'protein', 'fat', 'carbs'}
    missing = required_cols - norm_fields
    if missing:
        return jsonify({'error': f'Missing required columns: {", ".join(sorted(missing))}'}), 400

    # Pre-load existing names for O(1) duplicate checks
    existing_names = {
        row[0].lower()
        for row in db.session.query(SavedFood.name).filter_by(is_archived=False).all()
    }

    imported = 0
    skipped = 0
    errors = []
    total = 0

    for row in reader:
        total += 1
        if total > 500:
            errors.append('Maximum 500 rows per import exceeded — remaining rows ignored')
            break

        # Normalise row keys
        norm_row = {k.strip().lower(): (v or '').strip() for k, v in row.items() if k}

        name = norm_row.get('name', '').strip()
        if not name:
            errors.append(f'Row {total + 1}: name is required')
            continue

        if name.lower() in existing_names:
            skipped += 1
            continue

        # Parse required numeric macros
        try:
            protein = float(norm_row.get('protein', ''))
            fat = float(norm_row.get('fat', ''))
            carbs = float(norm_row.get('carbs', ''))
        except (ValueError, TypeError):
            errors.append(f'Row {total + 1} ("{name}"): protein, fat, carbs must be numeric')
            continue

        if protein < 0 or fat < 0 or carbs < 0:
            errors.append(f'Row {total + 1} ("{name}"): macro values must be >= 0')
            continue

        # Optional fields
        cal_raw = norm_row.get('calories', '').strip()
        try:
            calories = float(cal_raw) if cal_raw else (protein * 4 + fat * 9 + carbs * 4)
        except ValueError:
            calories = protein * 4 + fat * 9 + carbs * 4

        srv_raw = norm_row.get('serving_size', '').strip()
        try:
            serving_size = float(srv_raw) if srv_raw else 100.0
            if serving_size <= 0:
                serving_size = 100.0
        except ValueError:
            serving_size = 100.0

        serving_unit = norm_row.get('serving_unit', '').strip() or 'g'

        try:
            food = SavedFood(
                name=name,
                protein=round(protein, 2),
                fat=round(fat, 2),
                carbs=round(carbs, 2),
                calories=round(calories, 1),
                default_serving=serving_size,
                serving_unit=serving_unit,
                food_type='ingredient',
                source='custom',
                is_archived=False,
            )
            db.session.add(food)
            existing_names.add(name.lower())
            imported += 1
        except Exception as exc:
            errors.append(f'Row {total + 1} ("{name}"): {exc}')

    if imported > 0:
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            return jsonify({'error': f'Database error: {exc}'}), 500

    return jsonify({'imported': imported, 'skipped': skipped, 'errors': errors[:20]})