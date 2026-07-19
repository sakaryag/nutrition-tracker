from flask import Blueprint, render_template
from routes.auth import login_required

pages_bp = Blueprint('pages', __name__)


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