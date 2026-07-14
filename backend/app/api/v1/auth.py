import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from jose import jwt
from passlib.context import CryptContext

from app.config import settings
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Single-User: Zugangsdaten aus Env (APP_USERNAME + APP_PASSWORD_HASH, bcrypt).
# Es gibt KEINEN Default-Hash mehr — ohne konfiguriertes Passwort verweigert
# die App den Start (main.py::_ensure_password_configured, Issue #1).
_USERNAME = os.getenv("APP_USERNAME", "admin")


def _get_password_hash() -> str:
    """DB-Hash hat Vorrang vor der Env-Var (In-App-Passwortwechsel)."""
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
    return os.getenv("APP_PASSWORD_HASH", "")


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    stored_hash = _get_password_hash()
    if not stored_hash or data.username != _USERNAME or not pwd_context.verify(data.password, stored_hash):
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

