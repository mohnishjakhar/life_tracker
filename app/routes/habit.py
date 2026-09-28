from datetime import date, datetime, timedelta, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.habit import Habit, HabitLog

habit_bp = Blueprint("habit", __name__, url_prefix="/habit")


def get_start_of_week(dt=None):
    """Get the Monday of the current week for a given date."""
    if dt is None:
        dt = date.today()
    return dt - timedelta(days=dt.weekday())


def calculate_streaks(habit):
    """Calculate the current and longest streaks of active days for a habit."""
    # Unique sorted dates of logs
    logged_dates = sorted(list({log.date for log in habit.logs}))
    
    if not logged_dates:
        return 0, 0

    # Calculate streaks
    streaks = []
    current_run = 0
    prev_date = None
    
    for d in logged_dates:
        if prev_date is None:
            current_run = 1
        elif (d - prev_date).days == 1:
            current_run += 1
        elif (d - prev_date).days > 1:
            streaks.append(current_run)
            current_run = 1
        prev_date = d
    streaks.append(current_run)
    
    longest_streak = max(streaks) if streaks else 0

    # Calculate current streak
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # Current streak is only active if logged today or yesterday
    if logged_dates[-1] in (today, yesterday):
        curr_streak = 0
        check_date = logged_dates[-1]
        idx = len(logged_dates) - 1
        while idx >= 0:
            if logged_dates[idx] == check_date:
                curr_streak += 1
                check_date = check_date - timedelta(days=1)
                idx -= 1
            else:
                break
        current_streak = curr_streak
    else:
        current_streak = 0

    return current_streak, longest_streak


@habit_bp.route("/")
@login_required
def dashboard():
    today = date.today()
    start_of_week = get_start_of_week(today)
    end_of_week = start_of_week + timedelta(days=6)

    # Fetch active habits for current user
    active_habits = Habit.query.filter_by(user_id=current_user.id, is_active=True).all()
    archived_habits = Habit.query.filter_by(user_id=current_user.id, is_active=False).all()

    # Pre-calculate progress for each habit
    habit_data = []
    for habit in active_habits:
        # Check if logged today
        today_log = HabitLog.query.filter_by(habit_id=habit.id, date=today).first()
        
        # Calculate logs in current week
        week_logs_count = HabitLog.query.filter(
            HabitLog.habit_id == habit.id,
            HabitLog.date >= start_of_week,
            HabitLog.date <= end_of_week
        ).count()

        current_streak, _ = calculate_streaks(habit)

        habit_data.append({
            "habit": habit,
            "today_log": today_log,
            "week_logs_count": week_logs_count,
            "current_streak": current_streak
        })

    return render_template(
        "habit/dashboard.html",
        habit_data=habit_data,
        archived_habits=archived_habits,
        today=today
    )


@habit_bp.route("/add", methods=["POST"])
@login_required
def add_habit():
    name = request.form.get("name")
    description = request.form.get("description")
    frequency_per_week = request.form.get("frequency_per_week", type=int)
    measurement_type = request.form.get("measurement_type", "boolean")
    measurement_unit = request.form.get("measurement_unit", "completed")
    habit_type = request.form.get("habit_type", "positive")

    if habit_type not in ["positive", "negative"]:
        habit_type = "positive"

    if not name:
        flash("Habit name is required.", "danger")
        return redirect(url_for("habit.dashboard"))

    if frequency_per_week < 1 or frequency_per_week > 7:
        flash("Frequency must be between 1 and 7 days per week.", "danger")
        return redirect(url_for("habit.dashboard"))

    # For boolean type, force unit to "completed"
    if measurement_type == "boolean":
        measurement_unit = "completed"

    habit = Habit(
        user_id=current_user.id,
        name=name,
        description=description,
        frequency_per_week=frequency_per_week,
        measurement_type=measurement_type,
        measurement_unit=measurement_unit,
        habit_type=habit_type
    )

    db.session.add(habit)
    db.session.commit()
    flash(f"Habit '{name}' created successfully!", "success")
    return redirect(url_for("habit.dashboard"))


@habit_bp.route("/quick-log", methods=["POST"])
@login_required
def quick_log():
    habit_id = request.form.get("habit_id", type=int)
    value_str = request.form.get("value")
    
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    today = date.today()

    # Determine numeric value
    if habit.measurement_type == "boolean":
        # Toggle boolean log for today
        existing_log = HabitLog.query.filter_by(habit_id=habit.id, date=today).first()
        if existing_log:
            db.session.delete(existing_log)
            db.session.commit()
            return jsonify({"status": "deleted", "message": "Habit log removed for today."})
        else:
            new_log = HabitLog(habit_id=habit.id, date=today, value=1.0)
            db.session.add(new_log)
            db.session.commit()
            return jsonify({"status": "logged", "message": "Habit logged successfully for today."})
    else:
        # Numeric values (duration, count, custom)
        try:
            value = float(value_str) if value_str else 0.0
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid measurement value."}), 400

        existing_log = HabitLog.query.filter_by(habit_id=habit.id, date=today).first()
        if existing_log:
            existing_log.value = value
            existing_log.created_at = datetime.now(timezone.utc)
            db.session.commit()
            return jsonify({"status": "updated", "message": "Habit log updated for today."})
        else:
            new_log = HabitLog(habit_id=habit.id, date=today, value=value)
            db.session.add(new_log)
            db.session.commit()
            return jsonify({"status": "logged", "message": "Habit logged successfully for today."})


