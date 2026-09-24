import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import current_app

logger = logging.getLogger("lifetracker.email")


def get_email_template(otp_code: str, purpose: str, expiry_minutes: int = 10) -> tuple[str, str, str]:
    """
    Returns (subject, plain_text, html_body) for OTP email.
    """
    if purpose == "registration":
        title = "Email Verification"
        action_text = "verifying your Life Tracker account"
        subject = f"Life Tracker - Your Verification Code is {otp_code}"
    else:
        title = "Password Reset"
        action_text = "resetting your Life Tracker password"
        subject = f"Life Tracker - Your Password Reset OTP is {otp_code}"

    plain_text = f"""
Hello,

Your verification code for {action_text} is:

{otp_code}

This code will expire in {expiry_minutes} minutes.
If you did not request this, please ignore this email.

Best regards,
The Life Tracker Team
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f4f6f9;
            margin: 0;
            padding: 24px;
            color: #1e293b;
        }}
        .email-container {{
            max-width: 520px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            border: 1px solid #e2e8f0;
        }}
        .header {{
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            padding: 28px 24px;
            text-align: center;
            color: #ffffff;
        }}
        .header h1 {{
            margin: 0;
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}
        .content {{
            padding: 32px 28px;
        }}
        .content h2 {{
            font-size: 18px;
            margin-top: 0;
            margin-bottom: 12px;
            color: #0f172a;
        }}
        .content p {{
            font-size: 14px;
            line-height: 1.6;
            color: #475569;
            margin-bottom: 20px;
        }}
        .otp-box {{
            background: #f8fafc;
            border: 2px dashed #6366f1;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
            margin: 24px 0;
        }}
        .otp-code {{
            font-size: 32px;
            font-weight: 800;
            letter-spacing: 8px;
            color: #4f46e5;
            font-family: 'Courier New', Courier, monospace;
            margin: 0;
        }}
        .expiry-note {{
            font-size: 13px;
            color: #64748b;
            text-align: center;
            margin-top: 8px;
            margin-bottom: 0;
        }}
        .footer {{
            background-color: #f8fafc;
            padding: 18px 24px;
            text-align: center;
            border-top: 1px solid #e2e8f0;
            font-size: 12px;
            color: #94a3b8;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>Life Tracker</h1>
        </div>
        <div class="content">
            <h2>{title}</h2>
            <p>Use the verification code below to proceed with {action_text}:</p>
            <div class="otp-box">
                <div class="otp-code">{otp_code}</div>
                <p class="expiry-note">&#9200; Valid for the next {expiry_minutes} minutes</p>
            </div>
            <p style="font-size: 13px; color: #64748b;">If you did not make this request, please safely disregard this email or contact support if you have concerns.</p>
        </div>
        <div class="footer">
            &copy; Life Tracker &bull; All-in-One Personal Growth System
        </div>
    </div>
</body>
</html>
"""
    return subject, plain_text, html_body


def send_otp_email(to_email: str, otp_code: str, purpose: str = "registration") -> tuple[bool, str]:
    """
    Sends OTP email to the given recipient.
    Falls back to console/logger if SMTP is not configured or in development mode.
    """
    config = current_app.config
    mail_server = config.get("MAIL_SERVER")
    mail_port = config.get("MAIL_PORT", 587)
    mail_username = config.get("MAIL_USERNAME", "")
    mail_password = config.get("MAIL_PASSWORD", "")
    mail_sender = config.get("MAIL_DEFAULT_SENDER", "noreply@lifetracker.com")
    use_tls = config.get("MAIL_USE_TLS", True)
    use_ssl = config.get("MAIL_USE_SSL", False)
    expiry_minutes = config.get("OTP_EXPIRY_MINUTES", 10)

    subject, plain_text, html_body = get_email_template(otp_code, purpose, expiry_minutes)

    # If no credentials provided, log the OTP in dev mode
    if not mail_username or not mail_password:
        dev_msg = f"""
============================================================
[LIFE TRACKER OTP - DEVELOPMENT MODE]
To: {to_email}
Purpose: {purpose}
OTP Code: >>> {otp_code} <<<
Expires in: {expiry_minutes} minutes
(Configure MAIL_USERNAME and MAIL_PASSWORD in .env for live emails)
============================================================
"""
        print(dev_msg)
        logger.info("Dev Mode OTP for %s (%s): %s", to_email, purpose, otp_code)
        return True, "OTP generated (Dev Mode logged to console)"

    from email.utils import parseaddr, formataddr

    if not mail_sender or mail_sender == "noreply@lifetracker.com":
        mail_sender = formataddr(("Life Tracker", mail_username)) if mail_username else "noreply@lifetracker.com"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = mail_sender
        msg["To"] = to_email

        part1 = MIMEText(plain_text, "plain")
        part2 = MIMEText(html_body, "html")
        msg.attach(part1)
        msg.attach(part2)

        if use_ssl:
            server = smtplib.SMTP_SSL(mail_server, mail_port, timeout=10)
        else:
            server = smtplib.SMTP(mail_server, mail_port, timeout=10)
            if use_tls:
                server.starttls()

        server.login(mail_username, mail_password)
        envelope_from = parseaddr(mail_sender)[1] or mail_username
        server.sendmail(envelope_from, [to_email], msg.as_string())
        server.quit()
        logger.info("OTP sent successfully to %s", to_email)
        return True, "OTP email sent successfully."
    except Exception as e:
        logger.error("Failed to send email via SMTP to %s: %s", to_email, str(e))
        # Fallback log so dev testing isn't blocked by network/SMTP issue
        print(f"\n[SMTP FAILED - FALLBACK OTP]: {to_email} -> {otp_code}\nError: {e}\n")
        return False, f"Could not send email: {str(e)}"
