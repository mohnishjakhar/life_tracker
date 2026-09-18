from datetime import date, timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.models.finance import Transaction
from app.models.academic import Semester, Course, Assessment, StudyGoal
from app.models.habit import Habit, HabitLog
from app.models.health import (
    ExerciseTarget,
    ExerciseLog,
    BodyMeasurement,
    DietTarget,
    DietLog,
    DailyHealthLog,
    HealthIssue,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    today = date.today()

    # ── Finance Summary ────────────────────────────────────
    income_total = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter_by(user_id=current_user.id, type="income")
        .scalar()
    )
    expense_total = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter_by(user_id=current_user.id, type="expense")
        .scalar()
    )

    # Last 7 days of transactions for mini chart
    week_start = today - timedelta(days=6)
    recent_txns = (
        Transaction.query
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.date >= week_start
        )
        .order_by(Transaction.date.asc())
        .all()
    )
    finance_chart_labels = [(week_start + timedelta(days=i)).strftime("%b %d") for i in range(7)]
    finance_income_data  = [0.0] * 7
    finance_expense_data = [0.0] * 7
    for t in recent_txns:
        idx = (t.date - week_start).days
        if 0 <= idx < 7:
            if t.type == "income":
                finance_income_data[idx] += float(t.amount)
            else:
                finance_expense_data[idx] += float(t.amount)

    finance = {
        "income_total": float(income_total),
        "expense_total": float(expense_total),
        "balance": float(income_total) - float(expense_total),
        "chart_labels": finance_chart_labels,
        "income_data": finance_income_data,
        "expense_data": finance_expense_data,
    }

    # ── Academic Summary ────────────────────────────────────
    semesters = Semester.query.filter_by(user_id=current_user.id).all()
    courses   = Course.query.filter_by(user_id=current_user.id).all()

    # Compute per-semester GPA for chart
    sem_chart_labels = []
    sem_chart_gpas   = []
    for sem in semesters:
        if sem.gpa is not None:
            sem_chart_labels.append(sem.name)
            sem_chart_gpas.append(round(sem.gpa, 2))
        else:
            sem_courses = [c for c in sem.courses if c.grade_point is not None]
            if sem_courses:
                total_credits = sum(c.credits for c in sem_courses)
                if total_credits:
                    gpa = sum(c.grade_point * c.credits for c in sem_courses) / total_credits
                    sem_chart_labels.append(sem.name)
                    sem_chart_gpas.append(round(gpa, 2))

    # Upcoming assessments in next 14 days
    upcoming_tests = (
        Assessment.query
        .join(Course)
        .filter(
            Course.user_id == current_user.id,
            Assessment.date >= today,
            Assessment.date <= today + timedelta(days=14),
            Assessment.is_completed == False
        )
        .order_by(Assessment.date.asc())
        .limit(5)
        .all()
    )

    # Open study goals
    pending_goals = (
        StudyGoal.query
        .filter_by(user_id=current_user.id, is_completed=False)
        .order_by(StudyGoal.target_date.asc())
        .limit(5)
        .all()
    )

    academic = {
        "semester_count": len(semesters),
        "course_count": len(courses),
        "sem_chart_labels": sem_chart_labels,
        "sem_chart_gpas": sem_chart_gpas,
        "current_gpa": sem_chart_gpas[-1] if sem_chart_gpas else None,
        "upcoming_tests": upcoming_tests,
        "pending_goals": pending_goals,
    }

    # ── Habit Summary ────────────────────────────────────────
    active_habits = Habit.query.filter_by(user_id=current_user.id, is_active=True).all()

    # Today's completion status
    habits_done_today = 0
    habit_summary_rows = []
    for h in active_habits:
        today_log = HabitLog.query.filter_by(habit_id=h.id, date=today).first()
        if today_log:
            habits_done_today += 1

        # Last 7 days completion for mini sparkline
        week_logs = {
            log.date: log.value
            for log in HabitLog.query.filter(
                HabitLog.habit_id == h.id,
                HabitLog.date >= week_start,
                HabitLog.date <= today
            ).all()
        }
        week_done = [1 if (week_start + timedelta(days=i)) in week_logs else 0 for i in range(7)]

        habit_summary_rows.append({
            "habit": h,
            "done_today": bool(today_log),
            "week_done": week_done,
        })

    habits = {
        "total_active": len(active_habits),
        "done_today": habits_done_today,
        "rows": habit_summary_rows,
    }

    # ── Health Summary ────────────────────────────────────────
    ex_target = ExerciseTarget.query.filter_by(user_id=current_user.id).first()
    target_days = ex_target.target_days_per_week if ex_target else 4
    target_mins = ex_target.target_minutes_per_week if ex_target else 150

    curr_week_start = today - timedelta(days=today.weekday())
    curr_week_end = curr_week_start + timedelta(days=6)
    week_workouts = (
        ExerciseLog.query.filter(
            ExerciseLog.user_id == current_user.id,
            ExerciseLog.date >= curr_week_start,
            ExerciseLog.date <= curr_week_end,
        ).all()
    )
    workouts_done_days = len(set(w.date for w in week_workouts))
    workouts_total_mins = sum(w.duration_minutes for w in week_workouts)

    today_diet_logs = DietLog.query.filter_by(user_id=current_user.id, date=today).all()
    today_calories = sum(m.calories for m in today_diet_logs)
    d_target = DietTarget.query.filter_by(user_id=current_user.id).first()
    target_calories = d_target.target_calories if d_target else 2000
    target_water_ml = d_target.target_water_ml if d_target else 2500

    today_health_log = DailyHealthLog.query.filter_by(user_id=current_user.id, date=today).first()
    today_water_ml = today_health_log.water_ml if today_health_log else 0

    latest_vital = (
        BodyMeasurement.query.filter_by(user_id=current_user.id)
        .order_by(BodyMeasurement.date.desc(), BodyMeasurement.id.desc())
        .first()
    )

    active_issues = (
        HealthIssue.query.filter(
            HealthIssue.user_id == current_user.id,
            HealthIssue.status.in_(["Active", "Recovering"]),
        )
        .order_by(HealthIssue.start_date.desc())
        .all()
    )

    health = {
        "target_days": target_days,
        "workouts_done_days": workouts_done_days,
        "target_mins": target_mins,
        "workouts_total_mins": workouts_total_mins,
        "today_calories": today_calories,
        "target_calories": target_calories,
        "today_water_ml": today_water_ml,
        "target_water_ml": target_water_ml,
        "latest_vital": latest_vital,
        "active_issues": active_issues,
    }

    return render_template(
        "dashboard.html",
        finance=finance,
        academic=academic,
        habits=habits,
        health=health,
        today=today,
    )
