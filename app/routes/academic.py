from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.academic import Semester, Course, Assessment, StudyGoal

academic_bp = Blueprint("academic", __name__, url_prefix="/academic")

@academic_bp.route("/")
@login_required
def dashboard():
    semesters = Semester.query.filter_by(user_id=current_user.id).all()
    courses = Course.query.filter_by(user_id=current_user.id).all()
    upcoming_tests = (
        Assessment.query.join(Course)
        .filter(Course.user_id == current_user.id, Assessment.is_completed == False)
        .order_by(Assessment.date.asc())
        .all()
    )
    study_goals = StudyGoal.query.filter_by(user_id=current_user.id).order_by(StudyGoal.target_date.asc()).all()

    # Calculate metrics
    total_credits = 0
    total_grade_points = 0.0
    completed_credits = 0

    for course in courses:
        total_credits += course.credits
        if course.grade_point is not None:
            total_grade_points += course.grade_point * course.credits
            completed_credits += course.credits

    gpa_overall = (total_grade_points / completed_credits) if completed_credits > 0 else 0.0

    # Prepare chart data
    chart_labels = []
    chart_gpas = []

    for sem in semesters:
        chart_labels.append(sem.name)
        if sem.gpa is not None:
            chart_gpas.append(sem.gpa)
        else:
            sem_courses = [c for c in courses if c.semester_id == sem.id and c.grade_point is not None]
            sem_credits = sum(c.credits for c in sem_courses)
            sem_gp = sum(c.grade_point * c.credits for c in sem_courses)
            sem_gpa = (sem_gp / sem_credits) if sem_credits > 0 else 0.0
            chart_gpas.append(round(sem_gpa, 2))

    return render_template(
        "academic/dashboard.html",
        semesters=semesters,
        courses=courses,
        upcoming_tests=upcoming_tests,
        study_goals=study_goals,
        total_credits=total_credits,
        completed_credits=completed_credits,
        gpa_overall=round(gpa_overall, 2),
        chart_labels=chart_labels,
        chart_gpas=chart_gpas,
    )

@academic_bp.route("/manage")
@login_required
def manage():
    semesters = Semester.query.filter_by(user_id=current_user.id).all()
    courses = Course.query.filter_by(user_id=current_user.id).all()
    return render_template("academic/manage.html", semesters=semesters, courses=courses)

@academic_bp.route("/semester/add", methods=["POST"])
@login_required
def add_semester():
    name = request.form.get("name", "").strip()
    gpa_str = request.form.get("gpa", "").strip()

    if not name:
        flash("Semester name is required.", "danger")
        return redirect(url_for("academic.manage"))

    gpa = None
    if gpa_str:
        try:
            gpa = float(gpa_str)
        except ValueError:
            flash("Invalid GPA format.", "danger")
            return redirect(url_for("academic.manage"))

    sem = Semester(user_id=current_user.id, name=name, gpa=gpa)
    db.session.add(sem)
    db.session.commit()
    flash("Semester added.", "success")
    return redirect(url_for("academic.manage"))

@academic_bp.route("/semester/delete/<int:sem_id>", methods=["POST"])
@login_required
def delete_semester(sem_id):
    sem = Semester.query.filter_by(id=sem_id, user_id=current_user.id).first_or_404()
    db.session.delete(sem)
    db.session.commit()
    flash("Semester deleted.", "info")
    return redirect(url_for("academic.manage"))

@academic_bp.route("/course/add", methods=["POST"])
@login_required
def add_course():
    name = request.form.get("name", "").strip()
    credits_str = request.form.get("credits", "3").strip()
    semester_id_str = request.form.get("semester_id", "").strip()
    grade = request.form.get("grade", "").strip() or None
    grade_point_str = request.form.get("grade_point", "").strip()
    marks_obtained_str = request.form.get("marks_obtained", "").strip()
    max_marks_str = request.form.get("max_marks", "100").strip()

    if not name:
        flash("Subject/Course name is required.", "danger")
        return redirect(url_for("academic.manage"))

    try:
        credits = int(credits_str)
    except ValueError:
        flash("Credits must be a number.", "danger")
        return redirect(url_for("academic.manage"))

    semester_id = None
    if semester_id_str:
        semester_id = int(semester_id_str)
        Semester.query.filter_by(id=semester_id, user_id=current_user.id).first_or_404()

    grade_point = None
    if grade_point_str:
        try:
            grade_point = float(grade_point_str)
        except ValueError:
            flash("Invalid Grade Point format.", "danger")
            return redirect(url_for("academic.manage"))

    marks_obtained = None
    if marks_obtained_str:
        try:
            marks_obtained = float(marks_obtained_str)
        except ValueError:
            flash("Invalid marks format.", "danger")
            return redirect(url_for("academic.manage"))

    max_marks = 100.0
    if max_marks_str:
        try:
            max_marks = float(max_marks_str)
        except ValueError:
            flash("Invalid max marks format.", "danger")
            return redirect(url_for("academic.manage"))

    course = Course(
        user_id=current_user.id,
        semester_id=semester_id,
        name=name,
        credits=credits,
        grade=grade,
        grade_point=grade_point,
        marks_obtained=marks_obtained,
        max_marks=max_marks
    )
    db.session.add(course)
    db.session.commit()
    flash("Course added.", "success")
    return redirect(url_for("academic.manage"))

@academic_bp.route("/course/delete/<int:course_id>", methods=["POST"])
@login_required
def delete_course(course_id):
    course = Course.query.filter_by(id=course_id, user_id=current_user.id).first_or_404()
    db.session.delete(course)
    db.session.commit()
    flash("Course deleted.", "info")
    return redirect(url_for("academic.manage"))

@academic_bp.route("/test/add", methods=["POST"])
@login_required
def add_test():
    course_id_str = request.form.get("course_id")
    name = request.form.get("name", "").strip()
    date_str = request.form.get("date")
    max_marks_str = request.form.get("max_marks", "").strip()

    if not course_id_str or not name or not date_str:
        flash("Subject, name, and date are required for a test.", "danger")
        return redirect(url_for("academic.dashboard"))

    course_id = int(course_id_str)
    Course.query.filter_by(id=course_id, user_id=current_user.id).first_or_404()

    max_marks = None
    if max_marks_str:
        try:
            max_marks = float(max_marks_str)
        except ValueError:
            flash("Max marks must be a number.", "danger")
            return redirect(url_for("academic.dashboard"))

    try:
        date_val = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for("academic.dashboard"))

    test = Assessment(
        course_id=course_id,
        name=name,
        date=date_val,
        max_marks=max_marks,
        is_completed=False
    )
    db.session.add(test)
    db.session.commit()
    flash("Upcoming test added.", "success")
    return redirect(url_for("academic.dashboard"))

@academic_bp.route("/test/complete/<int:test_id>", methods=["POST"])
@login_required
def complete_test(test_id):
    test = Assessment.query.join(Course).filter(
        Assessment.id == test_id,
        Course.user_id == current_user.id
    ).first_or_404()

    marks_str = request.form.get("marks_obtained", "").strip()
    if not marks_str:
        flash("Marks obtained is required to complete a test.", "danger")
        return redirect(url_for("academic.dashboard"))

    try:
        marks = float(marks_str)
    except ValueError:
        flash("Invalid marks format.", "danger")
        return redirect(url_for("academic.dashboard"))

    test.marks_obtained = marks
    test.is_completed = True
    db.session.commit()
    flash("Test marked as completed.", "success")
    return redirect(url_for("academic.dashboard"))

@academic_bp.route("/test/delete/<int:test_id>", methods=["POST"])
@login_required
def delete_test(test_id):
    test = Assessment.query.join(Course).filter(
        Assessment.id == test_id,
        Course.user_id == current_user.id
    ).first_or_404()
    db.session.delete(test)
    db.session.commit()
    flash("Test deleted.", "info")
    return redirect(url_for("academic.dashboard"))

@academic_bp.route("/goal/add", methods=["POST"])
@login_required
def add_goal():
    title = request.form.get("title", "").strip()
    date_str = request.form.get("target_date")

    if not title or not date_str:
        flash("Goal title and date are required.", "danger")
        return redirect(url_for("academic.dashboard"))

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for("academic.dashboard"))

    goal = StudyGoal(user_id=current_user.id, title=title, target_date=target_date)
    db.session.add(goal)
    db.session.commit()
    flash("Study goal added.", "success")
    return redirect(url_for("academic.dashboard"))

@academic_bp.route("/goal/toggle/<int:goal_id>", methods=["POST"])
@login_required
def toggle_goal(goal_id):
    goal = StudyGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    goal.is_completed = not goal.is_completed
    db.session.commit()
    return redirect(url_for("academic.dashboard"))

@academic_bp.route("/goal/delete/<int:goal_id>", methods=["POST"])
@login_required
def delete_goal(goal_id):
    goal = StudyGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    db.session.delete(goal)
    db.session.commit()
    flash("Study goal deleted.", "info")
    return redirect(url_for("academic.dashboard"))
