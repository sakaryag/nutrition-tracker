import os
import shutil
from datetime import datetime
from flask import Flask
from flask_migrate import Migrate
from sqlalchemy import event, text
from models import db
from config import config
from oauth_client import oauth


def create_app(config_name=None, test_config=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config.get(config_name, config['default']))
    if test_config is not None:
        app.config.from_object(test_config)

    # Pool settings are configured in config.py per DB type (postgresql vs sqlite).

    db.init_app(app)
    Migrate(app, db)

    if oauth is not None:
        oauth.init_app(app)
        oauth.register(
            name='google',
            client_id=app.config.get('GOOGLE_CLIENT_ID'),
            client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )

    os.makedirs(app.instance_path, exist_ok=True)

    _register_blueprints(app)
    _register_cli(app)

    @app.context_processor
    def inject_current_user():
        from flask import session as _session
        uid = _session.get('user_id')
        if uid is None:
            return {'current_user': None}
        try:
            from models.user import User as _User
            return {'current_user': db.session.get(_User, uid)}
        except Exception:
            return {'current_user': None}

    with app.app_context():
        _create_all_if_needed(app)
        _migrate_add_columns(app)
        _auto_seed(app)
        _patch_name_tr(app)

    if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
        _backup_db(app)
        with app.app_context():
            @event.listens_for(db.engine, 'connect')
            def _set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute('PRAGMA journal_mode=WAL')
                cursor.execute('PRAGMA synchronous=NORMAL')
                cursor.execute('PRAGMA wal_checkpoint(PASSIVE)')
                cursor.close()

    return app


def _create_all_if_needed(app):
    """Only create tables if the database is new (no tables exist yet).

    The SQLite DB is persisted across deploys (e.g. via a Railway volume), so
    calling db.create_all() unconditionally on every startup would raise
    'table X already exists' once the schema has already been created.
    Flask-Migrate (and _migrate_add_columns) handle subsequent schema changes.
    """
    try:
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
    except Exception:
        existing_tables = []

    if not existing_tables:
        try:
            db.create_all()
        except Exception:
            pass  # another worker already created the tables


def _backup_db(app):
    """Keep last 3 daily backups of the SQLite DB next to the original."""
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not uri.startswith('sqlite:///'):
        return
    db_path = uri.replace('sqlite:///', '')
    if not os.path.isabs(db_path):
        db_path = os.path.join(app.instance_path, os.path.basename(db_path))
    if not os.path.exists(db_path):
        return
    today = datetime.now().strftime('%Y-%m-%d')
    backup_path = db_path + f'.backup-{today}'
    if not os.path.exists(backup_path):
        try:
            shutil.copy2(db_path, backup_path)
            # Remove backups older than 3 days
            backup_dir = os.path.dirname(db_path)
            base = os.path.basename(db_path)
            backups = sorted([
                f for f in os.listdir(backup_dir)
                if f.startswith(base + '.backup-')
            ])
            for old in backups[:-3]:
                try:
                    os.remove(os.path.join(backup_dir, old))
                except OSError:
                    pass
        except OSError:
            pass


