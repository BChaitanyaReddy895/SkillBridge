from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from src.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(*, user_id: int, role: str) -> str:
    now = _utcnow()
    exp = now + timedelta(hours=settings.jwt_expires_hours)
    payload: dict[str, Any] = {
        "type": "access",
        "user_id": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_monitoring_token(*, user_id: int, role: str) -> str:
    now = _utcnow()
    exp = now + timedelta(hours=settings.monitoring_jwt_expires_hours)
    payload: dict[str, Any] = {
        "type": "monitoring",
        "scope": "read:monitoring",
        "user_id": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "aud": "monitoring",
    }
    return jwt.encode(payload, settings.monitoring_jwt_secret, algorithm=settings.jwt_algorithm)

