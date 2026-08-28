from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas._validators import reject_control_chars, reject_explicit_null


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
    # Scan-Stufe B (Issue #57): pluggbares Lese-Modell. "gemini" (Default,
    # rückwärtskompatibel) | "openai" | "openrouter" | "ocr" (nur lokal).
    "scan_reader_provider": "gemini",
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "openrouter_api_key": "",
    "openrouter_model": "google/gemini-2.5-flash",
    # Lokaler Katalog-Bildcache (#43): "urls" (Default, kein Überraschungs-
    # Download) | "owned" (besessene + Wunschlisten-Karten) | "all" (ganzer
    # Katalog, ~3 GB Schätzung). Siehe services/catalog_images.py.
    "catalog_image_cache_level": "urls",
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
    "openai_api_key",
    "openrouter_api_key",
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
    # Scan-Stufe B (Issue #57)
    scan_reader_provider: str
    openai_api_key_set: bool
    openai_api_key_masked: str
    openai_model: str
    openrouter_api_key_set: bool
    openrouter_api_key_masked: str
    openrouter_model: str
    # Lokaler Katalog-Bildcache (#43) — kein Secret, GET maskiert nichts.
    catalog_image_cache_level: str


class SettingsUpdate(BaseModel):
    placeholder_images_enabled: Optional[bool] = None
    # Grenzen (#55, Panel-Fund): unbegrenzt konnte man sich die Startseite
    # dauerhaft lahmlegen — die Listen-API akzeptiert nur limit 1..5000, ein
    # gespeichertes 999999 hätte jede Kartenliste mit 422 beantwortet.
    cards_per_page: Optional[int] = Field(default=None, ge=1, le=500)
    default_sort: Optional[str] = None
    price_update_enabled: Optional[bool] = None
    price_update_hour: Optional[int] = Field(default=None, ge=0, le=23)
    price_source: Optional[str] = None
    default_language: Optional[str] = None
    default_condition: Optional[str] = None
    cardmarket_app_token: Optional[str] = None
    cardmarket_app_secret: Optional[str] = None
    cardmarket_access_token: Optional[str] = None
    cardmarket_access_secret: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    gemini_daily_limit: Optional[int] = Field(default=None, ge=0, le=1_000_000)
    # Scan-Stufe B (Issue #57)
    scan_reader_provider: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    openrouter_model: Optional[str] = None
    # #43: nur die drei Stufen — Literal liefert 422 bei jedem anderen Wert,
    # ohne einen eigenen Validator (Muster: CollectionTyp/ScanMode).
    catalog_image_cache_level: Optional[Literal["urls", "owned", "all"]] = None

    _v_ctrl = field_validator("*", mode="before")(reject_control_chars)
    # Alle Einstellungen landen als Text in der DB; ein ausdrückliches `null`
    # wurde zu "None" und sprengte danach int(...) → 500 (#55). Weglassen =
    # unverändert bleibt (Defaults werden nicht validiert).
    _v_null = field_validator("*")(reject_explicit_null)


class PasswordChange(BaseModel):
    # BEWUSST ohne Steuerzeichen-Sperre (Panel-Fund): Passwörter landen nur als
    # bcrypt-Hash in der DB — die Sperre schützt hier nichts, würde aber ein
    # bestehendes Passwort mit exotischem Zeichen unänderbar machen (Login
    # akzeptiert es ja weiterhin).
    current_password: str
    new_password: str
