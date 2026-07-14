import os
from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.setting import AppSetting
from app.schemas.setting import DEFAULTS, PasswordChange, SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_all(db: Session) -> dict[str, str]:
    rows = {r.key: r.value for r in db.query(AppSetting).all()}
    return {k: rows.get(k, v) for k, v in DEFAULTS.items()}


def _set(db: Session, key: str, value: str):
    row = db.get(AppSetting, key)
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))


def _to_response(raw: dict[str, str]) -> SettingsResponse:
    return SettingsResponse(
        placeholder_images_enabled=raw["placeholder_images_enabled"] == "true",
        cards_per_page=int(raw["cards_per_page"] or 48),
        default_sort=raw["default_sort"] or "pokedex_nr",
        price_update_enabled=raw["price_update_enabled"] == "true",
        price_update_hour=int(raw["price_update_hour"] or 3),
        price_source=raw["price_source"] or "30d_avg",
        default_language=raw["default_language"] or "DE",
        default_condition=raw["default_condition"] or "",
        cardmarket_app_token=raw["cardmarket_app_token"] or "",
        cardmarket_app_secret=raw["cardmarket_app_secret"] or "",
        cardmarket_access_token=raw["cardmarket_access_token"] or "",
        cardmarket_access_secret=raw["cardmarket_access_secret"] or "",
        gemini_api_key=raw["gemini_api_key"] or "",
        gemini_model=raw["gemini_model"] or "gemini-2.5-flash",
        gemini_daily_limit=int(raw["gemini_daily_limit"] or 0),
    )


@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    return _to_response(_get_all(db))


@router.put("", response_model=SettingsResponse)
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db)):
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        _set(db, key, str(value).lower() if isinstance(value, bool) else str(value))
    db.commit()
    return _to_response(_get_all(db))


@router.post("/change-password")
def change_password(data: PasswordChange, db: Session = Depends(get_db)):
    stored_hash_row = db.get(AppSetting, "app_password_hash")
    current_hash = (
        stored_hash_row.value if stored_hash_row
        else os.getenv("APP_PASSWORD_HASH", "")
    )
    if not current_hash or not pwd_context.verify(data.current_password, current_hash):
        raise HTTPException(status_code=400, detail="Aktuelles Passwort falsch")
    new_hash = pwd_context.hash(data.new_password)
    _set(db, "app_password_hash", new_hash)
    db.commit()
    return {"detail": "Passwort geändert"}
