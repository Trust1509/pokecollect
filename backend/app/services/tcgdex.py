"""
TCGdex API-Integration – zentrale Datenquelle für Kartendaten, Bilder und Preise.

TCGdex ist eine kostenlose, offene REST-API ohne API-Key.
Doku: https://tcgdex.dev   Basis: https://api.tcgdex.net/v2/{lang}

Ersetzt die alte pokemon.com-URL-Logik vollständig:
  - Bild-URL kommt direkt aus dem `image`-Feld (+ /{quality}.{format})
  - Set-IDs (z.B. "sv04.5") sind sprachunabhängig und stabil
  - localId = aufgedruckte Kartennummer → kein Nummern-Probing nötig
  - Preise (Cardmarket EUR) kommen im Card-Objekt gratis mit

Eigenimplementierung (MIT). Kein Code aus Drittprojekten übernommen.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

API_BASE = "https://api.tcgdex.net/v2"

# Hosts, von denen wir Bilder akzeptieren / als <img src> ausliefern.
# Schützt davor, dass über manipulierte API-/OCR-Daten eine fremde URL
# eingeschleust wird. Immer https.
ALLOWED_IMAGE_HOSTS = {"assets.tcgdex.net"}

# Serien, die NICHT übernommen werden. 'tcgp' = „Pokémon TCG Pocket": ein reines
# Handy-Spiel, dessen Karten nicht physisch existieren. PokéCollect verfolgt echte
# Karten – Pocket-Sets (~15 Sets, tausende Karten) würden sonst Katalog und
# Set-Filter zumüllen und die DB aufblähen.
EXCLUDED_SERIES = {"tcgp"}

# App-Sprachkürzel (DB-Feld `sprache`) → TCGdex-Sprachpfad.
# CN = Chinesisch (traditionell) → zh-tw, JP → ja.
LANG_MAP: dict[str, str] = {
    "DE": "de",
    "EN": "en",
    "FR": "fr",
    "ES": "es",
    "IT": "it",
    "JP": "ja",
    "CN": "zh-tw",
}

# Reihenfolge der Sprach-Fallbacks bei der Auflösung (EN ist am vollständigsten).
FALLBACK_LANGS = ["en", "de"]

DEFAULT_TIMEOUT = 10.0


# ── Pydantic-Modelle (nur relevante Felder, extra=ignore) ────────────────────

class CardMarketPricing(BaseModel):
    model_config = {"extra": "ignore", "populate_by_name": True}

    unit: Optional[str] = None
    updated: Optional[str] = None
    avg: Optional[float] = None
    low: Optional[float] = None
    trend: Optional[float] = None
    avg1: Optional[float] = None
    avg7: Optional[float] = None
    avg30: Optional[float] = None
    avg_holo: Optional[float] = Field(default=None, alias="avg-holo")
    low_holo: Optional[float] = Field(default=None, alias="low-holo")
    trend_holo: Optional[float] = Field(default=None, alias="trend-holo")
    avg1_holo: Optional[float] = Field(default=None, alias="avg1-holo")
    avg7_holo: Optional[float] = Field(default=None, alias="avg7-holo")
    avg30_holo: Optional[float] = Field(default=None, alias="avg30-holo")


class Pricing(BaseModel):
    model_config = {"extra": "ignore"}
    cardmarket: Optional[CardMarketPricing] = None


class Variants(BaseModel):
    model_config = {"extra": "ignore"}
    normal: bool = False
    reverse: bool = False
    holo: bool = False
    firstEdition: bool = False


class CardCount(BaseModel):
    model_config = {"extra": "ignore"}
    official: Optional[int] = None
    total: Optional[int] = None


class SetRef(BaseModel):
    model_config = {"extra": "ignore"}
    id: Optional[str] = None
    name: Optional[str] = None
    logo: Optional[str] = None
    symbol: Optional[str] = None
    cardCount: Optional[CardCount] = None


class TcgdexCard(BaseModel):
    """Voll-Kartendaten von /cards/{id} bzw. /sets/{setId}/{localId}."""
    model_config = {"extra": "ignore"}

    id: str
    localId: Optional[str] = None
    name: Optional[str] = None
    image: Optional[str] = None         # Basis-URL OHNE Qualität/Endung
    category: Optional[str] = None
    rarity: Optional[str] = None
    illustrator: Optional[str] = None
    dexId: Optional[list[int]] = None
    set: Optional[SetRef] = None
    variants: Optional[Variants] = None
    pricing: Optional[Pricing] = None

    @property
    def dex_id(self) -> Optional[int]:
        return self.dexId[0] if self.dexId else None


class TcgdexSetBrief(BaseModel):
    """Set aus der Liste /sets (ohne serie/symbol)."""
    model_config = {"extra": "ignore"}

    id: str
    name: Optional[str] = None
    logo: Optional[str] = None
    symbol: Optional[str] = None
    cardCount: Optional[CardCount] = None


# ── Bild-URL-Helfer ──────────────────────────────────────────────────────────

def is_allowed_image_url(url: Optional[str]) -> bool:
    """True nur für https-URLs auf einem erlaubten Bild-Host."""
    if not url:
        return False
    try:
        p = urlparse(url)
    except Exception:
        return False
    return p.scheme == "https" and p.hostname in ALLOWED_IMAGE_HOSTS


def image_url(base: Optional[str], quality: str = "high", fmt: str = "webp") -> Optional[str]:
    """
    Baut die vollständige Bild-URL aus dem `image`-Basisfeld.
    {base}/{quality}.{format}  →  …/swsh3/136/high.webp
    Gibt None zurück, wenn keine Basis vorhanden oder Host nicht erlaubt ist.
    """
    if not base:
        return None
    base = base.rstrip("/")
    if not is_allowed_image_url(base):
        log.warning("TCGdex-Bild-Host nicht erlaubt, ignoriert: %s", base)
        return None
    return f"{base}/{quality}.{fmt}"


def normalize_lang(sprache: Optional[str]) -> str:
    """App-Sprachkürzel → TCGdex-Sprachpfad. Default 'en'."""
    if not sprache:
        return "en"
    return LANG_MAP.get(sprache.upper(), "en")


# ── HTTP-Aufrufe ─────────────────────────────────────────────────────────────

async def _get_json(client: httpx.AsyncClient, path: str, params: Optional[dict] = None) -> Optional[Any]:
    try:
        resp = await client.get(path, params=params)
    except httpx.HTTPError as exc:
        log.warning("TCGdex-Request fehlgeschlagen (%s): %s", path, exc)
        return None
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        log.warning("TCGdex unerwarteter Status %s für %s", resp.status_code, path)
        return None
    try:
        return resp.json()
    except ValueError:
        log.warning("TCGdex lieferte kein JSON für %s", path)
        return None


def _client(lang: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=f"{API_BASE}/{lang}",
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "PokeCollect/0.7 (+self-hosted)"},
    )


async def get_card(card_id: str, lang: str = "en") -> Optional[TcgdexCard]:
    """Vollständige Kartendaten über die TCGdex-Karten-ID (z.B. 'swsh3-136')."""
    async with _client(lang) as client:
        data = await _get_json(client, f"/cards/{card_id}")
    if not isinstance(data, dict):
        return None
    return TcgdexCard.model_validate(data)


async def get_card_by_set(set_id: str, local_id: str, lang: str = "en") -> Optional[TcgdexCard]:
    """Karte über Set-ID + aufgedruckte Nummer (z.B. 'sv04.5', '7')."""
    async with _client(lang) as client:
        data = await _get_json(client, f"/sets/{set_id}/{local_id}")
    if not isinstance(data, dict):
        return None
    return TcgdexCard.model_validate(data)


async def fetch_card_by_set_multilang(
    set_id: str, local_id: str, primary_lang: str = "en"
) -> Optional[TcgdexCard]:
    """
    Wie get_card_by_set, probiert aber zuerst die gewünschte Sprache und dann
    die Fallback-Sprachen (Bild/Preise sind dort i.d.R. vollständiger).
    """
    langs = [primary_lang] + [l for l in FALLBACK_LANGS if l != primary_lang]
    for lang in langs:
        card = await get_card_by_set(set_id, local_id, lang)
        if card:
            return card
    return None


async def get_sets(lang: str = "en") -> list[TcgdexSetBrief]:
    """Alle Sets einer Sprache (Liste)."""
    async with _client(lang) as client:
        data = await _get_json(client, "/sets")
    if not isinstance(data, list):
        return []
    out: list[TcgdexSetBrief] = []
    for item in data:
        try:
            out.append(TcgdexSetBrief.model_validate(item))
        except Exception:
            continue
    return out


async def get_set(set_id: str, lang: str = "en") -> Optional[dict]:
    """Rohes Set-Detail-JSON (inkl. cards, serie, symbol, abbreviation)."""
    async with _client(lang) as client:
        return await _get_json(client, f"/sets/{set_id}")


async def search_cards(params: dict, lang: str = "en") -> list[dict]:
    """Kartensuche, z.B. {'name': 'Glurak'}. Liefert die rohe Trefferliste."""
    async with _client(lang) as client:
        data = await _get_json(client, "/cards", params=params)
    return data if isinstance(data, list) else []


# ── Hochsprachige Auflösung ──────────────────────────────────────────────────

def local_id_from_card_nr(karten_nr: Optional[str]) -> Optional[str]:
    """
    '007/091' → '7', '195/091' → '195', 'TG01/TG30' → 'TG01'.
    localId entspricht der aufgedruckten Nummer (führende Nullen entfernt,
    sofern rein numerisch).
    """
    if not karten_nr:
        return None
    part = karten_nr.split("/")[0].strip()
    if not part:
        return None
    if part.isdigit():
        return part.lstrip("0") or "0"
    return part  # alphanumerisch (TG-, GG-Präfixe) unverändert lassen
