import secrets
from datetime import datetime, timedelta, timezone
from app import db


class EmailOTP(db.Model):
    __tablename__ = "email_otps"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    otp_code = db.Column(db.String(6), nullable=False)
    purpose = db.Column(db.String(30), nullable=False)  # 'registration' or 'reset_password'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)

    # Temporary reset token generated upon successful OTP verification for password reset
    reset_token = db.Column(db.String(64), unique=True, nullable=True, index=True)
    reset_token_expires_at = db.Column(db.DateTime, nullable=True)

    @classmethod
    def create_otp(cls, email: str, purpose: str, expires_in_minutes: int = 10) -> str:
        """Invalidate old OTPs for this email/purpose, generate a new 6-digit OTP, save and return code."""
        # Invalidate existing unused OTPs
        cls.query.filter_by(email=email, purpose=purpose, is_used=False).update(
            {"is_used": True}
        )

        # Generate a cryptographically secure 6-digit OTP
        otp_code = f"{secrets.randbelow(900000) + 100000}"
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=expires_in_minutes)

        otp_record = cls(
            email=email,
            otp_code=otp_code,
            purpose=purpose,
            created_at=now,
            expires_at=expires_at,
            is_used=False,
        )
        db.session.add(otp_record)
        db.session.commit()
        return otp_code

    @classmethod
    def verify_otp(
        cls, email: str, otp_code: str, purpose: str, reset_window_minutes: int = 5
    ):
        """
        Verify the provided OTP.
        Returns:
            (True, reset_token) if successful (reset_token is generated for 'reset_password', else None)
            (False, error_message) if invalid/expired
        """
        now = datetime.now(timezone.utc)
        record = (
            cls.query.filter_by(
                email=email, otp_code=str(otp_code).strip(), purpose=purpose, is_used=False
            )
            .order_by(cls.created_at.desc())
            .first()
        )

        if not record:
            return False, "Invalid verification code. Please check and try again."

        record_expires_at = record.expires_at
        if record_expires_at.tzinfo is None:
            record_expires_at = record_expires_at.replace(tzinfo=timezone.utc)

        if record_expires_at < now:
            record.is_used = True
            db.session.commit()
            return False, "Verification code has expired. Please request a new one."

        # Mark OTP as used
        record.is_used = True

        reset_token = None
        if purpose == "reset_password":
            # Generate secure token with strict 5-minute expiry
            reset_token = secrets.token_urlsafe(32)
            record.reset_token = reset_token
            record.reset_token_expires_at = now + timedelta(minutes=reset_window_minutes)

        db.session.commit()
        return True, reset_token

    @classmethod
    def get_valid_reset_record(cls, token: str):
        """Validate reset token and ensure it has not passed the 5-minute window."""
        if not token:
            return None

        record = cls.query.filter_by(reset_token=token, purpose="reset_password").first()
        if not record:
            return None

        now = datetime.now(timezone.utc)
        token_expires_at = record.reset_token_expires_at
        if token_expires_at is None:
            return None

        if token_expires_at.tzinfo is None:
            token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)

        if token_expires_at < now:
            return None

        return record

    @classmethod
    def consume_reset_token(cls, token: str):
        """Invalidate the reset token once password has been updated."""
        record = cls.query.filter_by(reset_token=token).first()
        if record:
            record.reset_token = None
            record.reset_token_expires_at = None
            db.session.commit()

    def __repr__(self):
        return f"<EmailOTP {self.email} - {self.purpose}>"
