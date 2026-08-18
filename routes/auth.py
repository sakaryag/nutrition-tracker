import secrets
from datetime import timedelta
from functools import wraps
from flask import Blueprint, request, redirect, url_for, render_template, session, jsonify, current_app
from models import db
from models.user import User
from oauth_client import oauth

auth_bp = Blueprint('auth', __name__)


def current_user_id():
    """Return the logged-in user's id, or None when auth is disabled."""
    return session.get('user_id')


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


def premium_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_app.config.get('AUTH_ENABLED'):
            return f(*args, **kwargs)
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        from models.user import User
        user = User.query.get(user_id)
        if not user or not user.plan_feature_enabled:
            return jsonify({'error': 'Premium subscription required', 'upgrade_url': '/upgrade'}), 402
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if not current_app.config.get('AUTH_ENABLED'):
        return redirect(url_for('pages.dashboard'))
    if request.method == 'GET':
        google_enabled = bool(current_app.config.get('GOOGLE_CLIENT_ID'))
        return render_template('login.html', google_oauth_enabled=google_enabled)
    data = request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return render_template('login.html', error='Username and password are required.')
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_pw(password):
        return render_template('login.html', error='Invalid username or password.')
    session.permanent = True
    session['user_id'] = user.id
    session['username'] = user.username
    return redirect(url_for('pages.dashboard'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if not current_app.config.get('AUTH_ENABLED'):
        return redirect(url_for('pages.dashboard'))
    if request.method == 'GET':
        google_enabled = bool(current_app.config.get('GOOGLE_CLIENT_ID'))
        return render_template('register.html', google_oauth_enabled=google_enabled)
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
    role = data.get('role', 'member')
    user = User(username=username)
    user.set_pw(password)
    if role == 'dietitian':
        user.is_admin = True
        user.plan_feature_enabled = True
    db.session.add(user)
    db.session.commit()
    session.permanent = True
    session['user_id'] = user.id
    session['username'] = user.username
    return redirect(url_for('pages.dashboard'))


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/auth/google')
def google_login():
    if not current_app.config.get('AUTH_ENABLED'):
        return redirect(url_for('pages.dashboard'))
    if oauth is None:
        return render_template('login.html', error='Google sign-in is not available.', google_oauth_enabled=False)
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/auth/google/callback')
def google_callback():
    if not current_app.config.get('AUTH_ENABLED'):
        return redirect(url_for('pages.dashboard'))
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        return render_template('login.html', error='Google sign-in was cancelled or failed.', google_oauth_enabled=True)

    userinfo = token.get('userinfo') or {}
    google_id = userinfo.get('sub', '')
    email = userinfo.get('email', '')
    picture = userinfo.get('picture', '')

    if not google_id:
        return render_template('login.html', error='Could not retrieve Google account info.', google_oauth_enabled=True)

    user = User.query.filter_by(google_id=google_id).first()
    if user is None:
        user = User.query.filter_by(username=email).first() if email else None
        if user is None:
            base = (email.split('@')[0] if email else 'user').lower()
            base = ''.join(c for c in base if c.isalnum() or c == '_')[:30] or 'user'
            username = base
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f'{base}{counter}'
                counter += 1
            user = User(username=username, google_id=google_id, avatar_url=picture or None)
            user.set_pw(secrets.token_hex(32))
            db.session.add(user)
        else:
            user.google_id = google_id
            if picture:
                user.avatar_url = picture
    else:
        if picture and not user.avatar_url:
            user.avatar_url = picture

    db.session.commit()
    session.permanent = True
    session['user_id'] = user.id
    session['username'] = user.username
    return redirect(url_for('pages.dashboard'))