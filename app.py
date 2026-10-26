"""ERPilot AI Flask application entry point."""

from pathlib import Path
import secrets

from flask import Flask, jsonify, redirect, render_template, url_for
from sqlalchemy import inspect, text
from werkzeug.exceptions import HTTPException

from config import DevelopmentConfig
from inference_engine.rule_validator import (
    ALLOWED_CATEGORIES,
    load_json_file,
    validate_symptoms,
)
from models.db import db
from routes.triage import triage_bp


PROJECT_ROOT = Path(__file__).resolve().parent
SYMPTOMS_PATH = PROJECT_ROOT / "knowledge_base" / "symptoms.json"
SUPPORTED_FRONTEND_CATEGORIES = set(ALLOWED_CATEGORIES)


def create_app(test_config=None):
    """Create a configured Flask application without creating database state."""

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(DevelopmentConfig)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    with app.app_context():
        inspector = inspect(db.engine)
        if inspector.has_table("assessments"):
            columns = {
                column["name"]
                for column in inspector.get_columns("assessments")
            }
            if "workflow_mode" not in columns:
                db.session.execute(
                    text(
                        "ALTER TABLE assessments ADD COLUMN workflow_mode "
                        "VARCHAR(32) NOT NULL DEFAULT 'known_category'"
                    )
                )
            if "selected_category" not in columns:
                db.session.execute(
                    text(
                        "ALTER TABLE assessments ADD COLUMN selected_category "
                        "VARCHAR(100)"
                    )
                )
            if "checklist_json" not in columns:
                db.session.execute(
                    text(
                        "ALTER TABLE assessments ADD COLUMN checklist_json "
                        "TEXT NOT NULL DEFAULT '[]'"
                    )
                )
            db.session.execute(
                text(
                    "UPDATE assessments SET selected_category = category "
                    "WHERE workflow_mode = 'known_category' "
                    "AND selected_category IS NULL"
                )
            )
            db.session.commit()
        inspector = inspect(db.engine)
        if inspector.has_table("patients"):
            columns = {
                column["name"] for column in inspector.get_columns("patients")
            }
            if "patient_code" not in columns:
                db.session.execute(
                    text("ALTER TABLE patients ADD COLUMN patient_code VARCHAR(5)")
                )
            existing_rows = db.session.execute(
                text("SELECT id, patient_code FROM patients ORDER BY id")
            ).all()
            used_codes: set[str] = set()
            for patient_id, patient_code in existing_rows:
                if (
                    not isinstance(patient_code, str)
                    or len(patient_code) != 5
                    or not patient_code.isdigit()
                    or patient_code in used_codes
                ):
                    patient_code = _generate_unique_patient_code(used_codes)
                    db.session.execute(
                        text("UPDATE patients SET patient_code = :code WHERE id = :id"),
                        {"code": patient_code, "id": patient_id},
                    )
                used_codes.add(patient_code)
            db.session.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "ux_patients_patient_code ON patients (patient_code)"
                )
            )
            db.session.commit()
    app.register_blueprint(triage_bp)

    @app.get("/")
    def home():
        return redirect(url_for("register_page"))

    @app.get("/register")
    def register_page():
        return render_template(
            "register_patient.html",
        )

    @app.get("/assessment")
    def assessment_page():
        return render_template(
            "assessment.html",
            symptoms=_load_frontend_symptoms(),
            categories=sorted(ALLOWED_CATEGORIES),
            supported_categories=SUPPORTED_FRONTEND_CATEGORIES,
        )

    @app.get("/results")
    def results_page():
        return render_template(
            "results.html",
            symptoms=_load_frontend_symptoms(),
        )

    @app.get("/records")
    def patient_records_page():
        return render_template(
            "patient_records.html",
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return (
            jsonify(
                error=error.description,
                status=error.code,
                disclaimer=app.config["EDUCATIONAL_DISCLAIMER"],
            ),
            error.code,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.error("Unhandled application error: %s", error)
        return (
            jsonify(
                error="Internal server error.",
                status=500,
                disclaimer=app.config["EDUCATIONAL_DISCLAIMER"],
            ),
            500,
        )

    return app


def _load_frontend_symptoms():
    """Return the validated canonical symptom definitions for page rendering."""

    data = load_json_file(SYMPTOMS_PATH)
    validate_symptoms(data, SYMPTOMS_PATH)
    return data["symptoms"]


def _generate_unique_patient_code(used_codes: set[str]) -> str:
    for _attempt in range(1000):
        code = str(secrets.randbelow(90000) + 10000)
        if code not in used_codes:
            return code
    raise RuntimeError("Unable to generate a unique five-digit patient code")


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
