import unittest
from datetime import datetime, timedelta, timezone
from app import create_app, db
from app.models.user import User
from app.models.otp import EmailOTP
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class AuthOTPTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_registration_and_compulsory_otp_flow(self):
        # 1. Register a new user
        res = self.client.post("/register", data={
            "username": "alex",
            "email": "alex@example.com",
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Verify Your Email", res.data)

        # Check DB - user is not verified yet
        user = User.query.filter_by(email="alex@example.com").first()
        self.assertIsNotNone(user)
        self.assertFalse(user.is_verified)

        # Check OTP created
        otp_rec = EmailOTP.query.filter_by(email="alex@example.com", purpose="registration").first()
        self.assertIsNotNone(otp_rec)
        self.assertFalse(otp_rec.is_used)

        # 2. Try logging in before verifying email -> should fail and redirect to OTP verification
        login_res = self.client.post("/login", data={
            "username": "alex",
            "password": "Password123!"
        }, follow_redirects=True)
        self.assertIn(b"Your email has not been verified yet", login_res.data)
        self.assertIn(b"Verify Your Email", login_res.data)

        # 3. Enter wrong OTP
        verify_fail = self.client.post("/verify-otp", data={
            "email": "alex@example.com",
            "purpose": "registration",
            "otp_code": "000000"
        }, follow_redirects=True)
        self.assertIn(b"Invalid verification code", verify_fail.data)
        user = User.query.filter_by(email="alex@example.com").first()
        self.assertFalse(user.is_verified)

        # 4. Enter correct OTP
        latest_otp = EmailOTP.query.filter_by(email="alex@example.com", purpose="registration", is_used=False).first()
        verify_success = self.client.post("/verify-otp", data={
            "email": "alex@example.com",
            "purpose": "registration",
            "otp_code": latest_otp.otp_code
        }, follow_redirects=True)
        self.assertIn(b"verified successfully", verify_success.data)

        # User is now verified
        user = User.query.filter_by(email="alex@example.com").first()
        self.assertTrue(user.is_verified)

        # 5. Now user can log in successfully
        login_success = self.client.post("/login", data={
            "username": "alex",
            "password": "Password123!"
        }, follow_redirects=True)
        self.assertIn(b"Dashboard", login_success.data)

    def test_forgot_password_unverified_blocked(self):
        # Create unverified user
        unverified_user = User(username="unverified", email="unverified@example.com", is_verified=False)
        unverified_user.set_password("pass123")
        db.session.add(unverified_user)
        db.session.commit()

        # Try forgot password
        res = self.client.post("/forgot-password", data={
            "email": "unverified@example.com"
        }, follow_redirects=True)
        self.assertIn(b"Unverified accounts cannot reset passwords", res.data)

    def test_forgot_password_verified_and_5_min_window(self):
        # Create verified user
        verified_user = User(username="verified", email="verified@example.com", is_verified=True)
        verified_user.set_password("oldpassword")
        db.session.add(verified_user)
        db.session.commit()

        # 1. Request forgot password OTP
        fp_res = self.client.post("/forgot-password", data={
            "email": "verified@example.com"
        }, follow_redirects=True)
        self.assertIn(b"Password Reset Verification", fp_res.data)

        otp_rec = EmailOTP.query.filter_by(email="verified@example.com", purpose="reset_password", is_used=False).first()
        self.assertIsNotNone(otp_rec)

        # 2. Verify reset OTP
        verify_res = self.client.post("/verify-otp", data={
            "email": "verified@example.com",
            "purpose": "reset_password",
            "otp_code": otp_rec.otp_code
        }, follow_redirects=True)
        self.assertIn(b"Set New Password", verify_res.data)
        self.assertIn(b"Reset window expires in", verify_res.data)

        # Retrieve generated reset token
        updated_rec = db.session.get(EmailOTP, otp_rec.id)
        self.assertTrue(updated_rec.is_used)
        self.assertIsNotNone(updated_rec.reset_token)
        self.assertIsNotNone(updated_rec.reset_token_expires_at)

        token = updated_rec.reset_token

        # 3. Test expired token (> 5 min)
        # Manually expire the token
        updated_rec.reset_token_expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        db.session.commit()

        expired_res = self.client.get(f"/reset-password/{token}", follow_redirects=True)
        self.assertIn(b"expired (5-minute limit)", expired_res.data)

        # 4. Test valid active reset window
        # Reset expiry to now + 4 minutes
        updated_rec.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=4)
        db.session.commit()

        reset_res = self.client.post(f"/reset-password/{token}", data={
            "password": "brandnewpassword",
            "confirm_password": "brandnewpassword"
        }, follow_redirects=True)
        self.assertIn(b"Your password has been successfully reset", reset_res.data)

        # Verify password actually changed
        user = User.query.filter_by(email="verified@example.com").first()
        self.assertTrue(user.check_password("brandnewpassword"))
        self.assertFalse(user.check_password("oldpassword"))


if __name__ == "__main__":
    unittest.main()
