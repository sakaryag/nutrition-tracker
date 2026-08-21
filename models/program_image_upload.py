from datetime import datetime, timezone
from models import db


class ProgramImageUpload(db.Model):
    __tablename__ = 'program_image_upload'

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey('nutrition_plan.id'), nullable=True
    )
    uploaded_by = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False
    )
    file_path = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(300), nullable=False)
    mime_type = db.Column(db.String(50), nullable=False)
    # Values: pending, processing, draft_ready, confirmed, failed
    extraction_status = db.Column(db.String(20), nullable=False, default='pending')
    extracted_json = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            'id': self.id,
            'program_id': self.program_id,
            'uploaded_by': self.uploaded_by,
            'original_filename': self.original_filename,
            'mime_type': self.mime_type,
            'extraction_status': self.extraction_status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
