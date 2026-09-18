from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships to the various trackers (added as you build each module)
    transactions = db.relationship(
        "Transaction", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    semesters = db.relationship(
        "Semester", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    courses = db.relationship(
        "Course", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    study_goals = db.relationship(
        "StudyGoal", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    habits = db.relationship(
        "Habit", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    exercise_target = db.relationship(
        "ExerciseTarget", backref="user", uselist=False, lazy=True, cascade="all, delete-orphan"
    )
    exercise_logs = db.relationship(
        "ExerciseLog", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    body_measurements = db.relationship(
        "BodyMeasurement", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    medical_reports = db.relationship(
        "MedicalReport", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    health_issues = db.relationship(
        "HealthIssue", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    diet_target = db.relationship(
        "DietTarget", backref="user", uselist=False, lazy=True, cascade="all, delete-orphan"
    )
    diet_logs = db.relationship(
        "DietLog", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    daily_health_logs = db.relationship(
        "DailyHealthLog", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def __init__(self, username: str, email: str, password_hash: str | None = None, **kwargs):
        super().__init__(username=username, email=email, password_hash=password_hash, **kwargs)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self):
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
