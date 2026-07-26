"""
Einstellungs-Zugriff für Services (DRY): einzelne Werte mit Fallback auf die
DEFAULTS, ohne dass ein Service den Settings-Router importieren muss.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.setting import AppSetting
from app.schemas.setting import DEFAULTS


def get_setting(db: Session, key: str) -> str:
    """Wert einer Einstellung; leere/fehlende Werte fallen auf DEFAULTS zurück."""
    row = db.get(AppSetting, key)
    if row and row.value not in (None, ""):
        return row.value
    return DEFAULTS.get(key, "")
