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


def _is_reserved_username(username):
    # '__system__' owns seeded templates and has a well-known seed password.
    return username.startswith('__')


def is_superadmin(user):
    """True for site owners listed in SUPERADMIN_USERNAMES (or anyone when auth is off)."""
    if not current_app.config.get('AUTH_ENABLED'):
        return True
    if user is None or _is_reserved_username(user.username):
        return False
    names = current_app.config.get('SUPERADMIN_USERNAMES') or ()
    if isinstance(names, str):
        names = {n.strip() for n in names.split(',') if n.strip()}
    return user.username in names


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
    user = None if _is_reserved_username(username) else User.query.filter_by(username=username).first()
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
    # Email-shaped usernames are reserved for Google sign-in linking (prevents account pre-hijacking).
    if '@' in username:
        return render_template('register.html', error='Username cannot contain "@".')
    if len(password) < 6:
        return render_template('register.html', error='Password must be at least 6 characters.')
    if password != confirm:
        return render_template('register.html', error='Passwords do not match.')
    if _is_reserved_username(username) or User.query.filter_by(username=username).first():
        return render_template('register.html', error='Username already taken.')
    role = data.get('role', 'member')
    user = User(username=username)
    user.set_pw(password)
    if role == 'dietitian':
        # is_admin == dietitian role: scoped to consenting clients, never global access.
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


def delete_user_data(uid):
    """Permanently remove a user and everything linked to them. Caller commits."""
    import os
    from models.food_entry import FoodEntry
    from models.daily_target import DailyTarget
    from models.daily_note import DailyNote
    from models.water_log import WaterLog
    from models.meal_template import MealTemplate
    from models.recipe import Recipe
    from models.friend_connection import FriendConnection
    from models.feed_visibility import FeedVisibility
    from models.feed_reaction import FeedReaction
    from models.user_badge import UserBadge
    from models.shared_entry import SharedEntry
    from models.plan_task_completion import PlanTaskCompletion
    from models.user_plan_assignment import UserPlanAssignment
    from models.nutrition_plan import NutritionPlan
    from models.program_version import ProgramVersion
    from models.program_image_upload import ProgramImageUpload
    from models.slot_fulfillment import SlotFulfillment
    from models.dietitian_access import DietitianAccess
    from models.dietitian_visit import DietitianVisit
    from models.food_exchange_category import FoodExchangeCategory
    from models.weekly_category_quota import WeeklyCategoryQuota
    from models.weight_log import WeightLog, BodyGoal

    or_ = db.or_
    SharedEntry.query.filter(or_(SharedEntry.shared_by_id == uid, SharedEntry.shared_to_id == uid)).delete(synchronize_session=False)
    SlotFulfillment.query.filter_by(user_id=uid).delete(synchronize_session=False)
    FeedReaction.query.filter(or_(FeedReaction.reactor_id == uid, FeedReaction.target_user_id == uid)).delete(synchronize_session=False)
    FriendConnection.query.filter(or_(FriendConnection.requester_id == uid, FriendConnection.recipient_id == uid)).delete(synchronize_session=False)
    DietitianAccess.query.filter(or_(DietitianAccess.dietitian_id == uid, DietitianAccess.client_id == uid)).delete(synchronize_session=False)
    DietitianVisit.query.filter(or_(DietitianVisit.dietitian_id == uid, DietitianVisit.client_id == uid)).delete(synchronize_session=False)
    for model in (FeedVisibility, UserBadge, PlanTaskCompletion, UserPlanAssignment,
                  WaterLog, DailyNote, DailyTarget, FoodEntry, WeightLog, BodyGoal):
        model.query.filter_by(user_id=uid).delete(synchronize_session=False)

    # ORM deletes so child rows cascade (template items, recipe ingredients, category members).
    for tpl in MealTemplate.query.filter_by(user_id=uid).all():
        db.session.delete(tpl)
    recipe_ids = [r.id for r in Recipe.query.filter_by(owner_id=uid).all()]
    if recipe_ids:
        SlotFulfillment.query.filter(SlotFulfillment.recipe_id.in_(recipe_ids)).update({'recipe_id': None}, synchronize_session=False)
        for r in Recipe.query.filter(Recipe.id.in_(recipe_ids)).all():
            db.session.delete(r)
    cat_ids = [c.id for c in FoodExchangeCategory.query.filter_by(owner_id=uid).all()]
    if cat_ids:
        WeeklyCategoryQuota.query.filter(WeeklyCategoryQuota.exchange_category_id.in_(cat_ids)).delete(synchronize_session=False)
        SlotFulfillment.query.filter(SlotFulfillment.exchange_category_id.in_(cat_ids)).update({'exchange_category_id': None}, synchronize_session=False)
        for c in FoodExchangeCategory.query.filter(FoodExchangeCategory.id.in_(cat_ids)).all():
            db.session.delete(c)

    # Plans authored by a dietitian stay available to their clients, just unattributed.
    NutritionPlan.query.filter_by(created_by=uid).update({'created_by': None}, synchronize_session=False)
    ProgramVersion.query.filter_by(created_by=uid).update({'created_by': None}, synchronize_session=False)
    UserPlanAssignment.query.filter_by(assigned_by=uid).update({'assigned_by': None}, synchronize_session=False)

    upload_root = os.path.realpath(os.path.join(current_app.instance_path, 'uploads'))
    for up in ProgramImageUpload.query.filter_by(uploaded_by=uid).all():
        path = os.path.realpath(up.file_path or '')
        if path.startswith(upload_root + os.sep) and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass
        db.session.delete(up)

    user = db.session.get(User, uid)
    if user is not None:
        db.session.delete(user)


@auth_bp.route('/delete-account', methods=['GET', 'POST'])
def delete_account():
    auth_on = bool(current_app.config.get('AUTH_ENABLED'))
    uid = session.get('user_id') if auth_on else None
    user = db.session.get(User, uid) if uid else None
    if request.method == 'GET' or user is None:
        if user is not None:
            session['delete_token'] = secrets.token_urlsafe(32)
        return render_template('delete_account.html', auth_on=auth_on, user=user,
                               token=session.get('delete_token'))

    token = request.form.get('token', '')
    expected = session.pop('delete_token', None)
    if not expected or not secrets.compare_digest(token, expected):
        return render_template('delete_account.html', auth_on=auth_on, user=user,
                               error='Your session expired. Please try again.'), 400
    if request.form.get('confirm', '').strip().upper() != 'DELETE':
        session['delete_token'] = secrets.token_urlsafe(32)
        return render_template('delete_account.html', auth_on=auth_on, user=user,
                               token=session['delete_token'],
                               error='Type DELETE to confirm.'), 400

    delete_user_data(user.id)
    db.session.commit()
    session.clear()
    return render_template('delete_account.html', auth_on=auth_on, user=None, deleted=True)


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
        user = User.query.filter_by(username=email).first() if email and userinfo.get('email_verified') else None
        if user is None:
            base = (email.split('@')[0] if email else 'user').lower()
            base = ''.join(c for c in base if c.isalnum() or c == '_')[:30].lstrip('_') or 'user'
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