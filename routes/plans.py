from flask import Blueprint, jsonify, request, current_app, session
from datetime import date, timedelta
from models import db
from models.nutrition_plan import NutritionPlan
from models.plan_task import PlanTask
from models.user_plan_assignment import UserPlanAssignment
from models.plan_task_completion import PlanTaskCompletion
from routes.auth import current_user_id

plans_bp = Blueprint('plans', __name__, url_prefix='/api/plans')


@plans_bp.before_request
def check_auth():
    if current_app.config.get('AUTH_ENABLED') and 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401


def _effective_day_offsets(task, plan_duration):
    """Return all day_offsets this task applies to, expanding repeat_days."""
    import json
    if task.repeat_days:
        try:
            days = json.loads(task.repeat_days)
            if isinstance(days, list):
                return [int(d) for d in days if 0 <= int(d) < plan_duration]
        except (ValueError, TypeError):
            pass
    return [task.day_offset]


@plans_bp.route('/my-assignment', methods=['GET'])
def my_assignment():
    uid = current_user_id()
    assignment = UserPlanAssignment.query.filter_by(
        user_id=uid, is_active=True
    ).order_by(UserPlanAssignment.created_at.desc()).first()

    if assignment is None:
        return jsonify({'assignment': None})

    plan = assignment.plan
    today = date.today()
    start = assignment.start_date
    day_index = (today - start).days  # 0-based current day

    # Build tasks grouped by day_offset
    tasks_by_day = {}
    for t in plan.tasks:
        for off in _effective_day_offsets(t, plan.duration_days):
            tasks_by_day.setdefault(off, []).append(t.to_dict())

    # Fetch completions for the entire plan window
    end_date = start + timedelta(days=plan.duration_days - 1)
    completions = PlanTaskCompletion.query.filter(
        PlanTaskCompletion.user_id == uid,
        PlanTaskCompletion.plan_id == plan.id,
        PlanTaskCompletion.completed_date >= start,
        PlanTaskCompletion.completed_date <= end_date,
    ).all()
    completed_set = {(c.task_id, c.completed_date.isoformat()) for c in completions}

    return jsonify({
        'assignment': assignment.to_dict(),
        'plan': plan.to_dict(),
        'tasks_by_day': {str(k): v for k, v in tasks_by_day.items()},
        'completed': [c.to_dict() for c in completions],
        'completed_set': [{'task_id': c.task_id, 'date': c.completed_date.isoformat()} for c in completions],
        'today_day_index': day_index,
        'start_date': start.isoformat(),
    })


@plans_bp.route('/complete-task', methods=['POST'])
def complete_task():
    uid = current_user_id()
    data = request.get_json(silent=True) or {}
    task_id = data.get('task_id')
    raw_date = data.get('date')

    if not task_id or not raw_date:
        return jsonify({'error': 'task_id and date are required'}), 400

    try:
        target_date = date.fromisoformat(raw_date)
    except ValueError:
        return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400

    task = db.session.get(PlanTask, task_id)
    if task is None:
        return jsonify({'error': 'Task not found'}), 404

    # Verify user has this plan assigned
    assignment = UserPlanAssignment.query.filter_by(
        user_id=uid, plan_id=task.plan_id, is_active=True
    ).first()
    if assignment is None:
        return jsonify({'error': 'Plan not assigned to you'}), 403

    existing = PlanTaskCompletion.query.filter_by(
        user_id=uid, task_id=task_id, completed_date=target_date
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'status': 'uncompleted', 'task_id': task_id, 'date': raw_date})

    completion = PlanTaskCompletion(
        user_id=uid,
        plan_id=task.plan_id,
        task_id=task_id,
        completed_date=target_date,
        notes=data.get('notes'),
    )
    db.session.add(completion)
    db.session.commit()
    return jsonify({'status': 'completed', 'task_id': task_id, 'date': raw_date}), 201


