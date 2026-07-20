import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / '.env', override=True)


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-replace-in-production')
    _db_url = os.getenv('DATABASE_URL', 'sqlite:///nutritrack.db')
    # Railway (and Heroku) provide postgres:// but SQLAlchemy requires postgresql://
    if _db_url.startswith('postgres://'):
        _db_url = 'postgresql://' + _db_url[len('postgres://'):]
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,       # test connection before use — drops stale SSL connections gracefully
        'pool_recycle': 240,         # recycle every 4min — well under Railway's ~5min idle timeout
        'pool_size': 5,
        'max_overflow': 2,
        'connect_args': {'connect_timeout': 10},
    }
    AUTH_ENABLED = os.getenv('AUTH_ENABLED', 'true').lower() == 'true'
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    DEFAULT_PROTEIN_TARGET = float(os.getenv('DEFAULT_PROTEIN_TARGET', '150'))
    DEFAULT_FAT_TARGET = float(os.getenv('DEFAULT_FAT_TARGET', '65'))
    DEFAULT_CARBS_TARGET = float(os.getenv('DEFAULT_CARBS_TARGET', '250'))
    DEFAULT_CALORIES_TARGET = float(os.getenv('DEFAULT_CALORIES_TARGET', '2200'))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
