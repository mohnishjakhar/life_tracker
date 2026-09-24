import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Load environment variables from .env if present
load_dotenv(os.path.join(BASE_DIR, ".env"))



class Config:
    # In production, set SECRET_KEY as an environment variable instead.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-this")

    # Defaults to a local SQLite file for development.
    # Always resolve sqlite relative paths to the absolute project BASE_DIR
    _raw_db_url = os.environ.get("DATABASE_URL")
    if not _raw_db_url or _raw_db_url.strip() in ("", "sqlite:///life_tracker.db"):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'life_tracker.db')}"
    elif _raw_db_url.startswith("sqlite:///") and not os.path.isabs(_raw_db_url[10:]):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, _raw_db_url[10:])}"
    else:
        SQLALCHEMY_DATABASE_URI = _raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads for medical reports
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "medical_reports")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {"pdf"}

    # Mail / SMTP Configuration
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ["true", "on", "1"]
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "false").lower() in ["true", "on", "1"]
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER",
        os.environ.get("MAIL_USERNAME", "noreply@lifetracker.com")
    )

    # OTP and Password Reset Expiry Settings (in minutes)
    OTP_EXPIRY_MINUTES = int(os.environ.get("OTP_EXPIRY_MINUTES", 10))
    RESET_PASSWORD_WINDOW_MINUTES = int(os.environ.get("RESET_PASSWORD_WINDOW_MINUTES", 5))

