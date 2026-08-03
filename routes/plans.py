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