@plans_bp.route('/progress', methods=['GET'])
def progress():
    uid = current_user_id()
    days = min(int(request.args.get('days', 7)), 90)

    assignment = UserPlanAssignment.query.filter_by(
        user_id=uid, is_active=True
    ).order_by(UserPlanAssignment.created_at.desc()).first()

    if assignment is None:
        return jsonify({'days': [], 'overall_pct': 0})

    plan = assignment.plan
    today = date.today()
    start = assignment.start_date

    result = []
    for i in range(days):
        day_date = today - timedelta(days=days - 1 - i)
        day_offset = (day_date - start).days
        if day_offset < 0 or day_offset >= plan.duration_days:
            result.append({'date': day_date.isoformat(), 'pct': None, 'day_offset': day_offset})
            continue

        tasks_for_day = []
        for t in plan.tasks:
            offsets = _effective_day_offsets(t, plan.duration_days)
            if day_offset in offsets:
                tasks_for_day.append(t.id)

        total = len(tasks_for_day)
        if total == 0:
            result.append({'date': day_date.isoformat(), 'pct': 100, 'day_offset': day_offset, 'total': 0, 'done': 0})
            continue

        done = PlanTaskCompletion.query.filter(
            PlanTaskCompletion.user_id == uid,
            PlanTaskCompletion.plan_id == plan.id,
            PlanTaskCompletion.task_id.in_(tasks_for_day),
            PlanTaskCompletion.completed_date == day_date,
        ).count()

        pct = round(done / total * 100)
        result.append({'date': day_date.isoformat(), 'pct': pct, 'day_offset': day_offset, 'total': total, 'done': done})

    valid = [r for r in result if r.get('pct') is not None]
    overall = round(sum(r['pct'] for r in valid) / len(valid)) if valid else 0
    return jsonify({'days': result, 'overall_pct': overall})

# -- Rich plan view with Day/Slot structure ----------------------------------

@plans_bp.route('/my-assignment/rich', methods=['GET'])
def my_assignment_rich():
    """Return the active plan with the ProgramDay -> MealSlot -> SlotItem structure.
    Falls back to legacy task view if no ProgramDays exist."""
    uid = current_user_id()
    assignment = UserPlanAssignment.query.filter_by(
        user_id=uid, is_active=True
    ).order_by(UserPlanAssignment.created_at.desc()).first()

    if assignment is None:
        return jsonify({'assignment': None})

    plan = assignment.plan
    today = date.today()
    start = assignment.start_date
    day_index = (today - start).days

    from models.program_day import ProgramDay
    days = ProgramDay.query.filter_by(program_id=plan.id).order_by(ProgramDay.sort_order).all()

    if not days:
        # Legacy fallback
        return my_assignment()

    # Fetch today's fulfillments
    from models.slot_fulfillment import SlotFulfillment
    today_fulfillments = SlotFulfillment.query.filter_by(
        user_id=uid, fulfillment_date=today
    ).all()
    fulfilled_slot_ids = {sf.slot_id for sf in today_fulfillments}

    days_data = []
    for day in days:
        day_dict = {
            'id': day.id,
            'day_offset': day.day_offset,
            'label': day.label,
            'label_tr': day.label_tr,
            'notes': day.notes,
            'is_today': day.day_offset == day_index,
            'slots': [],
        }
        for slot in day.slots:
            slot_dict = slot.to_dict()
            slot_dict['fulfilled_today'] = slot.id in fulfilled_slot_ids
            day_dict['slots'].append(slot_dict)
        days_data.append(day_dict)

    from models.program_guideline import ProgramGuideline
    guidelines = ProgramGuideline.query.filter_by(program_id=plan.id).order_by(ProgramGuideline.sort_order).all()

    return jsonify({
        'assignment': assignment.to_dict(),
        'plan': plan.to_dict(),
        'days': days_data,
        'today_day_index': day_index,
        'start_date': start.isoformat(),
        'guidelines': [g.to_dict() for g in guidelines],
        'today_fulfillments': [sf.to_dict() for sf in today_fulfillments],
    })


