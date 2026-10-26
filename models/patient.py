"""Patient persistence model."""

from __future__ import annotations

import re
import secrets
from datetime import datetime

from sqlalchemy.orm import validates

from .db import db


def _new_patient_code():
    """Return a five-digit identifier; the unique index prevents duplicates."""

    return str(secrets.randbelow(90000) + 10000)


class Patient(db.Model):
    """Registered patient details used by an assessment."""

    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    patient_code = db.Column(
        db.String(5), nullable=False, unique=True, default=_new_patient_code
    )
    name = db.Column(db.String(200), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(100), nullable=False)
    incident_type = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    assessments = db.relationship(
        "Assessment",
        back_populates="patient",
        cascade="all, delete-orphan",
    )

    @validates("name", "gender", "incident_type")
    def validate_required_text(self, key, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string")
        return value.strip()

    @validates("patient_code")
    def validate_patient_code(self, key, value):
        if not isinstance(value, str) or not re.fullmatch(r"\d{5}", value):
            raise ValueError("patient_code must be a five-digit string")
        return value

    @validates("age")
    def validate_age(self, key, value):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("age must be a non-negative integer")
        if value < 0:
            raise ValueError("age must be a non-negative integer")
        return value
