from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, current_app, session
from routes.auth import login_required
from models import db
from models.user import User

pages_bp = Blueprint('pages', __name__)


def _get_current_user():
    uid = session.get('user_id')
    if uid is None:
        return None
    return db.session.get(User, uid)


def require_plan_feature(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_app.config.get('AUTH_ENABLED'):
            user = _get_current_user()
            if user is None:
                return redirect(url_for('auth.login'))
            if not user.is_admin and not user.plan_feature_enabled:
                return redirect(url_for('pages.dashboard'))
        return f(*args, **kwargs)
    return decorated


def require_admin_page(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_app.config.get('AUTH_ENABLED'):
            user = _get_current_user()
            if user is None:
                return redirect(url_for('auth.login'))
            if not user.is_admin:
                return redirect(url_for('pages.dashboard'))
        return f(*args, **kwargs)
    return decorated


@pages_bp.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')


@pages_bp.route('/history')
@login_required
def history():
    return render_template('history.html')


@pages_bp.route('/foods')
@login_required
def foods():
    return render_template('foods.html')


@pages_bp.route('/meals')
@login_required
def meals():
    return render_template('meal_templates.html')


@pages_bp.route('/settings')
@login_required
def settings():
    return render_template('settings.html')


@pages_bp.route('/chat')
@login_required
def chat():
    return render_template('chat.html')


@pages_bp.route('/reports')
@login_required
def reports():
    return render_template('reports.html')


@pages_bp.route('/plans')
@login_required
@require_plan_feature
def plans():
    return render_template('plans.html')


@pages_bp.route('/admin')
@login_required
@require_admin_page
def admin():
    return render_template('admin.html')