# -- Slot fulfillment --------------------------------------------------------

@plans_bp.route('/fulfill-slot', methods=['POST'])
def fulfill_slot():
    """Record that the patient consumed a slot. Creates or updates the fulfillment row.
    Optionally creates a FoodEntry so the food counts in daily nutrition totals."""
    uid = current_user_id()
    data = request.get_json(silent=True) or {}
    slot_id = data.get('slot_id')
    raw_date = data.get('date')

    if not slot_id or not raw_date:
        return jsonify({'error': 'slot_id and date are required'}), 400

    try:
        target_date = date.fromisoformat(raw_date)
    except ValueError:
        return jsonify({'error': 'Invalid date format, use YYYY-MM-DD'}), 400

    from models.meal_slot import MealSlot
    from models.slot_fulfillment import SlotFulfillment

    slot = db.session.get(MealSlot, slot_id)
    if slot is None:
        return jsonify({'error': 'Slot not found'}), 404

    existing = SlotFulfillment.query.filter_by(
        user_id=uid, slot_id=slot_id, fulfillment_date=target_date
    ).first()

    saved_food_id = data.get('saved_food_id')
    recipe_id = data.get('recipe_id')
    exchange_category_id = data.get('exchange_category_id')
    quantity = float(data['quantity']) if data.get('quantity') is not None else None
    unit = data.get('unit')

    if existing:
        # Toggle off if same food/recipe is re-submitted
        if (existing.saved_food_id == saved_food_id and
                existing.recipe_id == recipe_id and
                existing.exchange_category_id == exchange_category_id):
            db.session.delete(existing)
            db.session.commit()
            return jsonify({'status': 'unfulfilled', 'slot_id': slot_id, 'date': raw_date})
        existing.saved_food_id = saved_food_id
        existing.recipe_id = recipe_id
        existing.exchange_category_id = exchange_category_id
        existing.quantity = quantity
        existing.unit = unit
        db.session.commit()
        return jsonify({'status': 'updated', 'fulfillment': existing.to_dict()})

    from datetime import datetime, timezone
    sf = SlotFulfillment(
        user_id=uid,
        slot_id=slot_id,
        fulfillment_date=target_date,
        saved_food_id=saved_food_id,
        recipe_id=recipe_id,
        exchange_category_id=exchange_category_id,
        quantity=quantity,
        unit=unit,
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(sf)

    # Optionally auto-create a FoodEntry so it shows in the daily log
    if saved_food_id and quantity:
        from models.food_entry import FoodEntry
        from models.saved_food import SavedFood
        food = db.session.get(SavedFood, saved_food_id)
        if food:
            scale = quantity / 100.0
            entry = FoodEntry(
                user_id=uid,
                date=target_date,
                food_name=food.name,
                protein=round((food.protein or 0) * scale, 1),
                fat=round((food.fat or 0) * scale, 1),
                carbs=round((food.carbs or 0) * scale, 1),
                calories=round((food.calories or 0) * scale, 1),
                serving_size=quantity,
                serving_unit=unit or 'g',
                meal_type='plan',
            )
            db.session.add(entry)
            db.session.flush()
            sf.food_entry_id = entry.id

    db.session.commit()
    return jsonify({'status': 'fulfilled', 'fulfillment': sf.to_dict()}), 201


# -- Fulfillment status ------------------------------------------------------

@plans_bp.route('/fulfillment-status', methods=['GET'])
def fulfillment_status():
    """Per-slot fulfillment status for a given date."""
    uid = current_user_id()
    raw_date = request.args.get('date', date.today().isoformat())
    try:
        target_date = date.fromisoformat(raw_date)
    except ValueError:
        return jsonify({'error': 'Invalid date'}), 400

    assignment = UserPlanAssignment.query.filter_by(
        user_id=uid, is_active=True
    ).order_by(UserPlanAssignment.created_at.desc()).first()

    if assignment is None:
        return jsonify({'slots': [], 'date': raw_date})

    from models.program_day import ProgramDay
    from models.meal_slot import MealSlot
    from models.slot_fulfillment import SlotFulfillment

    day_index = (target_date - assignment.start_date).days
    day = ProgramDay.query.filter_by(
        program_id=assignment.plan_id, day_offset=day_index
    ).first()

    if day is None:
        return jsonify({'slots': [], 'date': raw_date, 'day_index': day_index})

    fulfillments = {
        sf.slot_id: sf.to_dict()
        for sf in SlotFulfillment.query.filter_by(user_id=uid, fulfillment_date=target_date).all()
    }

    slots = []
    for slot in day.slots:
        slots.append({
            **slot.to_dict(),
            'fulfillment': fulfillments.get(slot.id),
            'is_fulfilled': slot.id in fulfillments,
        })

    total = len(slots)
    done = sum(1 for s in slots if s['is_fulfilled'])
    return jsonify({
        'date': raw_date,
        'day_index': day_index,
        'slots': slots,
        'total': total,
        'done': done,
        'pct': round(done / total * 100) if total else 100,
    })


# -- Category progress -------------------------------------------------------

@plans_bp.route('/category-progress', methods=['GET'])
def category_progress():
    """Weekly category quota progress — how many portions consumed vs target."""
    uid = current_user_id()
    week_str = request.args.get('week')
    raw_date = request.args.get('date')

    assignment = UserPlanAssignment.query.filter_by(
        user_id=uid, is_active=True
    ).order_by(UserPlanAssignment.created_at.desc()).first()

    if assignment is None:
        return jsonify({'quotas': []})

    from models.weekly_category_quota import WeeklyCategoryQuota
    from models.slot_fulfillment import SlotFulfillment
    from models.food_exchange_category import FoodExchangeCategory
    from datetime import timedelta

    quotas = WeeklyCategoryQuota.query.filter_by(program_id=assignment.plan_id).all()

    if week_str:
        try:
            # Format: YYYY-WNN
            year, wn = week_str.split('-W')
            # ISO week: find Monday of that week
            import datetime as _dt
            jan4 = _dt.date(int(year), 1, 4)
            monday = jan4 - timedelta(days=jan4.isoweekday() - 1) + timedelta(weeks=int(wn) - 1)
            start_dt = monday
            end_dt = monday + timedelta(days=6)
        except Exception:
            return jsonify({'error': 'Invalid week format, use YYYY-WNN'}), 400
    elif raw_date:
        try:
            target_date = date.fromisoformat(raw_date)
            start_dt = end_dt = target_date
        except ValueError:
            return jsonify({'error': 'Invalid date'}), 400
    else:
        today = date.today()
        start_dt = end_dt = today

    fulfillments = SlotFulfillment.query.filter(
        SlotFulfillment.user_id == uid,
        SlotFulfillment.fulfillment_date >= start_dt,
        SlotFulfillment.fulfillment_date <= end_dt,
        SlotFulfillment.exchange_category_id != None,
    ).all()

    counts_by_cat = {}
    for sf in fulfillments:
        counts_by_cat[sf.exchange_category_id] = counts_by_cat.get(sf.exchange_category_id, 0) + 1

    result = []
    for q in quotas:
        cat = db.session.get(FoodExchangeCategory, q.exchange_category_id)
        consumed = counts_by_cat.get(q.exchange_category_id, 0)
        result.append({
            'quota_id': q.id,
            'category_id': q.exchange_category_id,
            'category_name': cat.name if cat else None,
            'category_name_tr': cat.name_tr if cat else None,
            'quota_per_week': q.quota_per_week,
            'consumed': consumed,
            'remaining': max(0, q.quota_per_week - consumed),
            'pct': round(min(consumed / q.quota_per_week * 100, 100)) if q.quota_per_week else 100,
        })

    return jsonify({'quotas': result, 'period': {'start': start_dt.isoformat(), 'end': end_dt.isoformat()}})
