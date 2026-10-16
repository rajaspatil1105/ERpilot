"""ERPilot AI Flask application entry point."""

from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, url_for
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
SUPPORTED_FRONTEND_CATEGORIES = {"brain_trauma", "chest_trauma"}


def create_app(test_config=None):
    """Create a configured Flask application without creating database state."""

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(DevelopmentConfig)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    app.register_blueprint(triage_bp)

    @app.get("/")
    def home():
        return redirect(url_for("register_page"))

    @app.get("/register")
    def register_page():
        return render_template(
            "register_patient.html",
            educational_disclaimer=app.config["EDUCATIONAL_DISCLAIMER"],
        )

    @app.get("/assessment")
    def assessment_page():
        return render_template(
            "assessment.html",
            educational_disclaimer=app.config["EDUCATIONAL_DISCLAIMER"],
            symptoms=_load_frontend_symptoms(),
            categories=sorted(ALLOWED_CATEGORIES),
            supported_categories=SUPPORTED_FRONTEND_CATEGORIES,
        )

    @app.get("/results")
    def results_page():
        return render_template(
            "results.html",
            educational_disclaimer=app.config["EDUCATIONAL_DISCLAIMER"],
            symptoms=_load_frontend_symptoms(),
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


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
