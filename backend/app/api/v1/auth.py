import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from jose import jwt
from passlib.context import CryptContext

from app.config import settings
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Single-user: credentials from environment variables
# Set APP_USERNAME and APP_PASSWORD_HASH (bcrypt) in .env
_USERNAME = os.getenv("APP_USERNAME", "admin")
_PASSWORD_HASH = os.getenv(
    "APP_PASSWORD_HASH",
    # Default hash for "secret" – MUST be changed in production
    "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
)


def _get_password_hash() -> str:
    """DB-Hash has priority over env var (allows in-app password change)."""
    try:
        from app.database import SessionLocal
        from app.models.setting import AppSetting
        db = SessionLocal()
        row = db.get(AppSetting, "app_password_hash")
        db.close()
        if row and row.value:
            return row.value
    except Exception:
        pass
    return _PASSWORD_HASH


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    if data.username != _USERNAME or not pwd_context.verify(data.password, _get_password_hash()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige Anmeldedaten",
        )
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    token = jwt.encode(
        {"sub": data.username, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(data: LoginRequest):
    return login(data)
