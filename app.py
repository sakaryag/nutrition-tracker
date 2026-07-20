import os
import shutil
from datetime import datetime
from flask import Flask
from flask_migrate import Migrate
from sqlalchemy import event, text
from models import db
from config import config


def create_app(config_name=None, test_config=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config.get(config_name, config['default']))
    if test_config is not None:
        app.config.from_object(test_config)

    db.init_app(app)
    Migrate(app, db)

    os.makedirs(app.instance_path, exist_ok=True)

    _register_blueprints(app)
    _register_cli(app)

    with app.app_context():
        db.create_all()
        _migrate_add_columns(app)
        _auto_seed(app)

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
    """Add columns to saved_food that may not exist on older DBs (SQLite ignores
    new columns in create_all on existing tables). Each ALTER is wrapped separately
    so one failure doesn't block the others."""
    migrations = [
        'ALTER TABLE saved_food ADD COLUMN food_type VARCHAR(20) NOT NULL DEFAULT "ingredient"',
        'ALTER TABLE saved_food ADD COLUMN name_tr VARCHAR(300)',
        'ALTER TABLE saved_food ADD COLUMN g_per_unit FLOAT',
        'ALTER TABLE saved_food ADD COLUMN valid_units VARCHAR(500)',
        'ALTER TABLE food_entry ADD COLUMN template_id INTEGER',
        'ALTER TABLE food_entry ADD COLUMN user_id INTEGER REFERENCES user(id)',
        'ALTER TABLE daily_target ADD COLUMN user_id INTEGER REFERENCES user(id)',
        'ALTER TABLE meal_template ADD COLUMN user_id INTEGER REFERENCES user(id)',
    ]
    with db.engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # column already exists


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
        app.register_blueprint(auth_bp)
        app.register_blueprint(entries_bp)
        app.register_blueprint(summary_bp)
        app.register_blueprint(targets_bp)
        app.register_blueprint(foods_bp)
        app.register_blueprint(export_bp)
        app.register_blueprint(meal_templates_bp)
        app.register_blueprint(chat_bp)
        app.register_blueprint(pages_bp)
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
    if SavedFood.query.first() is None:
        try:
            from seed_data.seed import seed_db
            seed_db()
            app.logger.info('Database seeded with initial food data.')
        except ImportError:
            pass



if __name__ == '__main__':
    application = create_app()
    application.run(debug=True, port=5000)