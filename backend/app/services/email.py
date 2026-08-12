"""Dev-friendly email sender. Logs to console; optional SMTP when configured."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("sunny.email")


def send_email(to: str, subject: str, body: str) -> dict:
    """Send email via SMTP if configured; always log in development."""
    logger.info("email to=%s subject=%s\n%s", to, subject, body)
    if not settings.smtp_host:
        return {"ok": True, "mode": "log", "to": to}
    msg = EmailMessage()
    msg["From"] = settings.smtp_from or "noreply@studiosunny.com"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_tls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
    return {"ok": True, "mode": "smtp", "to": to}
