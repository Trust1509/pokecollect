from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

# Fester Typ-Katalog (Issue #35). Interne ASCII-tauglichen Werte = zugleich
# Anzeige-Label (kurz gehalten); das Frontend darf eigene Label-Maps ergänzen.
SEALED_TYP_VALUES = [
    "Booster", "Display", "ETB", "Tin", "Blister", "Bundle", "Sonstiges",
]

# Zustand eines Sealed-Produkts — echte Umlaute (CLAUDE.md).
SEALED_ZUSTAND_VALUES = ["Versiegelt", "Geöffnet", "Beschädigt"]


class SealedProductBase(BaseModel):
    name: str
    typ: Optional[str] = None
    zustand: Optional[str] = None
    kaufpreis_eur: Optional[Decimal] = None
    kaufdatum: Optional[date] = None
    wert_eur: Optional[Decimal] = None
    notizen: Optional[str] = None
    # n:m-Set-Zuordnung (0..N Set-Kürzel). Leer erlaubt (Bundles ohne Bezug).
    set_codes: list[str] = []


class SealedProductCreate(SealedProductBase):
    pass


class SealedProductUpdate(BaseModel):
    name: Optional[str] = None
    typ: Optional[str] = None
    zustand: Optional[str] = None
    kaufpreis_eur: Optional[Decimal] = None
    kaufdatum: Optional[date] = None
    wert_eur: Optional[Decimal] = None
    notizen: Optional[str] = None
    # None = Zuordnung unverändert lassen; [] = alle Sets entfernen.
    set_codes: Optional[list[str]] = None


class SealedProductResponse(SealedProductBase):
    id: int
    bild_pfad: Optional[str] = None
    bild_thumbnail_pfad: Optional[str] = None
    hinzugefuegt_am: Optional[datetime] = None
    # Unrealisierter G/V = wert_eur − kaufpreis_eur (nur wenn BEIDE gesetzt).
    unrealisierter_gv_eur: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class SealedEnumsResponse(BaseModel):
    typ: list[str]
    zustand: list[str]
