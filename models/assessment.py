"""Assessment persistence model."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import validates

from .db import db


class Assessment(db.Model):
    """Inference result and submitted evidence linked to a patient."""

    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id"),
        nullable=False,
    )
    category = db.Column(db.String(100), nullable=False)
    evidence_json = db.Column(db.Text, nullable=False)
    vitals_json = db.Column(db.Text, nullable=False)
    inference_result_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    patient = db.relationship("Patient", back_populates="assessments")

    @validates("category")
    def validate_category(self, key, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("category must be a non-empty string")
        return value.strip()

    @validates("evidence_json", "vitals_json", "inference_result_json")
    def validate_json_text(self, key, value):
        if not isinstance(value, str):
            raise ValueError(f"{key} must contain serialized JSON")
        try:
            json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError(f"{key} must contain valid JSON") from error
        return value
