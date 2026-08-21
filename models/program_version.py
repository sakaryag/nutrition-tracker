from datetime import datetime, timezone
from models import db


class ProgramVersion(db.Model):
    __tablename__ = 'program_version'

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey('nutrition_plan.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    version_number = db.Column(db.Integer, nullable=False)
    snapshot_json = db.Column(db.Text, nullable=False)
    change_summary = db.Column(db.String(500), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('program_id', 'version_number', name='uq_program_version'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'program_id': self.program_id,
            'version_number': self.version_number,
            'change_summary': self.change_summary,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            # snapshot_json omitted by default — large payload
        }
