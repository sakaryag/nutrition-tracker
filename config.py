import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / '.env')


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-replace-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///nutritrack.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTH_ENABLED = os.getenv('AUTH_ENABLED', 'true').lower() == 'true'
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
