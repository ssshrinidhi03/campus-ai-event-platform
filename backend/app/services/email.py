"""
Email Service Module
Provides configurable email delivery for verification, password reset, and notifications.
Supports multiple backends: console (development), SMTP (production), and mock (testing).
"""

import logging
import smtplib
import ssl
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailBackend(ABC):
    """Abstract base class for email backends."""

    @abstractmethod
    def send(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """Send an email. Returns True on success, False on failure."""
        pass


class ConsoleEmailBackend(EmailBackend):
    """Development backend that logs emails to console."""

    def send(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        logger.info(f"[EMAIL] To: {to_email}")
        logger.info(f"[EMAIL] Subject: {subject}")
        logger.info(f"[EMAIL] Body:\n{body}")
        if html_body:
            logger.info(f"[EMAIL] HTML Body:\n{html_body}")
        return True


class SMTPEmailBackend(EmailBackend):
    """Production SMTP email backend."""

    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.use_tls = settings.SMTP_USE_TLS
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME

    def send(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        if not all([self.host, self.port, self.username, self.password, self.from_email]):
            logger.error("SMTP configuration incomplete. Cannot send email.")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            msg.attach(MIMEText(body, "plain"))
            if html_body:
                msg.attach(MIMEText(html_body, "html"))

            context = ssl.create_default_context()
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False


class MockEmailBackend(EmailBackend):
    """Testing backend that simulates email sending without actually sending."""

    def __init__(self):
        self.sent_emails = []

    def send(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        self.sent_emails.append({
            "to": to_email,
            "subject": subject,
            "body": body,
            "html_body": html_body,
        })
        logger.debug(f"[MOCK EMAIL] To: {to_email}, Subject: {subject}")
        return True


def get_email_backend() -> EmailBackend:
    """Get the configured email backend based on environment."""
    backend_type = getattr(settings, "EMAIL_BACKEND", "console").lower()

    if backend_type == "smtp":
        return SMTPEmailBackend()
    elif backend_type == "mock":
        return MockEmailBackend()
    else:
        return ConsoleEmailBackend()


# Email templates
VERIFICATION_EMAIL_SUBJECT = "Verify your CampusConnect account"
VERIFICATION_EMAIL_TEXT = """Welcome to CampusConnect!

Please verify your email address by clicking the link below:

{verification_link}

This link will expire in 24 hours.

If you didn't create an account, you can safely ignore this email.

---
CampusConnect Team
"""

VERIFICATION_EMAIL_HTML = """<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #4A6CF7;">Welcome to CampusConnect!</h2>
        <p>Please verify your email address by clicking the button below:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verification_link}" 
               style="background-color: #4A6CF7; color: white; padding: 12px 30px; 
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Verify Email Address
            </a>
        </div>
        <p style="color: #666; font-size: 14px;">This link will expire in 24 hours.</p>
        <p style="color: #666; font-size: 14px;">If you didn't create an account, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">CampusConnect Team</p>
    </div>
</body>
</html>
"""

RESET_EMAIL_SUBJECT = "Reset your CampusConnect password"
RESET_EMAIL_TEXT = """Password Reset Request

You requested a password reset for your CampusConnect account.

Click the link below to reset your password:

{reset_link}

This link will expire in 1 hour.

If you didn't request this, please ignore this email and your password will remain unchanged.

---
CampusConnect Team
"""

RESET_EMAIL_HTML = """<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #4A6CF7;">Password Reset Request</h2>
        <p>You requested a password reset for your CampusConnect account.</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}" 
               style="background-color: #4A6CF7; color: white; padding: 12px 30px; 
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Reset Password
            </a>
        </div>
        <p style="color: #666; font-size: 14px;">This link will expire in 1 hour.</p>
        <p style="color: #666; font-size: 14px;">If you didn't request this, please ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">CampusConnect Team</p>
    </div>
</body>
</html>
"""


def send_verification_email(email: str, verification_link: str) -> bool:
    """Send email verification link."""
    backend = get_email_backend()
    subject = VERIFICATION_EMAIL_SUBJECT
    body = VERIFICATION_EMAIL_TEXT.format(verification_link=verification_link)
    html_body = VERIFICATION_EMAIL_HTML.format(verification_link=verification_link)
    return backend.send(email, subject, body, html_body)


def send_password_reset_email(email: str, reset_link: str) -> bool:
    """Send password reset link."""
    backend = get_email_backend()
    subject = RESET_EMAIL_SUBJECT
    body = RESET_EMAIL_TEXT.format(reset_link=reset_link)
    html_body = RESET_EMAIL_HTML.format(reset_link=reset_link)
    return backend.send(email, subject, body, html_body)