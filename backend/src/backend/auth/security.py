from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from pwdlib import PasswordHash

from backend.config import settings

ALGORITHM = "HS256"

TokenType = Literal["access", "refresh"]

password_hash = PasswordHash.recommended()


class InvalidToken(Exception):
    pass


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def _secret(token_type: TokenType) -> str:
    if token_type == "access":
        return settings.jwt_access_secret
    return settings.jwt_refresh_secret


def _lifetime(token_type: TokenType) -> timedelta:
    if token_type == "access":
        return timedelta(minutes=settings.access_token_expire_minutes)
    return timedelta(days=settings.refresh_token_expire_days)


def create_token(user_id: str, token_type: TokenType) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "type": token_type,
        "iat": now,
        "exp": now + _lifetime(token_type),
    }
    return jwt.encode(payload, _secret(token_type), algorithm=ALGORITHM)


def create_access_token(user_id: str) -> str:
    return create_token(user_id, "access")


def create_refresh_token(user_id: str) -> str:
    return create_token(user_id, "refresh")


def decode_token(token: str, token_type: TokenType) -> str:
    """Return the user id in `token`, or raise InvalidToken."""
    try:
        payload = jwt.decode(
            token,
            _secret(token_type),
            algorithms=[ALGORITHM],
            options={"require": ["sub", "type", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc
    if payload["type"] != token_type:
        raise InvalidToken(f"expected a {token_type} token")
    return payload["sub"]
