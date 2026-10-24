from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings


_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_settings = get_settings()


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd.verify(password, password_hash)


def create_access_token(claims: dict[str, Any], expires_minutes: int | None = None) -> str:
    to_encode = claims.copy()
    exp = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or _settings.jwt_exp_minutes)
    to_encode.update({"exp": exp})
    return jwt.encode(to_encode, _settings.jwt_secret, algorithm=_settings.jwt_alg)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _settings.jwt_secret, algorithms=[_settings.jwt_alg])
    except JWTError as e:
        raise ValueError(f"Token invalido: {e}")