@habit_bp.route("/details/<int:habit_id>")
@login_required
def details(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()

    # Calculate streaks
    current_streak, longest_streak = calculate_streaks(habit)
    
    # Calculate general stats
    total_logs = len(habit.logs)
    avg_value = 0.0
    if total_logs > 0:
        avg_value = sum(log.value for log in habit.logs) / total_logs

    # Completion rate relative to when it was created
    days_since_creation = (date.today() - habit.created_at.date()).days + 1
    # Max active days possible based on weekly target
    target_ratio = habit.frequency_per_week / 7.0
    expected_logs = max(1, int(days_since_creation * target_ratio))
    completion_rate = min(100, int((total_logs / expected_logs) * 100))

    # Logs sorted by date descending for list view
    sorted_logs = sorted(habit.logs, key=lambda x: x.date, reverse=True)

    return render_template(
        "habit/details.html",
        habit=habit,
        current_streak=current_streak,
        longest_streak=longest_streak,
        total_logs=total_logs,
        avg_value=round(avg_value, 1),
        completion_rate=completion_rate,
        logs=sorted_logs
    )


@habit_bp.route("/log/add", methods=["POST"])
@login_required
def add_log():
    habit_id = request.form.get("habit_id", type=int)
    date_str = request.form.get("date")
    value_str = request.form.get("value")
    notes = request.form.get("notes")

    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    
    try:
        log_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        flash("Invalid date format. Use YYYY-MM-DD.", "danger")
        return redirect(url_for("habit.details", habit_id=habit.id))

    if log_date > date.today():
        flash("Cannot log habits in the future!", "danger")
        return redirect(url_for("habit.details", habit_id=habit.id))

    # Determine numeric value
    if habit.measurement_type == "boolean":
        value = 1.0
    else:
        try:
            value = float(value_str) if value_str else 0.0
        except ValueError:
            flash("Invalid measurement value.", "danger")
            return redirect(url_for("habit.details", habit_id=habit.id))

    # Upsert logic
    existing_log = HabitLog.query.filter_by(habit_id=habit.id, date=log_date).first()
    if existing_log:
        existing_log.value = value
        existing_log.notes = notes
        existing_log.created_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f"Log updated successfully for {log_date}.", "success")
    else:
        new_log = HabitLog(habit_id=habit.id, date=log_date, value=value, notes=notes)
        db.session.add(new_log)
        db.session.commit()
        flash(f"Logged progress for {log_date}.", "success")

    return redirect(url_for("habit.details", habit_id=habit.id))


@habit_bp.route("/log/delete/<int:log_id>", methods=["POST"])
@login_required
def delete_log(log_id):
    log = HabitLog.query.join(Habit).filter(
        HabitLog.id == log_id,
        Habit.user_id == current_user.id
    ).first_or_404()
    
    habit_id = log.habit_id
    db.session.delete(log)
    db.session.commit()
    
    flash("Log deleted successfully.", "success")
    return redirect(url_for("habit.details", habit_id=habit_id))


@habit_bp.route("/archive/<int:habit_id>", methods=["POST"])
@login_required
def archive_habit(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    habit.is_active = not habit.is_active
    db.session.commit()
    
    state = "archived" if not habit.is_active else "activated"
    flash(f"Habit '{habit.name}' has been {state}.", "success")
    return redirect(url_for("habit.dashboard"))


@habit_bp.route("/delete/<int:habit_id>", methods=["POST"])
@login_required
def delete_habit(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    name = habit.name
    db.session.delete(habit)
    db.session.commit()
    
    flash(f"Habit '{name}' and all its logs have been deleted.", "success")
    return redirect(url_for("habit.dashboard"))


@habit_bp.route("/api/stats/<int:habit_id>")
@login_required
def get_habit_stats(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()

    # 30-day graph data
    today = date.today()
    dates_list = [(today - timedelta(days=i)) for i in range(29, -1, -1)]
    dates_str_list = [d.strftime("%Y-%m-%d") for d in dates_list]

    # Fetch logs for the last 30 days (for chart)
    logs_30_days = HabitLog.query.filter(
        HabitLog.habit_id == habit.id,
        HabitLog.date >= dates_list[0],
        HabitLog.date <= dates_list[-1]
    ).all()

    logs_dict = {log.date.strftime("%Y-%m-%d"): log.value for log in logs_30_days}
    values_list = [logs_dict.get(d, 0.0) for d in dates_str_list]

    # BUG FIX: Return ALL historical logs with their actual values (not just dates)
    # so the heatmap can calculate correct intensity levels for each day.
    all_logs = {log.date.strftime("%Y-%m-%d"): log.value for log in habit.logs}

    return jsonify({
        "dates": dates_str_list,
        "values": values_list,
        "all_logged_dates": list(all_logs.keys()),
        "all_logged_values": all_logs,          # <-- full value map for heatmap intensity
        "measurement_type": habit.measurement_type,
        "measurement_unit": habit.measurement_unit,
        "habit_type": habit.habit_type
    })