def _migrate_add_columns(app):
    """Add columns that may not exist on older DBs. Each ALTER runs in its own
    transaction so a failure (column already exists) doesn't abort the others.
    This is critical for PostgreSQL which aborts the whole transaction on error."""
    is_pg = 'postgresql' in app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if is_pg:
        # PostgreSQL: IF NOT EXISTS is a no-op -- no error, no log noise
        migrations = [
            "ALTER TABLE saved_food ADD COLUMN IF NOT EXISTS food_type VARCHAR(20) NOT NULL DEFAULT 'ingredient'",
            'ALTER TABLE saved_food ADD COLUMN IF NOT EXISTS name_tr VARCHAR(300)',
            'ALTER TABLE saved_food ADD COLUMN IF NOT EXISTS g_per_unit FLOAT',
            'ALTER TABLE saved_food ADD COLUMN IF NOT EXISTS valid_units VARCHAR(500)',
            'ALTER TABLE saved_food ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE',
            'ALTER TABLE food_entry ADD COLUMN IF NOT EXISTS template_id INTEGER',
            'ALTER TABLE food_entry ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES "user"(id)',
            'ALTER TABLE daily_target ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES "user"(id)',
            'ALTER TABLE meal_template ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES "user"(id)',
            'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE',
            'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS plan_feature_enabled BOOLEAN DEFAULT FALSE',
            'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS google_id VARCHAR(255)',
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_user_google_id ON "user" (google_id) WHERE google_id IS NOT NULL',
            'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500)',
            'ALTER TABLE daily_target ADD COLUMN IF NOT EXISTS water_goal_ml FLOAT',
            # daily_note table creation handled by create_all; ensure it exists via migration too
            '''CREATE TABLE IF NOT EXISTS daily_note (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                note_date DATE NOT NULL,
                content TEXT NOT NULL DEFAULT \'\',
                updated_at TIMESTAMP
            )''',
            'CREATE INDEX IF NOT EXISTS ix_daily_note_user_id ON daily_note (user_id)',
            'CREATE INDEX IF NOT EXISTS ix_daily_note_note_date ON daily_note (note_date)',
            '''CREATE TABLE IF NOT EXISTS water_log (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                log_date DATE NOT NULL,
                amount_ml FLOAT NOT NULL,
                logged_at TIMESTAMP
            )''',
            'CREATE INDEX IF NOT EXISTS ix_water_log_user_id ON water_log (user_id)',
            'CREATE INDEX IF NOT EXISTS ix_water_log_log_date ON water_log (log_date)',
            # --- Family Mode / Social tables ---
            '''CREATE TABLE IF NOT EXISTS friend_connection (
                id SERIAL PRIMARY KEY,
                requester_id INTEGER NOT NULL REFERENCES "user"(id),
                recipient_id INTEGER NOT NULL REFERENCES "user"(id),
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                CONSTRAINT uq_friend_connection UNIQUE (requester_id, recipient_id)
            )''',
            'CREATE INDEX IF NOT EXISTS ix_friend_connection_requester_id ON friend_connection (requester_id)',
            'CREATE INDEX IF NOT EXISTS ix_friend_connection_recipient_id ON friend_connection (recipient_id)',
            '''CREATE TABLE IF NOT EXISTS shared_entry (
                id SERIAL PRIMARY KEY,
                entry_id INTEGER REFERENCES food_entry(id) ON DELETE SET NULL,
                shared_by_id INTEGER NOT NULL REFERENCES "user"(id),
                shared_to_id INTEGER NOT NULL REFERENCES "user"(id),
                cloned_entry_id INTEGER REFERENCES food_entry(id),
                shared_at TIMESTAMP
            )''',
            'CREATE INDEX IF NOT EXISTS ix_shared_entry_entry_id ON shared_entry (entry_id)',
            'CREATE INDEX IF NOT EXISTS ix_shared_entry_shared_by_id ON shared_entry (shared_by_id)',
            'CREATE INDEX IF NOT EXISTS ix_shared_entry_shared_to_id ON shared_entry (shared_to_id)',
            '''CREATE TABLE IF NOT EXISTS feed_visibility (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id),
                show_in_feed BOOLEAN NOT NULL DEFAULT FALSE,
                show_calories BOOLEAN NOT NULL DEFAULT TRUE,
                show_macros BOOLEAN NOT NULL DEFAULT TRUE,
                updated_at TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS user_badge (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES "user"(id),
                badge_key VARCHAR(50) NOT NULL,
                earned_at TIMESTAMP,
                badge_meta TEXT,
                CONSTRAINT uq_user_badge UNIQUE (user_id, badge_key)
            )''',
            'CREATE INDEX IF NOT EXISTS ix_user_badge_user_id ON user_badge (user_id)',
            # --- Dietitian access & notifications ---
            '''CREATE TABLE IF NOT EXISTS dietitian_access (
                id SERIAL PRIMARY KEY,
                dietitian_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                client_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                allowed BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                CONSTRAINT uq_dietitian_access UNIQUE (dietitian_id, client_id)
            )''',
            'CREATE INDEX IF NOT EXISTS ix_dietitian_access_dietitian_id ON dietitian_access (dietitian_id)',
            'CREATE INDEX IF NOT EXISTS ix_dietitian_access_client_id ON dietitian_access (client_id)',
            '''CREATE TABLE IF NOT EXISTS dietitian_visit (
                id SERIAL PRIMARY KEY,
                dietitian_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                client_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                visited_at TIMESTAMP,
                seen BOOLEAN NOT NULL DEFAULT FALSE
            )''',
            'CREATE INDEX IF NOT EXISTS ix_dietitian_visit_client_id ON dietitian_visit (client_id)',
        ]
    else:
        # SQLite does not support IF NOT EXISTS on ALTER TABLE -- use try/except
        migrations = [
            "ALTER TABLE saved_food ADD COLUMN food_type VARCHAR(20) NOT NULL DEFAULT 'ingredient'",
            'ALTER TABLE saved_food ADD COLUMN name_tr VARCHAR(300)',
            'ALTER TABLE saved_food ADD COLUMN g_per_unit FLOAT',
            'ALTER TABLE saved_food ADD COLUMN valid_units VARCHAR(500)',
            'ALTER TABLE saved_food ADD COLUMN is_archived BOOLEAN DEFAULT 0',
            'ALTER TABLE food_entry ADD COLUMN template_id INTEGER',
            'ALTER TABLE food_entry ADD COLUMN user_id INTEGER REFERENCES "user"(id)',
            'ALTER TABLE daily_target ADD COLUMN user_id INTEGER REFERENCES "user"(id)',
            'ALTER TABLE meal_template ADD COLUMN user_id INTEGER REFERENCES "user"(id)',
            'ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN DEFAULT 0',
            'ALTER TABLE "user" ADD COLUMN plan_feature_enabled BOOLEAN DEFAULT 0',
            'ALTER TABLE "user" ADD COLUMN google_id VARCHAR(255)',
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_user_google_id ON "user" (google_id)',
            'ALTER TABLE "user" ADD COLUMN avatar_url VARCHAR(500)',
            'ALTER TABLE daily_target ADD COLUMN water_goal_ml FLOAT',
            # SQLite: create daily_note if it doesn't exist yet (idempotent)
            '''CREATE TABLE IF NOT EXISTS daily_note (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                note_date DATE NOT NULL,
                content TEXT NOT NULL DEFAULT \'\',
                updated_at DATETIME
            )''',
            'CREATE INDEX IF NOT EXISTS ix_daily_note_user_id ON daily_note (user_id)',
            'CREATE INDEX IF NOT EXISTS ix_daily_note_note_date ON daily_note (note_date)',
            '''CREATE TABLE IF NOT EXISTS water_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                log_date DATE NOT NULL,
                amount_ml FLOAT NOT NULL,
                logged_at DATETIME
            )''',
            'CREATE INDEX IF NOT EXISTS ix_water_log_user_id ON water_log (user_id)',
            'CREATE INDEX IF NOT EXISTS ix_water_log_log_date ON water_log (log_date)',
            # --- Family Mode / Social tables ---
            '''CREATE TABLE IF NOT EXISTS friend_connection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_id INTEGER NOT NULL REFERENCES "user"(id),
                recipient_id INTEGER NOT NULL REFERENCES "user"(id),
                status VARCHAR(20) NOT NULL DEFAULT "pending",
                created_at DATETIME,
                updated_at DATETIME,
                CONSTRAINT uq_friend_connection UNIQUE (requester_id, recipient_id)
            )''',
            'CREATE INDEX IF NOT EXISTS ix_friend_connection_requester_id ON friend_connection (requester_id)',
            'CREATE INDEX IF NOT EXISTS ix_friend_connection_recipient_id ON friend_connection (recipient_id)',
            '''CREATE TABLE IF NOT EXISTS shared_entry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER REFERENCES food_entry(id) ON DELETE SET NULL,
                shared_by_id INTEGER NOT NULL REFERENCES "user"(id),
                shared_to_id INTEGER NOT NULL REFERENCES "user"(id),
                cloned_entry_id INTEGER REFERENCES food_entry(id),
                shared_at DATETIME
            )''',
            'CREATE INDEX IF NOT EXISTS ix_shared_entry_entry_id ON shared_entry (entry_id)',
            'CREATE INDEX IF NOT EXISTS ix_shared_entry_shared_by_id ON shared_entry (shared_by_id)',
            'CREATE INDEX IF NOT EXISTS ix_shared_entry_shared_to_id ON shared_entry (shared_to_id)',
            '''CREATE TABLE IF NOT EXISTS feed_visibility (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id),
                show_in_feed INTEGER NOT NULL DEFAULT 0,
                show_calories INTEGER NOT NULL DEFAULT 1,
                show_macros INTEGER NOT NULL DEFAULT 1,
                updated_at DATETIME
            )''',
            '''CREATE TABLE IF NOT EXISTS user_badge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES "user"(id),
                badge_key VARCHAR(50) NOT NULL,
                earned_at DATETIME,
                badge_meta TEXT,
                CONSTRAINT uq_user_badge UNIQUE (user_id, badge_key)
            )''',
            'CREATE INDEX IF NOT EXISTS ix_user_badge_user_id ON user_badge (user_id)',
            # --- Dietitian access & notifications ---
            '''CREATE TABLE IF NOT EXISTS dietitian_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dietitian_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                client_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                allowed INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME,
                updated_at DATETIME,
                CONSTRAINT uq_dietitian_access UNIQUE (dietitian_id, client_id)
            )''',
            'CREATE INDEX IF NOT EXISTS ix_dietitian_access_dietitian_id ON dietitian_access (dietitian_id)',
            'CREATE INDEX IF NOT EXISTS ix_dietitian_access_client_id ON dietitian_access (client_id)',
            '''CREATE TABLE IF NOT EXISTS dietitian_visit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dietitian_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                client_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                visited_at DATETIME,
                seen INTEGER NOT NULL DEFAULT 0
            )''',
            'CREATE INDEX IF NOT EXISTS ix_dietitian_visit_client_id ON dietitian_visit (client_id)',
        ]
    for sql in migrations:
        with db.engine.connect() as conn:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()


