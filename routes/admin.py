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


def _assert_owner(plan):
    """403 if AUTH is enabled and the current user doesn't own the plan."""
    if not current_app.config.get('AUTH_ENABLED'):
        return
    uid = session.get('user_id')
    if uid is not None and plan.created_by is not None and plan.created_by != uid:
        from flask import abort
        abort(403)


# Ã¢â€â‚¬Ã¢â€â‚¬ Plans Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

@admin_bp.route('/plans', methods=['GET'])
@require_plan_access
def list_plans():
    uid = session.get('user_id')
    query = NutritionPlan.query
    # Multi-tenant: filter by creator when auth is enabled and user is set
    if current_app.config.get('AUTH_ENABLED') and uid is not None:
        query = query.filter(
            (NutritionPlan.created_by == uid) | (NutritionPlan.created_by == None)
        )
    is_template = request.args.get('is_template')
    if is_template is not None:
        query = query.filter(NutritionPlan.is_template == (is_template == '1'))
    plans = query.order_by(NutritionPlan.created_at.desc()).all()
    return jsonify([p.to_dict() for p in plans])


@admin_bp.route('/plans', methods=['POST'])
@require_plan_access
def create_plan():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    plan = NutritionPlan(
        name=name,
        name_tr=data.get('name_tr', '').strip() or None,
        description=data.get('description', '').strip() or None,
        duration_days=int(data.get('duration_days', 7)),
        created_by=session.get('user_id'),
        is_public=bool(data.get('is_public', False)),
        status=data.get('status', 'draft'),
        is_template=bool(data.get('is_template', False)),
        locale=data.get('locale', 'tr'),
    )
    db.session.add(plan)
    db.session.commit()
    return jsonify(plan.to_dict()), 201


@admin_bp.route('/plans/<int:plan_id>', methods=['PUT'])
@require_plan_access
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
    if 'status' in data:
        plan.status = data['status']
    if 'is_template' in data:
        plan.is_template = bool(data['is_template'])
    if 'name_tr' in data:
        plan.name_tr = data['name_tr'].strip() or None
    if 'locale' in data:
        plan.locale = data['locale']
    db.session.commit()
    return jsonify(plan.to_dict())


