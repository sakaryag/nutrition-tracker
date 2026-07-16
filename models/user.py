from models import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    pw_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_pw(self, plaintext):
        self.pw_hash = generate_password_hash(plaintext)

    def check_pw(self, plaintext):
        return check_password_hash(self.pw_hash, plaintext)
