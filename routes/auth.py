from functools import wraps
from flask import Blueprint, request, redirect, url_for, render_template, session, jsonify, current_app
from models import db
from models.user import User

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_app.config.get('AUTH_ENABLED'):
            return f(*args, **kwargs)
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if not current_app.config.get('AUTH_ENABLED'):
        return redirect(url_for('pages.dashboard'))
    if request.method == 'GET':
        return render_template('login.html')
    data = request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return render_template('login.html', error='Username and password are required.')
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_pw(password):
        return render_template('login.html', error='Invalid username or password.')
    session['user_id'] = user.id
    session['username'] = user.username
    return redirect(url_for('pages.dashboard'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if not current_app.config.get('AUTH_ENABLED'):
        return redirect(url_for('pages.dashboard'))
    if request.method == 'GET':
        return render_template('register.html')
    data = request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    confirm = data.get('confirm', '')
    if not username or not password:
        return render_template('register.html', error='All fields are required.')
    if len(password) < 6:
        return render_template('register.html', error='Password must be at least 6 characters.')
    if password != confirm:
        return render_template('register.html', error='Passwords do not match.')
    if User.query.filter_by(username=username).first():
        return render_template('register.html', error='Username already taken.')
    user = User(username=username)
    user.set_pw(password)
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    session['username'] = user.username
    return redirect(url_for('pages.dashboard'))


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))