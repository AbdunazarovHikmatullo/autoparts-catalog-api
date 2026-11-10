"""Хеширование паролей (bcrypt) и работа с JWT-токенами."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Возвращает bcrypt-хеш пароля."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Проверяет пароль по сохранённому хешу."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    """Создаёт подписанный JWT access-токен. В subject хранится id пользователя."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Декодирует токен. Бросает jwt.PyJWTError, если токен невалиден или истёк."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
