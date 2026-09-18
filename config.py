import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # In production, set SECRET_KEY as an environment variable instead.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-this")

    # Defaults to a local SQLite file for development.
    # Swap DATABASE_URL to a Postgres URI later, e.g.:
    #   postgresql://user:password@localhost:5432/life_tracker
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'life_tracker.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads for medical reports
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "medical_reports")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {"pdf"}
