"""
Preis-Aktualisierung über TCGdex (pricing.cardmarket, EUR).

Ersetzt die separate Cardmarket-OAuth-Integration als Primärquelle.
Die Preise kommen im Card-Objekt gratis mit – kein API-Key nötig.

Folierungs-Logik:
  - Holo-Variante besessen  → avg30-holo (Fallback auf avg30)
  - sonst (Normal/Reverse)  → avg30      (Fallback auf avg7/avg/trend)

Chinesische Karten (zh-tw) haben oft keine Preise → Feld NICHT auf 0 setzen,
sondern unverändert lassen.

Cardmarket-OAuth bleibt optionaler Fallback, falls Credentials gesetzt sind.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.config import settings
from app.database import SessionLocal
from app.models.card import PokemonCard, PreisHistorie
from app.services import tcgdex
from app.services.card_image_service import fetch_tcgdex_card, resolve_set_id
from app.services.tcgdex import CardMarketPricing

log = logging.getLogger(__name__)


def _is_holo(folierung: Optional[str]) -> bool:
    """True, wenn die besessene Variante eine echte Holo (kein Reverse) ist."""
    if not folierung:
        return False
    f = folierung.lower()
    if "reverse" in f:
        return False
    return "holo" in f


def _first(*values) -> Optional[float]:
    for v in values:
        if v is not None:
            return v
    return None


def pick_cardmarket_price(cm: CardMarketPricing, folierung: Optional[str]) -> Optional[Decimal]:
    """Wählt den passenden 30-Tage-Durchschnitt je nach Folierung."""
    if cm is None:
        return None
    if _is_holo(folierung):
        val = _first(cm.avg30_holo, cm.avg30, cm.avg7_holo, cm.avg7, cm.avg)
    else:
        val = _first(cm.avg30, cm.avg7, cm.avg, cm.trend)
    if val is None:
        return None
    return Decimal(str(val))


async def _price_for_card(card: PokemonCard) -> Optional[Decimal]:
    """Holt den Cardmarket-Preis für eine Karte über TCGdex."""
    set_id = card.set_id
    if not set_id:
        # set_id liegt evtl. noch nicht an der Karte – über das Set auflösen
        db = SessionLocal()
        try:
            set_id = resolve_set_id(db, card.set_edition)
        finally:
            db.close()
    if not set_id:
        return None
    tc = await fetch_tcgdex_card(set_id, card.karten_nr, card.sprache)
    if not tc or not tc.pricing or not tc.pricing.cardmarket:
        return None
    return pick_cardmarket_price(tc.pricing.cardmarket, card.folierung)


async def refresh_prices_for_cards(card_ids: list[int]) -> None:
    """
    Aktualisiert Preise (TCGdex Cardmarket EUR) für die angegebenen Karten,
    schreibt Preisverlauf in preis_historie. Karten ohne Preis bleiben
    unverändert (kein 0-Wert).
    """
    updated = 0
    db = SessionLocal()
    try:
        for card_id in card_ids:
            card = db.get(PokemonCard, card_id)
            if not card:
                continue
            price = await _price_for_card(card)
            if price is None:
                price = _cardmarket_oauth_fallback(card)
            if price is None:
                continue
            card.wert_eur = price
            card.wert_aktualisiert = datetime.utcnow()
            db.add(PreisHistorie(karte_id=card.id, wert_eur=price, quelle="tcgdex-cardmarket"))
            updated += 1
        db.commit()
        log.info("Preisupdate (TCGdex) abgeschlossen: %d/%d Karten aktualisiert",
                 updated, len(card_ids))
    except Exception as exc:
        log.error("Fehler beim Preisupdate: %s", exc)
        db.rollback()
    finally:
        db.close()


def _cardmarket_oauth_fallback(card: PokemonCard) -> Optional[Decimal]:
    """Optionaler Fallback auf die alte Cardmarket-OAuth-Integration."""
    if not all([
        settings.cardmarket_app_token,
        settings.cardmarket_app_secret,
        settings.cardmarket_access_token,
        settings.cardmarket_access_secret,
    ]):
        return None
    try:
        from app.services.cardmarket import _fetch_price
        return _fetch_price(card)
    except Exception as exc:
        log.debug("Cardmarket-Fallback fehlgeschlagen für Karte %s: %s", card.id, exc)
        return None
