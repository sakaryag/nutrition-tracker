from functools import wraps
from flask import Blueprint, jsonify, request, current_app, session
from datetime import date, datetime
from models import db
from models.user import User
from models.nutrition_plan import NutritionPlan
from models.plan_task import PlanTask
from models.user_plan_assignment import UserPlanAssignment

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        uid = session.get('user_id')
        if uid is None and current_app.config.get('AUTH_ENABLED'):
            return jsonify({'error': 'Authentication required'}), 401
        if uid is not None:
            user = db.session.get(User, uid)
            if user is None or not getattr(user, 'is_admin', False):
                return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


# ── Plans ──────────────────────────────────────────────────────────────────

@admin_bp.route('/plans', methods=['GET'])
@require_admin
def list_plans():
    plans = NutritionPlan.query.order_by(NutritionPlan.created_at.desc()).all()
    return jsonify([p.to_dict() for p in plans])


@admin_bp.route('/plans', methods=['POST'])
@require_admin
def create_plan():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    plan = NutritionPlan(
        name=name,
        description=data.get('description', '').strip() or None,
        duration_days=int(data.get('duration_days', 7)),
        created_by=session.get('user_id'),
        is_public=bool(data.get('is_public', False)),
    )
    db.session.add(plan)
    db.session.commit()
    return jsonify(plan.to_dict()), 201


@admin_bp.route('/plans/<int:plan_id>', methods=['PUT'])
@require_admin
def update_plan(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    data = request.get_json(silent=True) or {}
    if 'name' in data:
        plan.name = data['name'].strip()
    if 'description' in data:
        plan.description = data['description'].strip() or None
    if 'duration_days' in data:
        plan.duration_days = int(data['duration_days'])
    if 'is_public' in data:
        plan.is_public = bool(data['is_public'])
    db.session.commit()
    return jsonify(plan.to_dict())


@admin_bp.route('/plans/<int:plan_id>', methods=['DELETE'])
@require_admin
def delete_plan(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    db.session.delete(plan)
    db.session.commit()
    return jsonify({'deleted': plan_id})


# ── Tasks ──────────────────────────────────────────────────────────────────

@admin_bp.route('/plans/<int:plan_id>/tasks', methods=['GET'])
@require_admin
def list_tasks(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    tasks = PlanTask.query.filter_by(plan_id=plan_id).order_by(PlanTask.day_offset, PlanTask.id).all()
    return jsonify([t.to_dict() for t in tasks])


@admin_bp.route('/plans/<int:plan_id>/tasks', methods=['POST'])
@require_admin
def add_task(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    data = request.get_json(silent=True) or {}
    description = data.get('description', '').strip()
    if not description:
        return jsonify({'error': 'description is required'}), 400
    task_type = data.get('task_type', 'food')
    if task_type not in ('food', 'habit', 'note'):
        return jsonify({'error': "task_type must be 'food', 'habit', or 'note'"}), 400
    task = PlanTask(
        plan_id=plan_id,
        day_offset=int(data.get('day_offset', 0)),
        task_type=task_type,
        description=description,
        food_name=data.get('food_name', '').strip() or None,
        quantity=float(data['quantity']) if data.get('quantity') is not None else None,
        unit=data.get('unit', '').strip() or None,
        repeat_days=data.get('repeat_days'),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@admin_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@require_admin
def delete_task(task_id):
    task = db.session.get(PlanTask, task_id)
    if task is None:
        return jsonify({'error': 'Task not found'}), 404
    db.session.delete(task)
    db.session.commit()
    return jsonify({'deleted': task_id})


# ── Users ──────────────────────────────────────────────────────────────────

@admin_bp.route('/users', methods=['GET'])
@require_admin
def list_users():
    users = User.query.order_by(User.username).all()
    result = []
    for u in users:
        assignment = UserPlanAssignment.query.filter_by(
            user_id=u.id, is_active=True
        ).order_by(UserPlanAssignment.created_at.desc()).first()
        active_plan_name = assignment.plan.name if assignment else None
        result.append({
            'id': u.id,
            'username': u.username,
            'is_admin': getattr(u, 'is_admin', False),
            'plan_feature_enabled': getattr(u, 'plan_feature_enabled', False),
            'active_plan_name': active_plan_name,
            'created_at': u.created_at.isoformat() if u.created_at else None,
        })
    return jsonify(result)


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_admin
def update_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({'error': 'User not found'}), 404
    data = request.get_json(silent=True) or {}
    if 'is_admin' in data:
        user.is_admin = bool(data['is_admin'])
    if 'plan_feature_enabled' in data:
        user.plan_feature_enabled = bool(data['plan_feature_enabled'])
    db.session.commit()
    return jsonify({
        'id': user.id,
        'username': user.username,
        'is_admin': getattr(user, 'is_admin', False),
        'plan_feature_enabled': getattr(user, 'plan_feature_enabled', False),
    })


@admin_bp.route('/users/<int:user_id>/assign-plan', methods=['POST'])
@require_admin
def assign_plan(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({'error': 'User not found'}), 404
    data = request.get_json(silent=True) or {}
    plan_id = data.get('plan_id')
    raw_date = data.get('start_date')
    if not plan_id:
        return jsonify({'error': 'plan_id is required'}), 400
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    try:
        start_date = date.fromisoformat(raw_date) if raw_date else date.today()
    except ValueError:
        start_date = date.today()
    # Deactivate existing assignments
    UserPlanAssignment.query.filter_by(user_id=user_id, is_active=True).update({'is_active': False})
    assignment = UserPlanAssignment(
        user_id=user_id,
        plan_id=plan_id,
        start_date=start_date,
        is_active=True,
        assigned_by=session.get('user_id'),
    )
    db.session.add(assignment)
    db.session.commit()
    return jsonify(assignment.to_dict()), 201