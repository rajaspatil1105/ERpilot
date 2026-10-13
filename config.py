"""Minimal Flask configuration for local educational development."""

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
