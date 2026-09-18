from datetime import datetime, timezone
from app import db

class Semester(db.Model):
    __tablename__ = "semesters"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)  # e.g., "Semester 1", "Fall 2026"
    gpa = db.Column(db.Float, nullable=True)  # Store GPA directly

    courses = db.relationship("Course", backref="semester", lazy=True, cascade="all, delete-orphan")

    def __init__(self, user_id: int, name: str, gpa: float | None = None, **kwargs):
        super().__init__(user_id=user_id, name=name, gpa=gpa, **kwargs)

    def __repr__(self):
        return f"<Semester {self.name}>"

class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, default=3)
    grade = db.Column(db.String(5), nullable=True)  # e.g., "A", "B+"
    grade_point = db.Column(db.Float, nullable=True)  # e.g., 4.0, 3.5
    marks_obtained = db.Column(db.Float, nullable=True)
    max_marks = db.Column(db.Float, default=100, nullable=True)

    assessments = db.relationship("Assessment", backref="course", lazy=True, cascade="all, delete-orphan")

    def __init__(self, user_id: int, name: str, semester_id: int | None = None, credits: int = 3, grade: str | None = None, grade_point: float | None = None, marks_obtained: float | None = None, max_marks: float = 100.0, **kwargs):
        super().__init__(user_id=user_id, name=name, semester_id=semester_id, credits=credits, grade=grade, grade_point=grade_point, marks_obtained=marks_obtained, max_marks=max_marks, **kwargs)

    def __repr__(self):
        return f"<Course {self.name}>"

class Assessment(db.Model):
    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Midterm 1"
    date = db.Column(db.Date, nullable=False)
    max_marks = db.Column(db.Float, nullable=True)
    marks_obtained = db.Column(db.Float, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)

    def __init__(self, course_id: int, name: str, date, max_marks: float | None = None, marks_obtained: float | None = None, is_completed: bool = False, **kwargs):
        super().__init__(course_id=course_id, name=name, date=date, max_marks=max_marks, marks_obtained=marks_obtained, is_completed=is_completed, **kwargs)

    def __repr__(self):
        return f"<Assessment {self.name}>"

class StudyGoal(db.Model):
    __tablename__ = "study_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    target_date = db.Column(db.Date, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)

    def __init__(self, user_id: int, title: str, target_date, is_completed: bool = False, **kwargs):
        super().__init__(user_id=user_id, title=title, target_date=target_date, is_completed=is_completed, **kwargs)

    def __repr__(self):
        return f"<StudyGoal {self.title}>"
