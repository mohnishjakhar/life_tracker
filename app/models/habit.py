from datetime import datetime, timezone
from app import db


class Habit(db.Model):
    __tablename__ = "habits"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    frequency_per_week = db.Column(db.Integer, nullable=False, default=7)
    measurement_type = db.Column(db.String(20), nullable=False, default="boolean")  # boolean, duration, count, custom
    measurement_unit = db.Column(db.String(50), nullable=False, default="completed")  # e.g., minutes, reps, glasses
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    logs = db.relationship("HabitLog", backref="habit", lazy=True, cascade="all, delete-orphan")

    def __init__(
        self,
        user_id: int,
        name: str,
        description: str | None = None,
        frequency_per_week: int = 7,
        measurement_type: str = "boolean",
        measurement_unit: str = "completed",
        is_active: bool = True,
        **kwargs,
    ):
        super().__init__(
            user_id=user_id,
            name=name,
            description=description,
            frequency_per_week=frequency_per_week,
            measurement_type=measurement_type,
            measurement_unit=measurement_unit,
            is_active=is_active,
            **kwargs,
        )

    def __repr__(self):
        return f"<Habit {self.name} (User {self.user_id})>"



class HabitLog(db.Model):
    __tablename__ = "habit_logs"

    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    value = db.Column(db.Float, nullable=False, default=1.0)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint("habit_id", "date", name="uq_habit_date"),)

    def __init__(self, habit_id: int, date, value: float = 1.0, notes: str | None = None, **kwargs):
        super().__init__(habit_id=habit_id, date=date, value=value, notes=notes, **kwargs)

    def __repr__(self):
        return f"<HabitLog Habit {self.habit_id} on {self.date}: {self.value}>"
