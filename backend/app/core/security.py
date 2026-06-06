from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.errors import AppError


def _to_bytes(password: str) -> bytes:
    # bcrypt only considers the first 72 bytes; encode and truncate to stay within
    # that limit for very long inputs rather than raising.
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_to_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {"sub": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise AppError.unauthorized("Invalid or expired authentication token") from exc
