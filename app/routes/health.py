import os
from datetime import date, datetime, timedelta, timezone
import uuid
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    send_file,
    current_app,
    abort,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models.health import (
    ExerciseTarget,
    ExerciseLog,
    BodyMeasurement,
    MedicalReport,
    HealthIssue,
    DietTarget,
    DietLog,
    DailyHealthLog,
)

health_bp = Blueprint("health", __name__, url_prefix="/health")


def allowed_pdf(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config.get(
        "ALLOWED_EXTENSIONS", {"pdf"}
    )


def get_or_create_exercise_target(user_id: int) -> ExerciseTarget:
    target = ExerciseTarget.query.filter_by(user_id=user_id).first()
    if not target:
        target = ExerciseTarget(
            user_id=user_id,
            target_days_per_week=4,
            target_minutes_per_week=150,
            target_calories_per_week=1500,
        )
        db.session.add(target)
        db.session.commit()
    return target


def get_or_create_diet_target(user_id: int) -> DietTarget:
    target = DietTarget.query.filter_by(user_id=user_id).first()
    if not target:
        target = DietTarget(
            user_id=user_id,
            target_calories=2000,
            target_protein_g=80.0,
            target_carbs_g=250.0,
            target_fats_g=65.0,
            target_fiber_g=30.0,
            target_water_ml=2500,
        )
        db.session.add(target)
        db.session.commit()
    return target


def get_or_create_daily_health(user_id: int, log_date: date) -> DailyHealthLog:
    daily = DailyHealthLog.query.filter_by(user_id=user_id, date=log_date).first()
    if not daily:
        daily = DailyHealthLog(user_id=user_id, date=log_date, water_ml=0, sleep_hours=7.0, sleep_quality="Good", energy_level=4)
        db.session.add(daily)
        db.session.commit()
    return daily


@health_bp.route("/")
@login_required
def dashboard():
    today = date.today()

    # Active tab from query parameter (exercise, diet, vitals, reports, issues)
    active_tab = request.args.get("tab", "overview")

    # 1. Exercise Stats (Current Week Monday-Sunday)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    weekly_workouts = (
        ExerciseLog.query.filter(
            ExerciseLog.user_id == current_user.id,
            ExerciseLog.date >= week_start,
            ExerciseLog.date <= week_end,
        )
        .order_by(ExerciseLog.date.desc(), ExerciseLog.created_at.desc())
        .all()
    )

    exercise_target = get_or_create_exercise_target(current_user.id)
    workout_days_done = len(set(w.date for w in weekly_workouts))
    total_workout_mins = sum(w.duration_minutes for w in weekly_workouts)
    total_workout_cals = sum(w.calories_burned or 0 for w in weekly_workouts)

    exercise_days_pct = (
        min(100, int((workout_days_done / exercise_target.target_days_per_week) * 100))
        if exercise_target.target_days_per_week > 0
        else 0
    )
    exercise_mins_pct = (
        min(100, int((total_workout_mins / exercise_target.target_minutes_per_week) * 100))
        if exercise_target.target_minutes_per_week > 0
        else 0
    )

    # 7-day workout chart breakdown
    day_workout_labels = [(week_start + timedelta(days=i)).strftime("%a") for i in range(7)]
    day_workout_mins = [0] * 7
    for w in weekly_workouts:
        idx = (w.date - week_start).days
        if 0 <= idx < 7:
            day_workout_mins[idx] += w.duration_minutes

    recent_workouts = (
        ExerciseLog.query.filter_by(user_id=current_user.id)
        .order_by(ExerciseLog.date.desc(), ExerciseLog.created_at.desc())
        .limit(10)
        .all()
    )

    # 2. Diet & Nutrition Stats (Today)
    diet_target = get_or_create_diet_target(current_user.id)
    today_meals = (
        DietLog.query.filter_by(user_id=current_user.id, date=today)
        .order_by(DietLog.created_at.asc())
        .all()
    )
    today_calories = sum(m.calories for m in today_meals)
    today_protein = sum(m.protein_g for m in today_meals)
    today_carbs = sum(m.carbs_g for m in today_meals)
    today_fats = sum(m.fats_g for m in today_meals)
    today_fiber = sum(m.fiber_g for m in today_meals)

    cal_pct = min(100, int((today_calories / diet_target.target_calories) * 100)) if diet_target.target_calories > 0 else 0
    prot_pct = min(100, int((today_protein / diet_target.target_protein_g) * 100)) if diet_target.target_protein_g > 0 else 0

    daily_health = get_or_create_daily_health(current_user.id, today)
    water_glasses = daily_health.water_ml // 250
    water_target_glasses = max(1, diet_target.target_water_ml // 250)
    water_pct = min(100, int((daily_health.water_ml / diet_target.target_water_ml) * 100)) if diet_target.target_water_ml > 0 else 0

    # 3. Body Measurements & Vitals
    latest_vitals = (
        BodyMeasurement.query.filter_by(user_id=current_user.id)
        .order_by(BodyMeasurement.date.desc(), BodyMeasurement.id.desc())
        .first()
    )
    all_vitals = (
        BodyMeasurement.query.filter_by(user_id=current_user.id)
        .order_by(BodyMeasurement.date.desc(), BodyMeasurement.id.desc())
        .limit(20)
        .all()
    )
    # Chronological measurements for trend chart
    vitals_chronological = sorted(all_vitals, key=lambda x: x.date)
    vitals_chart_labels = [v.date.strftime("%b %d") for v in vitals_chronological if v.weight_kg is not None]
    vitals_chart_weights = [v.weight_kg for v in vitals_chronological if v.weight_kg is not None]

    # 4. Medical Lab Reports
    medical_reports = (
        MedicalReport.query.filter_by(user_id=current_user.id)
        .order_by(MedicalReport.test_date.desc(), MedicalReport.id.desc())
        .all()
    )

    # 5. Health Issues & Doctor Visits
    active_issues = (
        HealthIssue.query.filter(
            HealthIssue.user_id == current_user.id,
            HealthIssue.status.in_(["Active", "Recovering"]),
        )
        .order_by(HealthIssue.start_date.desc())
        .all()
    )
    all_issues = (
        HealthIssue.query.filter_by(user_id=current_user.id)
        .order_by(HealthIssue.start_date.desc())
        .all()
    )

    # 6. Overall Daily Health / Vitality Score (0-100)
    # 25 pts: Workout progress
    ex_score = min(25, int((workout_days_done / max(1, exercise_target.target_days_per_week)) * 25))
    # 25 pts: Calorie balance (within 80%-110% of target = 25 pts, or proportional)
    cal_ratio = (today_calories / diet_target.target_calories) if diet_target.target_calories > 0 else 0
    if 0.8 <= cal_ratio <= 1.15:
        diet_score = 25
    elif cal_ratio > 0:
        diet_score = max(5, int(25 - abs(1.0 - cal_ratio) * 25))
    else:
        diet_score = 10
    # 25 pts: Water Hydration
    water_score = min(25, int((daily_health.water_ml / max(1, diet_target.target_water_ml)) * 25))
    # 25 pts: Sleep & Recovery
    sleep_score = 25 if (daily_health.sleep_hours or 0) >= 7.0 else int(((daily_health.sleep_hours or 0) / 7.0) * 25)
    vitality_score = min(100, ex_score + diet_score + water_score + sleep_score)

    return render_template(
        "health/dashboard.html",
        today=today,
        active_tab=active_tab,
        # Exercise
        exercise_target=exercise_target,
        weekly_workouts=weekly_workouts,
        recent_workouts=recent_workouts,
        workout_days_done=workout_days_done,
        total_workout_mins=total_workout_mins,
        total_workout_cals=total_workout_cals,
        exercise_days_pct=exercise_days_pct,
        exercise_mins_pct=exercise_mins_pct,
        day_workout_labels=day_workout_labels,
        day_workout_mins=day_workout_mins,
        # Diet
        diet_target=diet_target,
        today_meals=today_meals,
        today_calories=today_calories,
        today_protein=today_protein,
        today_carbs=today_carbs,
        today_fats=today_fats,
        today_fiber=today_fiber,
        cal_pct=cal_pct,
        prot_pct=prot_pct,
        daily_health=daily_health,
        water_glasses=water_glasses,
        water_target_glasses=water_target_glasses,
        water_pct=water_pct,
        # Vitals
        latest_vitals=latest_vitals,
        all_vitals=all_vitals,
        vitals_chart_labels=vitals_chart_labels,
        vitals_chart_weights=vitals_chart_weights,
        # Reports
        medical_reports=medical_reports,
        # Issues
        active_issues=active_issues,
        all_issues=all_issues,
        # Vitality
        vitality_score=vitality_score,
    )


# ═══════════════════════ EXERCISE ACTIONS ═══════════════════════

@health_bp.route("/exercise/target", methods=["POST"])
@login_required
def set_exercise_target():
    target = get_or_create_exercise_target(current_user.id)
    try:
        target.target_days_per_week = int(request.form.get("target_days_per_week", 4))
        target.target_minutes_per_week = int(request.form.get("target_minutes_per_week", 150))
        target.target_calories_per_week = int(request.form.get("target_calories_per_week", 1500))
        target.notes = request.form.get("notes", "").strip()
        db.session.commit()
        flash("Weekly exercise targets updated successfully!", "success")
    except (ValueError, TypeError) as e:
        flash("Invalid target values provided.", "danger")
    return redirect(url_for("health.dashboard", tab="exercise"))


@health_bp.route("/exercise/log", methods=["POST"])
@login_required
def log_exercise():
    try:
        log_date_str = request.form.get("date")
        log_date = datetime.strptime(log_date_str, "%Y-%m-%d").date() if log_date_str else date.today()
        workout_type = request.form.get("workout_type", "Running").strip()
        duration_minutes = int(request.form.get("duration_minutes", 30))
        calories_burned = int(request.form.get("calories_burned", 0)) if request.form.get("calories_burned") else 0
        intensity = request.form.get("intensity", "Moderate")
        exercises_details = request.form.get("exercises_details", "").strip()
        notes = request.form.get("notes", "").strip()

        log = ExerciseLog(
            user_id=current_user.id,
            date=log_date,
            workout_type=workout_type,
            duration_minutes=duration_minutes,
            calories_burned=calories_burned,
            intensity=intensity,
            exercises_details=exercises_details,
            notes=notes,
        )
        db.session.add(log)
        db.session.commit()
        flash(f"Logged {workout_type} workout ({duration_minutes} mins)!", "success")
    except Exception as e:
        flash(f"Error logging workout: {str(e)}", "danger")
    return redirect(url_for("health.dashboard", tab="exercise"))


@health_bp.route("/exercise/delete/<int:log_id>", methods=["POST"])
@login_required
def delete_exercise(log_id):
    log = ExerciseLog.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    db.session.delete(log)
    db.session.commit()
    flash("Workout log deleted.", "info")
    return redirect(url_for("health.dashboard", tab="exercise"))


# ═══════════════════════ VITALS ACTIONS ═══════════════════════

@health_bp.route("/vitals/log", methods=["POST"])
@login_required
def log_vitals():
    try:
        log_date_str = request.form.get("date")
        log_date = datetime.strptime(log_date_str, "%Y-%m-%d").date() if log_date_str else date.today()

        def parse_float(val):
            return float(val) if val and val.strip() else None

        def parse_int(val):
            return int(val) if val and val.strip() else None

        weight_kg = parse_float(request.form.get("weight_kg"))
        height_cm = parse_float(request.form.get("height_cm"))
        bp_sys = parse_int(request.form.get("blood_pressure_systolic"))
        bp_dia = parse_int(request.form.get("blood_pressure_diastolic"))
        resting_hr = parse_int(request.form.get("resting_heart_rate"))
        vision_right = request.form.get("vision_right", "").strip() or None
        vision_left = request.form.get("vision_left", "").strip() or None
        waist_cm = parse_float(request.form.get("waist_cm"))
        body_fat = parse_float(request.form.get("body_fat_pct"))
        notes = request.form.get("notes", "").strip() or None

        measurement = BodyMeasurement(
            user_id=current_user.id,
            date=log_date,
            weight_kg=weight_kg,
            height_cm=height_cm,
            blood_pressure_systolic=bp_sys,
            blood_pressure_diastolic=bp_dia,
            resting_heart_rate=resting_hr,
            vision_right=vision_right,
            vision_left=vision_left,
            waist_cm=waist_cm,
            body_fat_pct=body_fat,
            notes=notes,
        )
        measurement.calculate_bmi()
        db.session.add(measurement)
        db.session.commit()
        flash("Body measurements & vitals recorded!", "success")
    except Exception as e:
        flash(f"Error recording vitals: {str(e)}", "danger")
    return redirect(url_for("health.dashboard", tab="vitals"))


@health_bp.route("/vitals/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_vitals(item_id):
    measurement = BodyMeasurement.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(measurement)
    db.session.commit()
    flash("Measurement entry removed.", "info")
    return redirect(url_for("health.dashboard", tab="vitals"))


# ═══════════════════════ DIET & HYDRATION ACTIONS ═══════════════════════

@health_bp.route("/diet/target", methods=["POST"])
@login_required
def set_diet_target():
    target = get_or_create_diet_target(current_user.id)
    try:
        target.target_calories = int(request.form.get("target_calories", 2000))
        target.target_protein_g = float(request.form.get("target_protein_g", 80))
        target.target_carbs_g = float(request.form.get("target_carbs_g", 250))
        target.target_fats_g = float(request.form.get("target_fats_g", 65))
        target.target_fiber_g = float(request.form.get("target_fiber_g", 30))
        target.target_water_ml = int(request.form.get("target_water_ml", 2500))
        db.session.commit()
        flash("Nutrition targets updated successfully!", "success")
    except Exception as e:
        flash("Error saving nutrition targets.", "danger")
    return redirect(url_for("health.dashboard", tab="diet"))


@health_bp.route("/diet/log", methods=["POST"])
@login_required
def log_diet():
    try:
        log_date_str = request.form.get("date")
        log_date = datetime.strptime(log_date_str, "%Y-%m-%d").date() if log_date_str else date.today()
        meal_type = request.form.get("meal_type", "Breakfast")
        food_items = request.form.get("food_items", "").strip()

        # Selected tags can come from checkboxes or tag inputs
        tags_selected = request.form.getlist("food_tags")
        if not tags_selected and request.form.get("custom_tags"):
            tags_selected = [t.strip() for t in request.form.get("custom_tags").split(",")]
        food_tags = ", ".join([t for t in tags_selected if t])

        def parse_float(val):
            return float(val) if val and val.strip() else 0.0

        calories = parse_float(request.form.get("calories"))
        protein_g = parse_float(request.form.get("protein_g"))
        carbs_g = parse_float(request.form.get("carbs_g"))
        fats_g = parse_float(request.form.get("fats_g"))
        fiber_g = parse_float(request.form.get("fiber_g"))
        notes = request.form.get("notes", "").strip()

        meal = DietLog(
            user_id=current_user.id,
            date=log_date,
            meal_type=meal_type,
            food_items=food_items,
            food_tags=food_tags,
            calories=calories,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fats_g=fats_g,
            fiber_g=fiber_g,
            notes=notes,
        )
        db.session.add(meal)
        db.session.commit()
        flash(f"Logged {meal_type} meal ({int(calories)} kcal)!", "success")
    except Exception as e:
        flash(f"Error logging meal: {str(e)}", "danger")
    return redirect(url_for("health.dashboard", tab="diet"))


@health_bp.route("/diet/delete/<int:log_id>", methods=["POST"])
@login_required
def delete_diet(log_id):
    meal = DietLog.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    db.session.delete(meal)
    db.session.commit()
    flash("Meal entry deleted.", "info")
    return redirect(url_for("health.dashboard", tab="diet"))


@health_bp.route("/hydration/quick-add", methods=["POST"])
@login_required
def quick_hydration():
    today = date.today()
    daily = get_or_create_daily_health(current_user.id, today)
    delta_ml = int(request.form.get("amount_ml", 250))
    daily.water_ml = max(0, daily.water_ml + delta_ml)
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({
            "status": "success",
            "water_ml": daily.water_ml,
            "glasses": daily.water_ml // 250,
        })
    flash(f"Hydration updated! Today's water: {daily.water_ml} ml ({daily.water_ml // 250} glasses)", "success")
    return redirect(url_for("health.dashboard", tab="diet"))


@health_bp.route("/sleep/log", methods=["POST"])
@login_required
def log_sleep():
    today = date.today()
    daily = get_or_create_daily_health(current_user.id, today)
    try:
        daily.sleep_hours = float(request.form.get("sleep_hours", 7.0))
        daily.sleep_quality = request.form.get("sleep_quality", "Good")
        daily.energy_level = int(request.form.get("energy_level", 4))
        daily.notes = request.form.get("notes", "").strip()
        db.session.commit()
        flash("Sleep & energy logged!", "success")
    except Exception as e:
        flash(f"Error logging sleep: {str(e)}", "danger")
    return redirect(url_for("health.dashboard", tab="overview"))


# ═══════════════════════ HEALTH ISSUES & DOCTOR VISITS ═══════════════════════

@health_bp.route("/issue/log", methods=["POST"])
@login_required
def log_health_issue():
    try:
        start_date_str = request.form.get("start_date")
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else date.today()
        
        end_date_str = request.form.get("end_date")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str and end_date_str.strip() else None

        follow_up_str = request.form.get("follow_up_date")
        follow_up_date = datetime.strptime(follow_up_str, "%Y-%m-%d").date() if follow_up_str and follow_up_str.strip() else None

        title = request.form.get("title", "").strip()
        issue_type = request.form.get("issue_type", "Fever / Infection")
        severity = request.form.get("severity", "Moderate")
        status = request.form.get("status", "Active")
        symptoms = request.form.get("symptoms", "").strip()
        doctor_visited = bool(request.form.get("doctor_visited"))
        doctor_name = request.form.get("doctor_name", "").strip() or None
        clinic_hospital = request.form.get("clinic_hospital", "").strip() or None
        diagnosis = request.form.get("diagnosis", "").strip() or None
        prescription = request.form.get("prescription", "").strip() or None
        notes = request.form.get("notes", "").strip() or None

        issue = HealthIssue(
            user_id=current_user.id,
            title=title,
            issue_type=issue_type,
            severity=severity,
            status=status,
            start_date=start_date,
            end_date=end_date,
            symptoms=symptoms,
            doctor_visited=doctor_visited,
            doctor_name=doctor_name,
            clinic_hospital=clinic_hospital,
            diagnosis=diagnosis,
            prescription=prescription,
            follow_up_date=follow_up_date,
            notes=notes,
        )
        db.session.add(issue)
        db.session.commit()
        flash(f"Logged health issue: {title}", "success")
    except Exception as e:
        flash(f"Error recording health issue: {str(e)}", "danger")
    return redirect(url_for("health.dashboard", tab="issues"))


@health_bp.route("/issue/<int:issue_id>/status", methods=["POST"])
@login_required
def update_issue_status(issue_id):
    issue = HealthIssue.query.filter_by(id=issue_id, user_id=current_user.id).first_or_404()
    new_status = request.form.get("status", "Resolved")
    issue.status = new_status
    if new_status == "Resolved" and not issue.end_date:
        issue.end_date = date.today()
    db.session.commit()
    flash(f"Marked '{issue.title}' as {new_status}.", "info")
    return redirect(url_for("health.dashboard", tab="issues"))


@health_bp.route("/issue/delete/<int:issue_id>", methods=["POST"])
@login_required
def delete_health_issue(issue_id):
    issue = HealthIssue.query.filter_by(id=issue_id, user_id=current_user.id).first_or_404()
    db.session.delete(issue)
    db.session.commit()
    flash("Health issue record deleted.", "info")
    return redirect(url_for("health.dashboard", tab="issues"))


# ═══════════════════════ MEDICAL LAB REPORTS ═══════════════════════

@health_bp.route("/reports/upload", methods=["POST"])
@login_required
def upload_report():
    try:
        title = request.form.get("title", "Health Checkup Report").strip()
        test_date_str = request.form.get("test_date")
        test_date = datetime.strptime(test_date_str, "%Y-%m-%d").date() if test_date_str else date.today()
        lab_name = request.form.get("lab_name", "").strip() or None
        doctor_name = request.form.get("doctor_name", "").strip() or None
        summary_notes = request.form.get("summary_notes", "").strip() or None

        pdf_filename = None
        orig_filename = None
        file = request.files.get("report_pdf")
        if file and file.filename != "":
            if not allowed_pdf(file.filename):
                flash("Only PDF files are supported for medical reports.", "danger")
                return redirect(url_for("health.dashboard", tab="reports"))

            orig_filename = secure_filename(file.filename)
            unique_name = f"user{current_user.id}_{uuid.uuid4().hex[:10]}_{orig_filename}"
            upload_folder = current_app.config.get("UPLOAD_FOLDER")
            if upload_folder:
                os.makedirs(upload_folder, exist_ok=True)
                dest_path = os.path.join(upload_folder, unique_name)
                file.save(dest_path)
                pdf_filename = unique_name

        def parse_float(val):
            return float(val) if val and val.strip() else None

        report = MedicalReport(
            user_id=current_user.id,
            test_date=test_date,
            title=title,
            lab_name=lab_name,
            doctor_name=doctor_name,
            pdf_filename=pdf_filename,
            original_filename=orig_filename,
            summary_notes=summary_notes,
            # CBC
            hemoglobin=parse_float(request.form.get("hemoglobin")),
            wbc_count=parse_float(request.form.get("wbc_count")),
            rbc_count=parse_float(request.form.get("rbc_count")),
            platelet_count=parse_float(request.form.get("platelet_count")),
            hematocrit_pct=parse_float(request.form.get("hematocrit_pct")),
            # Lipid
            total_cholesterol=parse_float(request.form.get("total_cholesterol")),
            hdl_cholesterol=parse_float(request.form.get("hdl_cholesterol")),
            ldl_cholesterol=parse_float(request.form.get("ldl_cholesterol")),
            triglycerides=parse_float(request.form.get("triglycerides")),
            vldl=parse_float(request.form.get("vldl")),
            # Vitamins
            vitamin_d=parse_float(request.form.get("vitamin_d")),
            vitamin_b12=parse_float(request.form.get("vitamin_b12")),
            iron_ferritin=parse_float(request.form.get("iron_ferritin")),
            calcium=parse_float(request.form.get("calcium")),
            # Metabolic
            blood_sugar_fasting=parse_float(request.form.get("blood_sugar_fasting")),
            hba1c=parse_float(request.form.get("hba1c")),
            serum_creatinine=parse_float(request.form.get("serum_creatinine")),
            uric_acid=parse_float(request.form.get("uric_acid")),
            sgpt_alt=parse_float(request.form.get("sgpt_alt")),
            sgot_ast=parse_float(request.form.get("sgot_ast")),
            tsh=parse_float(request.form.get("tsh")),
            other_findings=request.form.get("other_findings", "").strip() or None,
        )
        db.session.add(report)
        db.session.commit()
        flash(f"Medical report '{title}' saved successfully!", "success")
    except Exception as e:
        flash(f"Error uploading report: {str(e)}", "danger")
    return redirect(url_for("health.dashboard", tab="reports"))


@health_bp.route("/reports/<int:report_id>")
@login_required
def view_report_detail(report_id):
    report = MedicalReport.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()
    panels = report.get_parameter_analysis()
    return render_template("health/report_detail.html", report=report, panels=panels)


@health_bp.route("/reports/<int:report_id>/pdf")
@login_required
def download_report_pdf(report_id):
    report = MedicalReport.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()
    if not report.pdf_filename:
        flash("No PDF file attached to this report.", "warning")
        return redirect(url_for("health.dashboard", tab="reports"))

    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    file_path = os.path.join(upload_folder, report.pdf_filename)
    if not os.path.exists(file_path):
        flash("PDF file was not found on the server.", "danger")
        return redirect(url_for("health.dashboard", tab="reports"))

    # as_attachment=False enables in-browser viewing for modern PDF viewers
    return send_file(
        file_path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=report.original_filename or f"report_{report.id}.pdf",
    )


@health_bp.route("/reports/<int:report_id>/delete", methods=["POST"])
@login_required
def delete_report(report_id):
    report = MedicalReport.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()
    if report.pdf_filename:
        upload_folder = current_app.config.get("UPLOAD_FOLDER")
        if upload_folder:
            file_path = os.path.join(upload_folder, report.pdf_filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
    db.session.delete(report)
    db.session.commit()
    flash(f"Report '{report.title}' removed.", "info")
    return redirect(url_for("health.dashboard", tab="reports"))
