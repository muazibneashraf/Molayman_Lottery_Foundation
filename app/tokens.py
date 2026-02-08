from __future__ import annotations

from typing import Any

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


def _serializer() -> URLSafeTimedSerializer:
    secret_key = current_app.config.get("SECRET_KEY")
    return URLSafeTimedSerializer(secret_key)


def generate_token(purpose: str, email: str) -> str:
    s = _serializer()
    return s.dumps({"purpose": purpose, "email": email}, salt=f"token:{purpose}")


def verify_token(purpose: str, token: str, max_age_seconds: int) -> dict[str, Any] | None:
    s = _serializer()
    try:
        data = s.loads(token, salt=f"token:{purpose}", max_age=max_age_seconds)
    except (SignatureExpired, BadSignature):
        return None

    if not isinstance(data, dict):
        return None
    if data.get("purpose") != purpose:
        return None
    if not data.get("email"):
        return None

    return data
