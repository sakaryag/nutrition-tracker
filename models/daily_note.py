from datetime import datetime
from models import db


class DailyNote(db.Model):
    __tablename__ = 'daily_note'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    note_date = db.Column(db.Date, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False, default='')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'note_date': self.note_date.isoformat(),
            'content': self.content,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
