from __future__ import annotations

from flask import current_app
from flask_mail import Message

from .extensions import mail


def mail_is_configured() -> bool:
    # Minimal check. If missing, we'll fall back to console-only behavior.
    return bool(current_app.config.get("MAIL_SERVER")) and bool(current_app.config.get("MAIL_DEFAULT_SENDER"))


def send_email(to: str, subject: str, text: str, html: str | None = None) -> bool:
    if not mail_is_configured():
        current_app.logger.warning("Email not configured. Would send to=%s subject=%s\n%s", to, subject, text)
        return False

    msg = Message(subject=subject, recipients=[to], body=text, html=html)
    mail.send(msg)
    return True
