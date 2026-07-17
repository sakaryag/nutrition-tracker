import os
from flask import Flask
from flask_migrate import Migrate
from sqlalchemy import event, text
from models import db
from config import config


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config.get(config_name, config['default']))

    db.init_app(app)
    Migrate(app, db)

    os.makedirs(app.instance_path, exist_ok=True)

    _register_blueprints(app)
    _register_cli(app)

    with app.app_context():
        db.create_all()
        _migrate_add_food_type(app)
        _auto_seed(app)

    if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
        with app.app_context():
            @event.listens_for(db.engine, 'connect')
            def _set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute('PRAGMA journal_mode=WAL')
                cursor.close()

    return app


def _migrate_add_food_type(app):
    """Add food_type column to saved_food if it does not already exist (SQLite does not
    auto-add columns when create_all() is called on an existing table)."""
    try:
        with db.engine.connect() as conn:
            conn.execute(
                text('ALTER TABLE saved_food ADD COLUMN food_type VARCHAR(20) NOT NULL DEFAULT "ingredient"')
            )
            conn.commit()
    except Exception:
        # Column already exists — this is expected on all runs after the first.
        pass


def _register_blueprints(app):
    try:
        from routes.auth import auth_bp
        from routes.entries import entries_bp
        from routes.summary import summary_bp
        from routes.targets import targets_bp
        from routes.foods import foods_bp
        from routes.export import export_bp
        from routes.meal_templates import meal_templates_bp
        from routes.pages import pages_bp
        app.register_blueprint(auth_bp)
        app.register_blueprint(entries_bp)
        app.register_blueprint(summary_bp)
        app.register_blueprint(targets_bp)
        app.register_blueprint(foods_bp)
        app.register_blueprint(export_bp)
        app.register_blueprint(meal_templates_bp)
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

    # Auto-seed recipe catalog if empty
    try:
        from models.recipe_catalog import RecipeCatalog
        if RecipeCatalog.query.first() is None:
            app.logger.info('Recipe catalog empty — run seed_data/seed_meals_kaggle.py to populate.')
    except Exception:
        pass


if __name__ == '__main__':
    application = create_app()
    application.run(debug=True, port=5000)