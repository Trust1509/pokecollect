"""
USD→EUR-Tageskurs für den $-Preis-Fallback (Epic #41).

Japanische Karten (und einzelne West-Karten) haben keinen Cardmarket-€-Preis,
aber einen TCGplayer-$-Marktpreis im Katalog-Cache. Für `wert_eur` und den
Preisverlauf rechnen wir $ mit dem EZB-Tageskurs in € um (Owner-Entscheid
2026-08-11: Umrechnung statt Nur-Anzeige, für ALLE Karten ohne €).

Quellen (beide frei, ohne Key):
  1. frankfurter.dev  — EZB-Referenzkurs (primär)
  2. open.er-api.com  — Fallback, falls frankfurter nicht erreichbar

Der Kurs wird prozess-lokal 12 h gecacht; schlagen beide Quellen fehl, dient
der letzte bekannte Kurs als Notnagel (Alter egal — besser ein gestriger Kurs
als gar kein Preis). Ohne jeden Kurs liefert `usd_eur_rate()` None → der
Aufrufer überspringt die Karte (wie bisher: nie 0 schreiben).
"""

from __future__ import annotations

import asyncio
import logging
import time
from decimal import Decimal
from typing import Optional

import httpx

log = logging.getLogger(__name__)

_FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest?base=USD&symbols=EUR"
_ERAPI_URL = "https://open.er-api.com/v6/latest/USD"
_CACHE_TTL = 12 * 3600.0

# (monotonic_ts, rate) — frischer Cache; _last_good bleibt als Notnagel stehen,
# verfällt aber nach 7 Tagen: €-Werte aus einem wochenalten Kurs wären stille
# Falschdaten (Panel-Fund). Das Lock verhindert, dass parallele Läufe (Cron +
# Hand-Refresh) bei kaltem Cache doppelt fetchen oder divergieren.
_cache: Optional[tuple[float, Decimal]] = None
_last_good: Optional[tuple[float, Decimal]] = None
_LAST_GOOD_MAX_ALTER = 7 * 24 * 3600.0
_lock = asyncio.Lock()


def _parse_rate(raw) -> Optional[Decimal]:
    """Zieht die EUR-Rate aus einer der beiden Antwortformen; None wenn unbrauchbar."""
    try:
        rates = raw.get("rates") or {}
        val = rates.get("EUR")
        if val is None:
            return None
        rate = Decimal(str(val))
        # Plausibilitätsfenster: USD/EUR bewegt sich seit Jahrzehnten zwischen
        # ~0.5 und ~2 — alles außerhalb ist ein Datenfehler, kein Kurs.
        if not (Decimal("0.3") < rate < Decimal("3")):
            log.warning("FX-Kurs unplausibel (%s) – verworfen.", rate)
            return None
        return rate
    except (AttributeError, TypeError, ValueError, ArithmeticError):
        return None


async def usd_eur_rate(*, transport=None) -> Optional[Decimal]:
    """
    USD→EUR-Kurs (z. B. 0.8666), 12 h gecacht. None nur, wenn beide Quellen
    scheitern UND noch nie ein Kurs geholt wurde. `transport` für Tests.

    Lock: bei kaltem Cache holt genau EIN Aufrufer den Kurs; Parallele warten
    und bedienen sich danach aus dem Cache (kein Doppel-Fetch, keine Divergenz).
    """
    global _cache, _last_good
    if _cache and (time.monotonic() - _cache[0]) < _CACHE_TTL:
        return _cache[1]

    async with _lock:
        # Doppelt prüfen: ein parallel wartender Aufrufer findet den Kurs jetzt.
        now = time.monotonic()
        if _cache and (now - _cache[0]) < _CACHE_TTL:
            return _cache[1]

        for url in (_FRANKFURTER_URL, _ERAPI_URL):
            try:
                async with httpx.AsyncClient(timeout=15.0, transport=transport) as client:
                    resp = await client.get(url, headers={"User-Agent": "PokeCollect/1.0"})
                if resp.status_code != 200:
                    log.info("FX-Quelle %s: Status %s", url, resp.status_code)
                    continue
                # parse_float=Decimal: Kurs exakt übernehmen statt über float
                # (json.loads-kwargs via httpx durchgereicht; Panel-Fund).
                rate = _parse_rate(resp.json(parse_float=Decimal))
                if rate is not None:
                    _cache = (now, rate)
                    _last_good = (now, rate)
                    return rate
            except Exception as exc:
                log.info("FX-Quelle %s nicht erreichbar: %s", url, type(exc).__name__)

        if _last_good is not None and (now - _last_good[0]) < _LAST_GOOD_MAX_ALTER:
            log.warning("FX-Quellen nicht erreichbar – nutze letzten bekannten Kurs %s.",
                        _last_good[1])
            return _last_good[1]
        log.warning("Kein (frischer) USD→EUR-Kurs verfügbar – $-Preis-Fallback übersprungen.")
        return None


def reset_cache() -> None:
    """Nur für Tests: Cache + Notnagel leeren."""
    global _cache, _last_good
    _cache = None
    _last_good = None
