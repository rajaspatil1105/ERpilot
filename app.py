"""ERPilot AI Flask application entry point."""

from flask import Flask
from flask import jsonify
from werkzeug.exceptions import HTTPException

from config import DevelopmentConfig
from models.db import db
from routes.triage import triage_bp


def create_app(test_config=None):
    """Create a configured Flask application without creating database state."""

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(DevelopmentConfig)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    app.register_blueprint(triage_bp)

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


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
