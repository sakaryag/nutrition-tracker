import io
import csv
from flask import Blueprint, request, Response, current_app, session, jsonify
from datetime import date
from models.food_entry import FoodEntry

export_bp = Blueprint('export', __name__, url_prefix='/api/export')


@export_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


@export_bp.route('', methods=['GET'])
def export_entries():
    """GET /api/export?start=YYYY-MM-DD&end=YYYY-MM-DD"""
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    if not start_str or not end_str:
        return Response('start and end query params are required', status=400)

    try:
        start_date = date.fromisoformat(start_str)
        end_date = date.fromisoformat(end_str)
    except ValueError:
        return Response('Invalid date format, use YYYY-MM-DD', status=400)

    entries = (
        FoodEntry.query
        .filter(FoodEntry.entry_date >= start_date, FoodEntry.entry_date <= end_date)
        .order_by(FoodEntry.entry_date, FoodEntry.entry_time)
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        'date', 'time', 'food_name', 'meal_type',
        'protein', 'fat', 'carbs', 'calories',
        'serving_size', 'serving_unit',
    ])
    for e in entries:
        writer.writerow([
            e.entry_date.isoformat(),
            e.entry_time.isoformat(),
            e.food_name,
            e.meal_type,
            e.protein,
            e.fat,
            e.carbs,
            e.calories,
            e.serving_size,
            e.serving_unit,
        ])

    filename = f'nutritrack_{start_str}_{end_str}.csv'
    return Response(
        buf.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )