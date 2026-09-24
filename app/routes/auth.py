from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models.user import User
from app.models.otp import EmailOTP
from app.utils.email import send_otp_email

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("auth.register"))

        if confirm_password and password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return redirect(url_for("auth.register"))

        # Check existing username
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            if existing_username.is_verified:
                flash("That username is already taken.", "danger")
                return redirect(url_for("auth.register"))
            elif existing_username.email != email:
                flash("That username is already reserved by a pending registration.", "danger")
                return redirect(url_for("auth.register"))

        # Check existing email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            if existing_user.is_verified:
                flash("An account with that email already exists. Please log in.", "danger")
                return redirect(url_for("auth.login"))
            else:
                # Update existing unverified user record with new username/password
                existing_user.username = username
                existing_user.set_password(password)
                user = existing_user
        else:
            user = User(username=username, email=email, is_verified=False)
            user.set_password(password)
            db.session.add(user)

        db.session.commit()

        # Generate OTP and send email
        expiry_minutes = current_app.config.get("OTP_EXPIRY_MINUTES", 10)
        otp_code = EmailOTP.create_otp(email, "registration", expires_in_minutes=expiry_minutes)
        success, msg = send_otp_email(email, otp_code, "registration")

        session["otp_email"] = email
        session["otp_purpose"] = "registration"

        if success:
            flash(
                f"Account created! We've sent a 6-digit verification code to {email}. Please verify your email to continue.",
                "success",
            )
        else:
            flash(
                f"Account created! Please enter your verification code sent to {email}.",
                "info",
            )

        return redirect(url_for("auth.verify_otp", email=email, purpose="registration"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username_or_email = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username_or_email or not password:
            flash("Please enter both your username/email and password.", "danger")
            return redirect(url_for("auth.login"))

        # Allow login via username or email
        user = (
            User.query.filter(
                (User.username == username_or_email)
                | (User.email == username_or_email.lower())
            ).first()
        )

        if user is None or not user.check_password(password):
            flash("Invalid username/email or password.", "danger")
            return redirect(url_for("auth.login"))

        # Compulsory verification check
        if not user.is_verified:
            expiry_minutes = current_app.config.get("OTP_EXPIRY_MINUTES", 10)
            otp_code = EmailOTP.create_otp(user.email, "registration", expires_in_minutes=expiry_minutes)
            send_otp_email(user.email, otp_code, "registration")

            session["otp_email"] = user.email
            session["otp_purpose"] = "registration"

            flash(
                "Your email has not been verified yet. We've sent a new verification code to your email. Please verify to activate your account.",
                "warning",
            )
            return redirect(
                url_for("auth.verify_otp", email=user.email, purpose="registration")
            )

        login_user(user)
        flash(f"Welcome back, {user.username}!", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    email = request.args.get("email") or request.form.get("email") or session.get("otp_email")
    purpose = request.args.get("purpose") or request.form.get("purpose") or session.get("otp_purpose", "registration")

    if not email:
        flash("Session expired or missing email. Please try again.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        # Handle 6 individual digits or single input
        otp_digit_keys = [f"otp_{i}" for i in range(1, 7)]
        if all(k in request.form for k in otp_digit_keys):
            otp_code = "".join(request.form.get(k, "").strip() for k in otp_digit_keys)
        else:
            otp_code = request.form.get("otp_code", "").strip()

        if not otp_code or len(otp_code) != 6:
            flash("Please enter the complete 6-digit verification code.", "danger")
            return render_template("auth/verify_otp.html", email=email, purpose=purpose)

        reset_window = current_app.config.get("RESET_PASSWORD_WINDOW_MINUTES", 5)
        success, result_data = EmailOTP.verify_otp(
            email=email, otp_code=otp_code, purpose=purpose, reset_window_minutes=reset_window
        )

        if not success:
            flash(result_data, "danger")
            return render_template("auth/verify_otp.html", email=email, purpose=purpose)

        # Handle successful verification by purpose
        if purpose == "registration":
            user = User.query.filter_by(email=email).first()
            if user:
                user.is_verified = True
                db.session.commit()
                # Clear session verification markers
                session.pop("otp_email", None)
                session.pop("otp_purpose", None)
                flash("Your email has been verified successfully! You can now log in.", "success")
                return redirect(url_for("auth.login"))
            else:
                flash("Account not found. Please register again.", "danger")
                return redirect(url_for("auth.register"))

        elif purpose == "reset_password":
            reset_token = result_data
            session.pop("otp_email", None)
            session.pop("otp_purpose", None)
            flash(
                "Code verified! Your password reset window is now active for 5 minutes.",
                "success",
            )
            return redirect(url_for("auth.reset_password", token=reset_token))

    return render_template("auth/verify_otp.html", email=email, purpose=purpose)


@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    email = request.form.get("email", "").strip().lower() or session.get("otp_email")
    purpose = request.form.get("purpose", "registration") or session.get("otp_purpose", "registration")

    if not email:
        flash("Email address is required to resend verification code.", "danger")
        return redirect(url_for("auth.login"))

    # For reset_password, make sure user exists and is verified
    if purpose == "reset_password":
        user = User.query.filter_by(email=email).first()
        if not user or not user.is_verified:
            flash("Cannot send password reset code to unverified or nonexistent email.", "danger")
            return redirect(url_for("auth.forgot_password"))

    expiry_minutes = current_app.config.get("OTP_EXPIRY_MINUTES", 10)
    otp_code = EmailOTP.create_otp(email, purpose, expires_in_minutes=expiry_minutes)
    send_otp_email(email, otp_code, purpose)

    session["otp_email"] = email
    session["otp_purpose"] = purpose

    flash(f"A new 6-digit verification code has been sent to {email}.", "success")
    return redirect(url_for("auth.verify_otp", email=email, purpose=purpose))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email:
            flash("Please enter your registered email address.", "danger")
            return redirect(url_for("auth.forgot_password"))

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("No registered account found with that email address.", "danger")
            return redirect(url_for("auth.forgot_password"))

        # Compulsory rule: Unverified accounts cannot unlock/use forgot password
        if not user.is_verified:
            flash(
                "This account's email has not been verified yet. Unverified accounts cannot reset passwords. "
                "Please verify your account first or register with a verified email.",
                "warning",
            )
            return redirect(url_for("auth.forgot_password"))

        expiry_minutes = current_app.config.get("OTP_EXPIRY_MINUTES", 10)
        otp_code = EmailOTP.create_otp(email, "reset_password", expires_in_minutes=expiry_minutes)
        send_otp_email(email, otp_code, "reset_password")

        session["otp_email"] = email
        session["otp_purpose"] = "reset_password"

        flash(
            f"We've sent a 6-digit password reset OTP to {email}. Please enter it below.",
            "info",
        )
        return redirect(url_for("auth.verify_otp", email=email, purpose="reset_password"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    otp_record = EmailOTP.get_valid_reset_record(token)

    if not otp_record:
        flash(
            "Your password reset window has expired (5-minute limit) or the link is invalid. Please request a new OTP.",
            "danger",
        )
        return redirect(url_for("auth.forgot_password"))

    # Calculate remaining seconds for the 5-minute active window
    now = datetime.now(timezone.utc)
    expiry = otp_record.reset_token_expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    remaining_seconds = max(0, int((expiry - now).total_seconds()))

    if remaining_seconds <= 0:
        flash("Password reset window has expired. Please request a new OTP.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not password or not confirm_password:
            flash("Please fill in both password fields.", "danger")
            return render_template(
                "auth/reset_password.html",
                token=token,
                email=otp_record.email,
                remaining_seconds=remaining_seconds,
            )

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template(
                "auth/reset_password.html",
                token=token,
                email=otp_record.email,
                remaining_seconds=remaining_seconds,
            )

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template(
                "auth/reset_password.html",
                token=token,
                email=otp_record.email,
                remaining_seconds=remaining_seconds,
            )

        user = User.query.filter_by(email=otp_record.email).first()
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for("auth.login"))

        user.set_password(password)
        EmailOTP.consume_reset_token(token)
        db.session.commit()

        flash("Your password has been successfully reset! Please log in with your new password.", "success")
        return redirect(url_for("auth.login"))

    return render_template(
        "auth/reset_password.html",
        token=token,
        email=otp_record.email,
        remaining_seconds=remaining_seconds,
    )


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for("auth.login"))
