import pytest
from app import create_app
from models import db as _db


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-secret'
    AUTH_ENABLED = False
    DEFAULT_PROTEIN_TARGET = 150
    DEFAULT_FAT_TARGET = 65
    DEFAULT_CARBS_TARGET = 250
    DEFAULT_CALORIES_TARGET = 2200


@pytest.fixture(scope='session')
def app():
    application = create_app(test_config=TestConfig)
    with application.app_context():
        _db.drop_all()
        _db.create_all()
    yield application


@pytest.fixture(autouse=True)
def db_session(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()