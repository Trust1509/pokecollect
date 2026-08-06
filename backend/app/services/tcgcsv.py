"""
TCGCSV-Client (Epic #41): kostenloser TCGplayer-Spiegel (tcgcsv.com, kein Key).

Nur lesend. Wird v. a. genutzt, um japanische Kartenbilder zu ergänzen, die
TCGdex (noch) fehlen — TCGplayer führt „Pokemon Japan" als eigene Kategorie (85)
mit CDN-Bildern auch für brandneue Sets. Etikette: ~250 ms zwischen Requests
(tcgcsv-FAQ). Kein Gesamt-Archiv → wir iterieren Gruppen/Produkte inkrementell.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlparse

import httpx

log = logging.getLogger(__name__)

BASE = "https://tcgcsv.com/tcgplayer"
CATEGORY_POKEMON = 3        # englische Karten + Sealed
CATEGORY_POKEMON_JP = 85    # japanische Karten + Sealed

# TCGplayer-Bild-CDN (in die Allowlist von tcgdex.is_allowed_image_url aufnehmen).
IMAGE_HOST = "tcgplayer-cdn.tcgplayer.com"

_TIMEOUT = httpx.Timeout(30.0)
_ETIQUETTE_SECONDS = 0.25   # tcgcsv-FAQ: ~250 ms zwischen Requests
# tcgcsv/CloudFront weist den py-httpx-Default-UA mit 401 ab → eigenen, höflichen
# User-Agent setzen (identifiziert die App, jeder echte UA wird akzeptiert).
_HEADERS = {"User-Agent": "PokeCollect/1.0 (self-hosted collection app)"}


async def _get_json(path: str, *, sleep=asyncio.sleep) -> Optional[object]:
    """Ein GET auf tcgcsv (mit Etikette-Pause davor). None bei Fehler/kein JSON."""
    await sleep(_ETIQUETTE_SECONDS)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as client:
            resp = await client.get(f"{BASE}/{path}")
        if resp.status_code != 200:
            log.warning("tcgcsv %s → Status %s", path, resp.status_code)
            return None
        return resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("tcgcsv %s fehlgeschlagen: %s", path, exc)
        return None


def _results(data: object) -> list[dict]:
    """tcgcsv liefert {success, results:[…]} — die Ergebnisliste rausziehen."""
    if isinstance(data, dict):
        r = data.get("results")
        return [x for x in r if isinstance(x, dict)] if isinstance(r, list) else []
    return [x for x in data if isinstance(x, dict)] if isinstance(data, list) else []


async def get_groups(category: int, *, sleep=asyncio.sleep) -> list[dict]:
    """Alle Gruppen (≈ Sets) einer Kategorie: {groupId, name, …}."""
    return _results(await _get_json(f"{category}/groups", sleep=sleep))


async def get_products(category: int, group_id: int, *, sleep=asyncio.sleep) -> list[dict]:
    """Produkte einer Gruppe: Karten UND Sealed. {productId, name, imageUrl, extendedData}."""
    return _results(await _get_json(f"{category}/{group_id}/products", sleep=sleep))


# ── Helfer fürs Matching (Set-Code + Nummer) ─────────────────────────────────

def set_code_from_group(name: Optional[str]) -> Optional[str]:
    """
    TCGplayer-Gruppenname → aufgedruckter Set-Code. Für JP-Sets steht er vorn,
    z. B. „M3: Nihil Zero" → „M3", „m1S: Mega Symphonia" → „M1S". Ohne Doppelpunkt
    None (dann kein sicheres Set-Match).
    """
    if not isinstance(name, str) or ":" not in name:
        return None
    code = name.split(":", 1)[0].strip().upper()
    return code or None


def _ext(product: dict, field: str) -> Optional[str]:
    """Wert aus TCGplayers extendedData-Liste [{name,value},…] lesen."""
    for e in product.get("extendedData") or []:
        if isinstance(e, dict) and e.get("name") == field:
            v = e.get("value")
            return str(v).strip() if v is not None else None
    return None


def product_number(product: dict) -> Optional[str]:
    """
    Normierte Sammelnummer eines Produkts für den Abgleich: der Zähler ohne
    führende Nullen, z. B. „009/080" → „9". None, wenn keine numerische Nummer
    (Sealed-Produkte haben keine).
    """
    raw = _ext(product, "Number")
    if not raw:
        return None
    head = raw.split("/", 1)[0].strip()
    m = re.match(r"^0*(\d+)$", head)
    return m.group(1) if m else None


def hires_image_url(product: dict) -> Optional[str]:
    """
    Hochauflösende Bild-URL eines Produkts (`_200w` → `_in_1000x1000`). Nur wenn
    die URL auf das erwartete TCGplayer-CDN zeigt (Absicherung).
    """
    url = product.get("imageUrl")
    if not isinstance(url, str):
        return None
    # EXAKTE Host-Prüfung (kein Substring!) — sonst würde
    # https://tcgplayer-cdn.tcgplayer.com.evil.example/… akzeptiert.
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme != "https" or parsed.hostname != IMAGE_HOST:
        return None
    return url.replace("_200w", "_in_1000x1000")


def is_card_product(product: dict) -> bool:
    """Kartenprodukt (hat eine Sammelnummer) vs. Sealed (keine)."""
    return product_number(product) is not None