@admin_bp.route('/plans/<int:plan_id>', methods=['DELETE'])
@require_plan_access
def delete_plan(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    db.session.delete(plan)
    db.session.commit()
    return jsonify({'deleted': plan_id})


# Ã¢â€â‚¬Ã¢â€â‚¬ Tasks Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

@admin_bp.route('/plans/<int:plan_id>/tasks', methods=['GET'])
@require_plan_access
def list_tasks(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    tasks = PlanTask.query.filter_by(plan_id=plan_id).order_by(PlanTask.day_offset, PlanTask.id).all()
    return jsonify([t.to_dict() for t in tasks])


@admin_bp.route('/plans/<int:plan_id>/tasks', methods=['POST'])
@require_plan_access
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
@require_plan_access
def delete_task(task_id):
    task = db.session.get(PlanTask, task_id)
    if task is None:
        return jsonify({'error': 'Task not found'}), 404
    db.session.delete(task)
    db.session.commit()
    return jsonify({'deleted': task_id})


# Ã¢â€â‚¬Ã¢â€â‚¬ Users Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

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
    db.session.flush()  # get assignment.id
    # Create a dietitian_access row (denied by default) so client sees the consent toggle
    dietitian_id = session.get('user_id')
    if dietitian_id:
        existing = db.session.execute(
            db.text('SELECT id FROM dietitian_access WHERE dietitian_id=:d AND client_id=:c'),
            {'d': dietitian_id, 'c': user_id},
        ).fetchone()
        if not existing:
            try:
                from datetime import datetime as _dt
                db.session.execute(
                    db.text(
                        'INSERT INTO dietitian_access (dietitian_id, client_id, allowed, created_at, updated_at) '
                        'VALUES (:d, :c, :a, :t, :t)'
                    ),
                    {'d': dietitian_id, 'c': user_id, 'a': False, 't': _dt.utcnow()},
                )
            except Exception:
                pass
    db.session.commit()
    return jsonify(assignment.to_dict()), 201

# -- Program Day CRUD -------------------------------------------------------

@admin_bp.route('/plans/<int:plan_id>/days', methods=['GET'])
@require_plan_access
def list_days(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    _assert_owner(plan)
    from models.program_day import ProgramDay
    days = ProgramDay.query.filter_by(program_id=plan_id).order_by(ProgramDay.sort_order).all()
    return jsonify([d.to_dict() for d in days])


@admin_bp.route('/plans/<int:plan_id>/days', methods=['POST'])
@require_plan_access
def add_day(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    _assert_owner(plan)
    from models.program_day import ProgramDay
    from datetime import datetime, timezone
    data = request.get_json(silent=True) or {}
    # Find next available day_offset
    existing_offsets = {d.day_offset for d in ProgramDay.query.filter_by(program_id=plan_id).all()}
    offset = 0
    while offset in existing_offsets:
        offset += 1
    day = ProgramDay(
        program_id=plan_id,
        day_offset=data.get('day_offset', offset),
        label=data.get('label') or f'Day {offset + 1}',
        label_tr=data.get('label_tr') or None,
        notes=data.get('notes') or None,
        sort_order=data.get('sort_order', offset),
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(day)
    db.session.commit()
    return jsonify(day.to_dict()), 201


@admin_bp.route('/days/<int:day_id>', methods=['PUT'])
@require_plan_access
def update_day(day_id):
    from models.program_day import ProgramDay
    day = db.session.get(ProgramDay, day_id)
    if day is None:
        return jsonify({'error': 'Day not found'}), 404
    _assert_owner(day.program)
    data = request.get_json(silent=True) or {}
    if 'label' in data:
        day.label = data['label']
    if 'label_tr' in data:
        day.label_tr = data['label_tr'] or None
    if 'notes' in data:
        day.notes = data['notes'] or None
    if 'sort_order' in data:
        day.sort_order = int(data['sort_order'])
    db.session.commit()
    return jsonify(day.to_dict())


@admin_bp.route('/days/<int:day_id>', methods=['DELETE'])
@require_plan_access
def delete_day(day_id):
    from models.program_day import ProgramDay
    day = db.session.get(ProgramDay, day_id)
    if day is None:
        return jsonify({'error': 'Day not found'}), 404
    _assert_owner(day.program)
    db.session.delete(day)
    db.session.commit()
    return jsonify({'deleted': day_id})


@admin_bp.route('/days/<int:day_id>/copy', methods=['POST'])
@require_plan_access
def copy_day(day_id):
    """Deep-clone a day (all slots and items) to a new day in the same program."""
    from models.program_day import ProgramDay
    from models.meal_slot import MealSlot
    from models.slot_item import SlotItem
    from datetime import datetime, timezone
    day = db.session.get(ProgramDay, day_id)
    if day is None:
        return jsonify({'error': 'Day not found'}), 404
    _assert_owner(day.program)
    data = request.get_json(silent=True) or {}
    existing_offsets = {d.day_offset for d in ProgramDay.query.filter_by(program_id=day.program_id).all()}
    offset = 0
    while offset in existing_offsets:
        offset += 1
    now = datetime.now(timezone.utc)
    new_day = ProgramDay(
        program_id=day.program_id,
        day_offset=data.get('day_offset', offset),
        label=data.get('label') or (day.label + ' (copy)' if day.label else f'Day {offset + 1}'),
        label_tr=day.label_tr,
        notes=day.notes,
        sort_order=data.get('sort_order', offset),
        created_at=now,
    )
    db.session.add(new_day)
    db.session.flush()
    for slot in day.slots:
        new_slot = MealSlot(
            day_id=new_day.id,
            slot_name=slot.slot_name,
            slot_name_tr=slot.slot_name_tr,
            sort_order=slot.sort_order,
            content_pattern=slot.content_pattern,
            is_optional=slot.is_optional,
            created_at=now,
        )
        db.session.add(new_slot)
        db.session.flush()
        for item in slot.items:
            new_item = SlotItem(
                slot_id=new_slot.id,
                alternative_group=item.alternative_group,
                rotation_frequency=item.rotation_frequency,
                saved_food_id=item.saved_food_id,
                recipe_id=item.recipe_id,
                exchange_category_id=item.exchange_category_id,
                food_name_override=item.food_name_override,
                quantity=item.quantity,
                unit=item.unit,
                is_fallback=item.is_fallback,
                sort_order=item.sort_order,
                notes=item.notes,
                notes_tr=item.notes_tr,
            )
            db.session.add(new_item)
    db.session.commit()
    return jsonify(new_day.to_dict()), 201


@admin_bp.route('/days/<int:day_id>/copy-to-remaining', methods=['POST'])
@require_plan_access
def copy_day_to_remaining(day_id):
    """Clone the source day's slots/items into every day in the same program that has no slots."""
    from models.program_day import ProgramDay
    from models.meal_slot import MealSlot
    from models.slot_item import SlotItem
    from datetime import datetime, timezone
    day = db.session.get(ProgramDay, day_id)
    if day is None:
        return jsonify({'error': 'Day not found'}), 404
    _assert_owner(day.program)
    now = datetime.now(timezone.utc)
    target_days = ProgramDay.query.filter(
        ProgramDay.program_id == day.program_id,
        ProgramDay.id != day_id,
    ).all()
    # Only copy to days that currently have no slots
    filled = 0
    for target in target_days:
        if target.slots:
            continue
        for slot in day.slots:
            new_slot = MealSlot(
                day_id=target.id,
                slot_name=slot.slot_name,
                slot_name_tr=slot.slot_name_tr,
                sort_order=slot.sort_order,
                content_pattern=slot.content_pattern,
                is_optional=slot.is_optional,
                created_at=now,
            )
            db.session.add(new_slot)
            db.session.flush()
            for item in slot.items:
                new_item = SlotItem(
                    slot_id=new_slot.id,
                    alternative_group=item.alternative_group,
                    rotation_frequency=item.rotation_frequency,
                    saved_food_id=item.saved_food_id,
                    recipe_id=item.recipe_id,
                    exchange_category_id=item.exchange_category_id,
                    food_name_override=item.food_name_override,
                    quantity=item.quantity,
                    unit=item.unit,
                    is_fallback=item.is_fallback,
                    sort_order=item.sort_order,
                    notes=item.notes,
                    notes_tr=item.notes_tr,
                )
                db.session.add(new_item)
        filled += 1
    db.session.commit()
    return jsonify({'filled_days': filled})


# -- MealSlot CRUD -----------------------------------------------------------

@admin_bp.route('/days/<int:day_id>/slots', methods=['GET'])
@require_plan_access
def list_slots(day_id):
    from models.program_day import ProgramDay
    from models.meal_slot import MealSlot
    day = db.session.get(ProgramDay, day_id)
    if day is None:
        return jsonify({'error': 'Day not found'}), 404
    _assert_owner(day.program)
    slots = MealSlot.query.filter_by(day_id=day_id).order_by(MealSlot.sort_order).all()
    return jsonify([s.to_dict() for s in slots])


@admin_bp.route('/days/<int:day_id>/slots', methods=['POST'])
@require_plan_access
def add_slot(day_id):
    from models.program_day import ProgramDay
    from models.meal_slot import MealSlot
    from datetime import datetime, timezone
    day = db.session.get(ProgramDay, day_id)
    if day is None:
        return jsonify({'error': 'Day not found'}), 404
    _assert_owner(day.program)
    data = request.get_json(silent=True) or {}
    slot_name = data.get('slot_name', '').strip()
    if not slot_name:
        return jsonify({'error': 'slot_name is required'}), 400
    slot = MealSlot(
        day_id=day_id,
        slot_name=slot_name,
        slot_name_tr=data.get('slot_name_tr') or None,
        sort_order=data.get('sort_order', 0),
        content_pattern=data.get('content_pattern', 'A'),
        is_optional=bool(data.get('is_optional', False)),
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(slot)
    db.session.commit()
    return jsonify(slot.to_dict()), 201


@admin_bp.route('/slots/<int:slot_id>', methods=['PUT'])
@require_plan_access
def update_slot(slot_id):
    from models.meal_slot import MealSlot
    slot = db.session.get(MealSlot, slot_id)
    if slot is None:
        return jsonify({'error': 'Slot not found'}), 404
    _assert_owner(slot.day.program)
    data = request.get_json(silent=True) or {}
    if 'slot_name' in data:
        slot.slot_name = data['slot_name'].strip()
    if 'slot_name_tr' in data:
        slot.slot_name_tr = data['slot_name_tr'] or None
    if 'sort_order' in data:
        slot.sort_order = int(data['sort_order'])
    if 'content_pattern' in data:
        slot.content_pattern = data['content_pattern']
    if 'is_optional' in data:
        slot.is_optional = bool(data['is_optional'])
    db.session.commit()
    return jsonify(slot.to_dict())


@admin_bp.route('/slots/<int:slot_id>', methods=['DELETE'])
@require_plan_access
def delete_slot(slot_id):
    from models.meal_slot import MealSlot
    slot = db.session.get(MealSlot, slot_id)
    if slot is None:
        return jsonify({'error': 'Slot not found'}), 404
    _assert_owner(slot.day.program)
    db.session.delete(slot)
    db.session.commit()
    return jsonify({'deleted': slot_id})


# -- SlotItem CRUD -----------------------------------------------------------

@admin_bp.route('/slots/<int:slot_id>/items', methods=['GET'])
@require_plan_access
def list_slot_items(slot_id):
    from models.meal_slot import MealSlot
    from models.slot_item import SlotItem
    slot = db.session.get(MealSlot, slot_id)
    if slot is None:
        return jsonify({'error': 'Slot not found'}), 404
    _assert_owner(slot.day.program)
    items = SlotItem.query.filter_by(slot_id=slot_id).order_by(SlotItem.sort_order).all()
    return jsonify([i.to_dict() for i in items])


@admin_bp.route('/slots/<int:slot_id>/items', methods=['POST'])
@require_plan_access
def add_slot_item(slot_id):
    from models.meal_slot import MealSlot
    from models.slot_item import SlotItem
    slot = db.session.get(MealSlot, slot_id)
    if slot is None:
        return jsonify({'error': 'Slot not found'}), 404
    _assert_owner(slot.day.program)
    data = request.get_json(silent=True) or {}
    item = SlotItem(
        slot_id=slot_id,
        alternative_group=data.get('alternative_group'),
        rotation_frequency=data.get('rotation_frequency'),
        saved_food_id=data.get('saved_food_id'),
        recipe_id=data.get('recipe_id'),
        exchange_category_id=data.get('exchange_category_id'),
        food_name_override=data.get('food_name_override') or None,
        quantity=float(data['quantity']) if data.get('quantity') is not None else None,
        unit=data.get('unit') or None,
        is_fallback=bool(data.get('is_fallback', False)),
        sort_order=data.get('sort_order', 0),
        notes=data.get('notes') or None,
        notes_tr=data.get('notes_tr') or None,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@admin_bp.route('/slot-items/<int:item_id>', methods=['PUT'])
@require_plan_access
def update_slot_item(item_id):
    from models.slot_item import SlotItem
    item = db.session.get(SlotItem, item_id)
    if item is None:
        return jsonify({'error': 'Item not found'}), 404
    _assert_owner(item.slot.day.program)
    data = request.get_json(silent=True) or {}
    for field in ('alternative_group', 'rotation_frequency', 'saved_food_id',
                  'recipe_id', 'exchange_category_id', 'food_name_override',
                  'quantity', 'unit', 'is_fallback', 'sort_order', 'notes', 'notes_tr'):
        if field in data:
            setattr(item, field, data[field])
    db.session.commit()
    return jsonify(item.to_dict())


@admin_bp.route('/slot-items/<int:item_id>', methods=['DELETE'])
@require_plan_access
def delete_slot_item(item_id):
    from models.slot_item import SlotItem
    item = db.session.get(SlotItem, item_id)
    if item is None:
        return jsonify({'error': 'Item not found'}), 404
    _assert_owner(item.slot.day.program)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'deleted': item_id})


# -- Guidelines CRUD ---------------------------------------------------------

@admin_bp.route('/plans/<int:plan_id>/guidelines', methods=['GET'])
@require_plan_access
def list_guidelines(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    _assert_owner(plan)
    from models.program_guideline import ProgramGuideline
    gs = ProgramGuideline.query.filter_by(program_id=plan_id).order_by(ProgramGuideline.sort_order).all()
    return jsonify([g.to_dict() for g in gs])


@admin_bp.route('/plans/<int:plan_id>/guidelines', methods=['POST'])
@require_plan_access
def add_guideline(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    _assert_owner(plan)
    from models.program_guideline import ProgramGuideline
    from datetime import datetime, timezone
    data = request.get_json(silent=True) or {}
    if not data.get('rule_text', '').strip():
        return jsonify({'error': 'rule_text is required'}), 400
    g = ProgramGuideline(
        program_id=plan_id,
        guideline_type=data.get('guideline_type', 'general'),
        target_category_id=data.get('target_category_id'),
        target_food_id=data.get('target_food_id'),
        frequency_min=data.get('frequency_min'),
        frequency_max=data.get('frequency_max'),
        daily_qty_min=data.get('daily_qty_min'),
        daily_qty_max=data.get('daily_qty_max'),
        unit=data.get('unit') or None,
        rule_text=data['rule_text'].strip(),
        rule_text_tr=data.get('rule_text_tr', '').strip() or None,
        sort_order=data.get('sort_order', 0),
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(g)
    db.session.commit()
    return jsonify(g.to_dict()), 201


@admin_bp.route('/guidelines/<int:gid>', methods=['PUT'])
@require_plan_access
def update_guideline(gid):
    from models.program_guideline import ProgramGuideline
    g = db.session.get(ProgramGuideline, gid)
    if g is None:
        return jsonify({'error': 'Guideline not found'}), 404
    _assert_owner(g.program)
    data = request.get_json(silent=True) or {}
    for field in ('guideline_type', 'target_category_id', 'target_food_id',
                  'frequency_min', 'frequency_max', 'daily_qty_min', 'daily_qty_max',
                  'unit', 'rule_text', 'rule_text_tr', 'sort_order'):
        if field in data:
            setattr(g, field, data[field] if data[field] != '' else None)
    db.session.commit()
    return jsonify(g.to_dict())


@admin_bp.route('/guidelines/<int:gid>', methods=['DELETE'])
@require_plan_access
def delete_guideline(gid):
    from models.program_guideline import ProgramGuideline
    g = db.session.get(ProgramGuideline, gid)
    if g is None:
        return jsonify({'error': 'Guideline not found'}), 404
    _assert_owner(g.program)
    db.session.delete(g)
    db.session.commit()
    return jsonify({'deleted': gid})


# -- Weekly Category Quota CRUD ----------------------------------------------

@admin_bp.route('/plans/<int:plan_id>/quotas', methods=['GET'])
@require_plan_access
def list_quotas(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    _assert_owner(plan)
    from models.weekly_category_quota import WeeklyCategoryQuota
    quotas = WeeklyCategoryQuota.query.filter_by(program_id=plan_id).all()
    return jsonify([q.to_dict() for q in quotas])


@admin_bp.route('/plans/<int:plan_id>/quotas', methods=['POST'])
@require_plan_access
def add_quota(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    _assert_owner(plan)
    from models.weekly_category_quota import WeeklyCategoryQuota
    data = request.get_json(silent=True) or {}
    if not data.get('exchange_category_id') or not data.get('quota_per_week'):
        return jsonify({'error': 'exchange_category_id and quota_per_week are required'}), 400
    q = WeeklyCategoryQuota(
        program_id=plan_id,
        exchange_category_id=int(data['exchange_category_id']),
        quota_per_week=int(data['quota_per_week']),
        slot_id=data.get('slot_id'),
        notes=data.get('notes') or None,
    )
    db.session.add(q)
    db.session.commit()
    return jsonify(q.to_dict()), 201


@admin_bp.route('/quotas/<int:qid>', methods=['PUT'])
@require_plan_access
def update_quota(qid):
    from models.weekly_category_quota import WeeklyCategoryQuota
    q = db.session.get(WeeklyCategoryQuota, qid)
    if q is None:
        return jsonify({'error': 'Quota not found'}), 404
    plan = db.session.get(NutritionPlan, q.program_id)
    _assert_owner(plan)
    data = request.get_json(silent=True) or {}
    for field in ('exchange_category_id', 'quota_per_week', 'slot_id', 'notes'):
        if field in data:
            setattr(q, field, data[field])
    db.session.commit()
    return jsonify(q.to_dict())


@admin_bp.route('/quotas/<int:qid>', methods=['DELETE'])
@require_plan_access
def delete_quota(qid):
    from models.weekly_category_quota import WeeklyCategoryQuota
    q = db.session.get(WeeklyCategoryQuota, qid)
    if q is None:
        return jsonify({'error': 'Quota not found'}), 404
    plan = db.session.get(NutritionPlan, q.program_id)
    _assert_owner(plan)
    db.session.delete(q)
    db.session.commit()
    return jsonify({'deleted': qid})


# -- Template operations -----------------------------------------------------

@admin_bp.route('/plans/<int:plan_id>/promote-to-template', methods=['POST'])
@require_plan_access
def promote_to_template(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    _assert_owner(plan)
    plan.is_template = True
    db.session.commit()
    return jsonify(plan.to_dict())


@admin_bp.route('/plans/<int:plan_id>/clone-from-template', methods=['POST'])
@require_plan_access
def clone_plan(plan_id):
    """Deep-clone a template plan into a new editable program."""
    source = db.session.get(NutritionPlan, plan_id)
    if source is None:
        return jsonify({'error': 'Plan not found'}), 404
    from models.program_day import ProgramDay
    from models.meal_slot import MealSlot
    from models.slot_item import SlotItem
    from models.program_guideline import ProgramGuideline
    from models.weekly_category_quota import WeeklyCategoryQuota
    from datetime import datetime, timezone
    data = request.get_json(silent=True) or {}
    now = datetime.now(timezone.utc)
    uid = session.get('user_id')
    new_plan = NutritionPlan(
        name=data.get('name') or (source.name + ' (copy)'),
        name_tr=source.name_tr,
        description=source.description,
        duration_days=source.duration_days,
        created_by=uid,
        is_public=False,
        status='draft',
        is_template=False,
        parent_template_id=source.id,
        current_version=1,
        locale=source.locale,
    )
    db.session.add(new_plan)
    db.session.flush()
    for day in source.days:
        new_day = ProgramDay(
            program_id=new_plan.id, day_offset=day.day_offset, label=day.label,
            label_tr=day.label_tr, notes=day.notes, sort_order=day.sort_order, created_at=now,
        )
        db.session.add(new_day)
        db.session.flush()
        for slot in day.slots:
            new_slot = MealSlot(
                day_id=new_day.id, slot_name=slot.slot_name, slot_name_tr=slot.slot_name_tr,
                sort_order=slot.sort_order, content_pattern=slot.content_pattern,
                is_optional=slot.is_optional, created_at=now,
            )
            db.session.add(new_slot)
            db.session.flush()
            for item in slot.items:
                db.session.add(SlotItem(
                    slot_id=new_slot.id, alternative_group=item.alternative_group,
                    rotation_frequency=item.rotation_frequency, saved_food_id=item.saved_food_id,
                    recipe_id=item.recipe_id, exchange_category_id=item.exchange_category_id,
                    food_name_override=item.food_name_override, quantity=item.quantity,
                    unit=item.unit, is_fallback=item.is_fallback, sort_order=item.sort_order,
                    notes=item.notes, notes_tr=item.notes_tr,
                ))
    for g in source.guidelines:
        db.session.add(ProgramGuideline(
            program_id=new_plan.id, guideline_type=g.guideline_type,
            target_category_id=g.target_category_id, target_food_id=g.target_food_id,
            frequency_min=g.frequency_min, frequency_max=g.frequency_max,
            daily_qty_min=g.daily_qty_min, daily_qty_max=g.daily_qty_max,
            unit=g.unit, rule_text=g.rule_text, rule_text_tr=g.rule_text_tr,
            sort_order=g.sort_order, created_at=now,
        ))
    for q in WeeklyCategoryQuota.query.filter_by(program_id=source.id).all():
        db.session.add(WeeklyCategoryQuota(
            program_id=new_plan.id, exchange_category_id=q.exchange_category_id,
            quota_per_week=q.quota_per_week, notes=q.notes,
        ))
    db.session.commit()
    return jsonify(new_plan.to_dict()), 201


# -- Program Versioning ------------------------------------------------------

def _snapshot_plan(plan):
    """Serialize the entire plan tree to JSON for versioning."""
    import json
    from models.program_guideline import ProgramGuideline
    data = plan.to_dict()
    data['days'] = [d.to_dict() for d in plan.days]
    data['guidelines'] = [g.to_dict() for g in plan.guidelines]
    return json.dumps(data)


@admin_bp.route('/plans/<int:plan_id>/versions', methods=['GET'])
@require_plan_access
def list_versions(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    _assert_owner(plan)
    from models.program_version import ProgramVersion
    versions = ProgramVersion.query.filter_by(program_id=plan_id).order_by(ProgramVersion.version_number.desc()).all()
    return jsonify([v.to_dict() for v in versions])


@admin_bp.route('/plans/<int:plan_id>/versions', methods=['POST'])
@require_plan_access
def save_version(plan_id):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    _assert_owner(plan)
    from models.program_version import ProgramVersion
    from datetime import datetime, timezone
    data = request.get_json(silent=True) or {}
    latest = ProgramVersion.query.filter_by(program_id=plan_id).order_by(ProgramVersion.version_number.desc()).first()
    next_num = (latest.version_number + 1) if latest else 1
    v = ProgramVersion(
        program_id=plan_id,
        version_number=next_num,
        snapshot_json=_snapshot_plan(plan),
        change_summary=data.get('change_summary') or None,
        created_by=session.get('user_id'),
        created_at=datetime.now(timezone.utc),
    )
    plan.current_version = next_num
    db.session.add(v)
    db.session.commit()
    return jsonify(v.to_dict()), 201


@admin_bp.route('/plans/<int:plan_id>/versions/<int:version_num>', methods=['GET'])
@require_plan_access
def get_version(plan_id, version_num):
    plan = db.session.get(NutritionPlan, plan_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    _assert_owner(plan)
    from models.program_version import ProgramVersion
    v = ProgramVersion.query.filter_by(program_id=plan_id, version_number=version_num).first()
    if v is None:
        return jsonify({'error': 'Version not found'}), 404
    d = v.to_dict()
    d['snapshot_json'] = v.snapshot_json
    return jsonify(d)


# -- Image upload (stub) -----------------------------------------------------

@admin_bp.route('/plans/upload-image', methods=['POST'])
@require_plan_access
def upload_image():
    from models.program_image_upload import ProgramImageUpload
    from datetime import datetime, timezone
    import os
    if 'file' not in request.files:
        return jsonify({'error': 'file is required'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'No file selected'}), 400
    upload_dir = os.path.join(current_app.instance_path, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    now = datetime.now(timezone.utc)
    safe_name = f'{int(now.timestamp())}_{f.filename}'
    file_path = os.path.join(upload_dir, safe_name)
    f.save(file_path)
    upload = ProgramImageUpload(
        uploaded_by=session.get('user_id'),
        file_path=file_path,
        original_filename=f.filename,
        mime_type=f.content_type or 'application/octet-stream',
        extraction_status='pending',
        created_at=now,
        updated_at=now,
    )
    db.session.add(upload)
    db.session.commit()
    return jsonify(upload.to_dict()), 201


@admin_bp.route('/plans/confirm-extraction/<int:upload_id>', methods=['POST'])
@require_plan_access
def confirm_extraction(upload_id):
    from models.program_image_upload import ProgramImageUpload
    from datetime import datetime, timezone
    upload = db.session.get(ProgramImageUpload, upload_id)
    if upload is None:
        return jsonify({'error': 'Upload not found'}), 404
    if upload.extraction_status not in ('draft_ready',):
        return jsonify({'error': 'Nothing to confirm — run extraction first'}), 400
    upload.extraction_status = 'confirmed'
    upload.updated_at = datetime.now(timezone.utc)
    if upload.program_id:
        plan = db.session.get(NutritionPlan, upload.program_id)
        if plan:
            plan.status = 'active'
    db.session.commit()
    return jsonify(upload.to_dict())


# -- Image extraction pipeline -----------------------------------------------

@admin_bp.route('/plans/process-image/<int:upload_id>', methods=['POST'])
@require_plan_access
def process_image(upload_id):
    """Trigger async Claude Vision extraction for a previously uploaded image."""
    from models.program_image_upload import ProgramImageUpload
    from datetime import datetime, timezone
    import threading, json as _json

    upload = db.session.get(ProgramImageUpload, upload_id)
    if upload is None:
        return jsonify({'error': 'Upload not found'}), 404
    if upload.extraction_status == 'processing':
        return jsonify({'message': 'Already processing', 'upload': upload.to_dict()}), 202
    if upload.extraction_status == 'draft_ready':
        result = {}
        if upload.extracted_json:
            try:
                result = _json.loads(upload.extracted_json)
            except Exception:
                pass
        return jsonify({'message': 'Already extracted', 'upload': upload.to_dict(), 'extracted': result})

    upload.extraction_status = 'processing'
    upload.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    # Run extraction in a background thread so the HTTP request returns quickly
    app = current_app._get_current_object()

    def _worker():
        import json as _j
        with app.app_context():
            from models import db as _db
            from models.program_image_upload import ProgramImageUpload as _PIU
            from datetime import datetime as _dt, timezone as _tz
            from utils.image_extractor import extract_diet_plan
            rec = _db.session.get(_PIU, upload_id)
            if rec is None:
                return
            try:
                result = extract_diet_plan(rec.file_path, rec.mime_type)
                rec.extracted_json = _j.dumps(result, ensure_ascii=False)
                rec.extraction_status = 'draft_ready'
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error('Extraction failed upload_id=%d: %s', upload_id, exc)
                rec.extraction_status = 'failed'
                rec.error_message = str(exc)
            rec.updated_at = _dt.now(_tz.utc)
            _db.session.commit()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    return jsonify({'message': 'Processing started', 'upload': upload.to_dict()}), 202


@admin_bp.route('/plans/upload-status/<int:upload_id>', methods=['GET'])
@require_plan_access
def upload_status(upload_id):
    """Poll extraction status. Returns extracted JSON when draft_ready."""
    import json as _json
    from models.program_image_upload import ProgramImageUpload
    upload = db.session.get(ProgramImageUpload, upload_id)
    if upload is None:
        return jsonify({'error': 'Upload not found'}), 404
    resp = upload.to_dict()
    if upload.extraction_status == 'draft_ready' and upload.extracted_json:
        try:
            resp['extracted'] = _json.loads(upload.extracted_json)
        except Exception:
            resp['extracted'] = None
    return jsonify(resp)


@admin_bp.route('/plans/apply-extraction/<int:upload_id>', methods=['POST'])
@require_plan_access
def apply_extraction(upload_id):
    """
    Apply a confirmed or draft_ready extraction to the plan:
    create ProgramDay → MealSlot → SlotItem rows from extracted_json.
    Existing days for the plan are cleared first if replace=true is passed.
    """
    import json as _json
    from models.program_image_upload import ProgramImageUpload
    from models.program_day import ProgramDay
    from models.meal_slot import MealSlot
    from models.slot_item import SlotItem
    from models.saved_food import SavedFood
    from datetime import datetime, timezone

    upload = db.session.get(ProgramImageUpload, upload_id)
    if upload is None:
        return jsonify({'error': 'Upload not found'}), 404
    if upload.extraction_status not in ('draft_ready', 'confirmed'):
        return jsonify({'error': 'Extraction not ready — process the image first'}), 400
    if not upload.extracted_json:
        return jsonify({'error': 'No extracted data found'}), 400
    if not upload.program_id:
        return jsonify({'error': 'Upload is not linked to a plan — set program_id first'}), 400

    data = request.get_json(silent=True) or {}
    replace = data.get('replace', True)

    try:
        extracted = _json.loads(upload.extracted_json)
    except Exception:
        return jsonify({'error': 'Extracted JSON is corrupt'}), 500

    plan = db.session.get(NutritionPlan, upload.program_id)
    if plan is None:
        return jsonify({'error': 'Plan not found'}), 404
    _assert_owner(plan)

    if replace:
        # Remove existing days (cascades to slots+items)
        ProgramDay.query.filter_by(program_id=plan.id).delete()
        db.session.flush()

    # Update plan metadata if extraction has it
    if extracted.get('plan_name') and not plan.name:
        plan.name = extracted['plan_name']
    if extracted.get('duration_days') and not plan.duration_days:
        plan.duration_days = extracted['duration_days']

    # Build food name → id map for fuzzy matching
    all_foods = SavedFood.query.with_entities(SavedFood.id, SavedFood.name, SavedFood.name_tr).all()
    food_lookup = {f.name.lower(): f.id for f in all_foods}
    food_lookup_tr = {(f.name_tr or '').lower(): f.id for f in all_foods if f.name_tr}

    def _match_food(name):
        """Return SavedFood.id or None using exact → fuzzy matching."""
        if not name:
            return None
        lower = name.lower()
        if lower in food_lookup:
            return food_lookup[lower]
        if lower in food_lookup_tr:
            return food_lookup_tr[lower]
        try:
            from rapidfuzz import process as rfp
            best = rfp.extractOne(lower, food_lookup.keys(), score_cutoff=80)
            if best:
                return food_lookup[best[0]]
            best_tr = rfp.extractOne(lower, food_lookup_tr.keys(), score_cutoff=80)
            if best_tr:
                return food_lookup_tr[best_tr[0]]
        except ImportError:
            pass
        return None

    now = datetime.now(timezone.utc)
    days_created = 0
    slots_created = 0
    items_created = 0
    unmatched_foods = []

    for i, day_data in enumerate(extracted.get('days', [])):
        day = ProgramDay(
            program_id=plan.id,
            day_offset=day_data.get('day_offset', i),
            label=day_data.get('label'),
            label_tr=day_data.get('label_tr'),
            notes=day_data.get('notes'),
            sort_order=i,
            created_at=now,
        )
        db.session.add(day)
        db.session.flush()
        days_created += 1

        for j, slot_data in enumerate(day_data.get('slots', [])):
            slot = MealSlot(
                day_id=day.id,
                slot_name=slot_data.get('slot_name', 'Slot'),
                slot_name_tr=slot_data.get('slot_name_tr'),
                sort_order=j,
                content_pattern=slot_data.get('content_pattern'),
                is_optional=bool(slot_data.get('is_optional', False)),
                created_at=now,
            )
            db.session.add(slot)
            db.session.flush()
            slots_created += 1

            for k, item_data in enumerate(slot_data.get('items', [])):
                fname = item_data.get('food_name') or ''
                food_id = _match_food(fname)
                if food_id is None and fname:
                    unmatched_foods.append(fname)
                item = SlotItem(
                    slot_id=slot.id,
                    saved_food_id=food_id,
                    food_name_override=fname if food_id is None else None,
                    quantity=item_data.get('quantity'),
                    unit=item_data.get('unit') or 'g',
                    notes=item_data.get('notes'),
                    notes_tr=item_data.get('notes_tr'),
                    sort_order=k,
                    is_fallback=False,
                )
                db.session.add(item)
                items_created += 1

    upload.extraction_status = 'confirmed'
    upload.updated_at = now
    db.session.commit()

    return jsonify({
        'message': 'Extraction applied',
        'days_created': days_created,
        'slots_created': slots_created,
        'items_created': items_created,
        'unmatched_foods': list(set(unmatched_foods)),
    })
