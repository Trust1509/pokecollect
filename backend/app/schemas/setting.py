from typing import Optional
from pydantic import BaseModel


DEFAULTS: dict[str, str] = {
    "placeholder_images_enabled": "true",
    "cards_per_page": "48",
    "default_sort": "pokedex_nr",
    "price_update_enabled": "true",
    "price_update_hour": "3",
    "price_source": "30d_avg",
    "default_language": "DE",
    "default_condition": "",
    "cardmarket_app_token": "",
    "cardmarket_app_secret": "",
    "cardmarket_access_token": "",
    "cardmarket_access_secret": "",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "gemini_daily_limit": "0",   # 0 = unbekannt/kein Limit anzeigen
}

# Secrets verlassen das Backend nie im Klartext (Issue #1): die Response
# liefert je Secret nur noch <key>_set (bool) + <key>_masked ("•••• " +
# letzte 4 Zeichen). Ändern geht weiter über PUT mit dem Klartext-Wert.
SECRET_KEYS: tuple[str, ...] = (
    "cardmarket_app_token",
    "cardmarket_app_secret",
    "cardmarket_access_token",
    "cardmarket_access_secret",
    "gemini_api_key",
)


class SettingsResponse(BaseModel):
    placeholder_images_enabled: bool
    cards_per_page: int
    default_sort: str
    price_update_enabled: bool
    price_update_hour: int
    price_source: str
    default_language: str
    default_condition: str
    cardmarket_app_token_set: bool
    cardmarket_app_token_masked: str
    cardmarket_app_secret_set: bool
    cardmarket_app_secret_masked: str
    cardmarket_access_token_set: bool
    cardmarket_access_token_masked: str
    cardmarket_access_secret_set: bool
    cardmarket_access_secret_masked: str
    gemini_api_key_set: bool
    gemini_api_key_masked: str
    gemini_model: str
    gemini_daily_limit: int


class SettingsUpdate(BaseModel):
    placeholder_images_enabled: Optional[bool] = None
    cards_per_page: Optional[int] = None
    default_sort: Optional[str] = None
    price_update_enabled: Optional[bool] = None
    price_update_hour: Optional[int] = None
    price_source: Optional[str] = None
    default_language: Optional[str] = None
    default_condition: Optional[str] = None
    cardmarket_app_token: Optional[str] = None
    cardmarket_app_secret: Optional[str] = None
    cardmarket_access_token: Optional[str] = None
    cardmarket_access_secret: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    gemini_daily_limit: Optional[int] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