def _register_blueprints(app):
    try:
        from routes.auth import auth_bp
        from routes.entries import entries_bp
        from routes.summary import summary_bp
        from routes.targets import targets_bp
        from routes.foods import foods_bp
        from routes.export import export_bp
        from routes.meal_templates import meal_templates_bp
        from routes.chat import chat_bp
        from routes.pages import pages_bp
        from routes.notes import notes_bp
        from routes.water import water_bp
        from routes.plans import plans_bp
        from routes.admin import admin_bp
        from routes.friends import friends_bp
        from routes.shared import shared_bp
        from routes.social import social_bp
        from routes.game import game_bp
        from routes.dietitian import dietitian_bp
        app.register_blueprint(auth_bp)
        app.register_blueprint(entries_bp)
        app.register_blueprint(summary_bp)
        app.register_blueprint(targets_bp)
        app.register_blueprint(foods_bp)
        app.register_blueprint(export_bp)
        app.register_blueprint(meal_templates_bp)
        app.register_blueprint(chat_bp)
        app.register_blueprint(pages_bp)
        app.register_blueprint(notes_bp)
        app.register_blueprint(water_bp)
        app.register_blueprint(plans_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(friends_bp)
        app.register_blueprint(shared_bp)
        app.register_blueprint(social_bp)
        app.register_blueprint(game_bp)
        app.register_blueprint(dietitian_bp)
    except ImportError:
        app.logger.warning('Some blueprints not yet available.')


def _register_cli(app):
    try:
        from seed_data.seed import seed_command
        app.cli.add_command(seed_command)
    except ImportError:
        pass


def _auto_seed(app):
    from models.saved_food import SavedFood
    if SavedFood.query.filter_by(source='usda').first() is None:
        try:
            from seed_data.seed import seed_db
            seed_db()
            app.logger.info('Database seeded with initial food data.')
        except ImportError:
            pass


def _patch_name_tr(app):
    """Back-fill name_tr for existing USDA foods that have NULL name_tr."""
    import csv as csv_mod
    from models.saved_food import SavedFood
    if not SavedFood.query.filter(SavedFood.source == 'usda', SavedFood.name_tr == None).first():
        return  # nothing to patch
    csv_path = os.path.join(os.path.dirname(__file__), 'seed_data', 'foods.csv')
    if not os.path.exists(csv_path):
        return
    with open(csv_path, newline='', encoding='utf-8') as f:
        rows = {r['usda_fdc_id']: r for r in csv_mod.DictReader(f)}
    updated = 0
    for food in SavedFood.query.filter_by(source='usda').all():
        row = rows.get(str(food.usda_fdc_id))
        if row and row.get('name_tr') and not food.name_tr:
            food.name_tr = row['name_tr']
            updated += 1
    if updated:
        db.session.commit()
        app.logger.info(f'Patched name_tr for {updated} USDA foods.')



if __name__ == '__main__':
    application = create_app()
    application.run(debug=True, port=5000)