from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas._validators import reject_control_chars, reject_explicit_null

# Fester Typ-Katalog (Issue #35). Interne ASCII-tauglichen Werte = zugleich
# Anzeige-Label (kurz gehalten); das Frontend darf eigene Label-Maps ergänzen.
SEALED_TYP_VALUES = [
    "Booster", "Display", "ETB", "Tin", "Blister", "Bundle", "Sonstiges",
]

# Zustand eines Sealed-Produkts — echte Umlaute (CLAUDE.md).
SEALED_ZUSTAND_VALUES = ["Versiegelt", "Geöffnet", "Beschädigt"]

# Grenzen (Härtung #38): set_code ist Teil des zusammengesetzten Primär-
# schlüssels → begrenzte Länge/Anzahl, sonst btree-Limit/500. Großschreibung
# wird normalisiert, damit der Filter case-insensitiv trifft.
MAX_SET_CODE_LEN = 32
MAX_SET_CODES = 50
# Obergrenze der ROH-Liste (vor Dedup/Leerfilter): MAX_SET_CODES begrenzt nur die
# eindeutigen Codes und greift erst NACH der Schleife — ohne Roh-Cap würde eine
# Riesenliste (z. B. 100k Duplikate) erst voll verarbeitet. Großzügig über
# MAX_SET_CODES, damit legitime Duplikate/Leerwerte weiter still dedupliziert
# werden, aber Missbrauch früh (auf Feldebene) abprallt. (#38, Codex-Review)
MAX_SET_CODES_RAW = 200
MAX_NAME_LEN = 200
# Numeric(8,2) → max. 999.999,99; ohne Grenze → Postgres-Overflow/500.
# Negative Beträge würden die Statistik still verfälschen → ge=0.
MONEY_FIELD = Field(default=None, ge=0, max_digits=8, decimal_places=2)


def _validate_name(v: Optional[str]) -> Optional[str]:
    """Name darf nicht nur aus Leerzeichen bestehen (#38). None bleibt None
    (Update: unverändert; explizites null fängt der Router mit 422 ab)."""
    if v is not None and not v.strip():
        raise ValueError("Name darf nicht leer sein")
    return v


def _validate_typ(v: Optional[str]) -> Optional[str]:
    if v is not None and v not in SEALED_TYP_VALUES:
        raise ValueError(f"Ungültiger Typ. Erlaubt: {', '.join(SEALED_TYP_VALUES)}")
    return v


def _validate_zustand(v: Optional[str]) -> Optional[str]:
    if v is not None and v not in SEALED_ZUSTAND_VALUES:
        raise ValueError(f"Ungültiger Zustand. Erlaubt: {', '.join(SEALED_ZUSTAND_VALUES)}")
    return v


def _normalize_set_codes(v: Optional[list[str]]) -> Optional[list[str]]:
    """Trimmen, Großschreibung, dedup, Leere raus, Länge/Anzahl begrenzen (#38).
    None bleibt None (Update: Zuordnung unverändert)."""
    if v is None:
        return None
    out: list[str] = []
    seen: set[str] = set()
    for code in v:
        s = (code or "").strip().upper()
        if not s:
            continue
        if len(s) > MAX_SET_CODE_LEN:
            raise ValueError(f"Set-Kürzel zu lang (max. {MAX_SET_CODE_LEN} Zeichen): {s[:40]}")
        if s not in seen:
            seen.add(s)
            out.append(s)
    if len(out) > MAX_SET_CODES:
        raise ValueError(f"Zu viele Sets (max. {MAX_SET_CODES})")
    return out


class SealedProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_NAME_LEN)
    typ: Optional[str] = None
    zustand: Optional[str] = None
    kaufpreis_eur: Optional[Decimal] = MONEY_FIELD
    kaufdatum: Optional[date] = None
    wert_eur: Optional[Decimal] = MONEY_FIELD
    # Sealed-Katalog-Verknüpfung (#46): TCGplayer-productId. Gesetzt →
    # Auto-Wert + CDN-Bild; None = Freitext-Produkt (manuell bewertet).
    tcgplayer_product_id: Optional[int] = None
    notizen: Optional[str] = None
    # n:m-Set-Zuordnung (0..N Set-Kürzel). Leer erlaubt (Bundles ohne Bezug).
    # max_length kappt die ROH-Liste (Missbrauchsschutz, #38); die inhaltliche
    # Grenze (≤ MAX_SET_CODES eindeutige) prüft _normalize_set_codes.
    set_codes: list[str] = Field(default=[], max_length=MAX_SET_CODES_RAW)

    _v_ctrl = field_validator("*", mode="before")(reject_control_chars)
    _v_name = field_validator("name")(_validate_name)
    _v_typ = field_validator("typ")(_validate_typ)
    _v_zustand = field_validator("zustand")(_validate_zustand)
    _v_sets = field_validator("set_codes")(_normalize_set_codes)


class SealedProductCreate(SealedProductBase):
    pass


class SealedProductUpdate(BaseModel):
    # name nicht gesetzt = unverändert; wenn gesetzt, dann nicht leer. Ein
    # explizites null fängt min_length NICHT ab → der Router weist es mit 422 ab.
    name: Optional[str] = Field(default=None, min_length=1, max_length=MAX_NAME_LEN)
    typ: Optional[str] = None
    zustand: Optional[str] = None
    kaufpreis_eur: Optional[Decimal] = MONEY_FIELD
    kaufdatum: Optional[date] = None
    wert_eur: Optional[Decimal] = MONEY_FIELD
    # Weggelassen = unverändert (exclude_unset); explizit null ODER 0 =
    # Verknüpfung lösen; id = (neu) verknüpfen.
    tcgplayer_product_id: Optional[int] = None
    notizen: Optional[str] = None
    # None = Zuordnung unverändert lassen; [] = alle Sets entfernen.
    set_codes: Optional[list[str]] = Field(default=None, max_length=MAX_SET_CODES_RAW)

    _v_ctrl = field_validator("*", mode="before")(reject_control_chars)
    _v_name = field_validator("name")(_validate_name)
    _v_typ = field_validator("typ")(_validate_typ)
    _v_zustand = field_validator("zustand")(_validate_zustand)
    _v_sets = field_validator("set_codes")(_normalize_set_codes)


class SealedProductResponse(BaseModel):
    id: int
    name: str
    typ: Optional[str] = None
    zustand: Optional[str] = None
    kaufpreis_eur: Optional[Decimal] = None
    kaufdatum: Optional[date] = None
    wert_eur: Optional[Decimal] = None
    notizen: Optional[str] = None
    set_codes: list[str] = []
    bild_pfad: Optional[str] = None
    bild_thumbnail_pfad: Optional[str] = None
    # Sealed-Katalog (#46): Verknüpfung + CDN-Bild + Stand des Auto-Werts
    tcgplayer_product_id: Optional[int] = None
    bild_url: Optional[str] = None
    wert_aktualisiert: Optional[datetime] = None
    hinzugefuegt_am: Optional[datetime] = None
    # Unrealisierter G/V = wert_eur − kaufpreis_eur (nur wenn BEIDE gesetzt).
    unrealisierter_gv_eur: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class SealedEnumsResponse(BaseModel):
    typ: list[str]
    zustand: list[str]


class SealedCatalogItem(BaseModel):
    """Ein Eintrag des TCGplayer-Sealed-Katalogs (#46, Picker-Quelle)."""
    product_id: int
    region: str
    set_code: Optional[str] = None
    name: str
    image_url: Optional[str] = None
    price_usd: Optional[float] = None
    price_usd_updated: Optional[str] = None

    model_config = {"from_attributes": True}
