"""Flask configuration for local educational development."""

import os


class DevelopmentConfig:
    """Configuration used by the local development entry point."""

    DEBUG = True
    SECRET_KEY = os.environ.get(
        "ERPILOT_SECRET_KEY",
        "development-only-insecure-key",
    )
    SQLALCHEMY_DATABASE_URI = "sqlite:///erpilot.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    EDUCATIONAL_DISCLAIMER = (
        "ERPilot AI is an educational prototype, not clinically validated, "
        "not intended for use on real patients, and not a substitute for "
        "qualified clinical judgment."
    )
