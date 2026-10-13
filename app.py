"""ERPilot AI local development entry point placeholder.

Application routes, persistence, inference, and templates are implemented in
later stages.
"""

from flask import Flask

from config import DevelopmentConfig


app = Flask(__name__)
app.config.from_object(DevelopmentConfig)


if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
