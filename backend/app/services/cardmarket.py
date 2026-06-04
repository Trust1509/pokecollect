"""
Cardmarket API Integration (OAuth 1.0a).
Docs: https://api.cardmarket.com/ws/documentation
"""

import logging
from datetime import datetime
from decimal import Decimal

import httpx
from requests_oauthlib import OAuth1

from app.config import settings
from app.database import SessionLocal
from app.models.card import PokemonCard, PreisHistorie

log = logging.getLogger(__name__)

CM_BASE = "https://api.cardmarket.com/ws/v2.0/output.json"


def _oauth() -> OAuth1:
    return OAuth1(
        settings.cardmarket_app_token,
        settings.cardmarket_app_secret,
        settings.cardmarket_access_token,
        settings.cardmarket_access_secret,
    )


def _fetch_price(card: PokemonCard) -> Decimal | None:
    if not all([
        settings.cardmarket_app_token,
        settings.cardmarket_app_secret,
        settings.cardmarket_access_token,
        settings.cardmarket_access_secret,
    ]):
        log.warning("Cardmarket-Credentials nicht konfiguriert")
        return None

    # Suche nach Produkt
    search_url = f"{CM_BASE}/products/find"
    params = {
        "search": card.kartenname,
        "exact": 0,
        "idGame": 1,  # Pokémon TCG
        "idLanguage": 5 if card.sprache == "DE" else 1,
    }

    try:
        import requests
        resp = requests.get(search_url, params=params, auth=_oauth(), timeout=10)
        resp.raise_for_status()
        data = resp.json()

        products = data.get("product", [])
        if not products:
            return None

        # Erstes passendes Produkt nehmen
        product_id = products[0]["idProduct"]
        price_url = f"{CM_BASE}/products/{product_id}"
        resp2 = requests.get(price_url, auth=_oauth(), timeout=10)
        resp2.raise_for_status()
        product_data = resp2.json().get("product", {})
        price_info = product_data.get("priceGuide", {})
        avg30 = price_info.get("avg30")
        return Decimal(str(avg30)) if avg30 else None

    except Exception as exc:
        log.error("Cardmarket-Fehler für Karte %d (%s): %s", card.id, card.kartenname, exc)
        return None


def refresh_prices_for_cards(card_ids: list[int]):
    db = SessionLocal()
    try:
        for card_id in card_ids:
            card = db.get(PokemonCard, card_id)
            if not card:
                continue
            price = _fetch_price(card)
            if price is not None:
                card.wert_eur = price
                card.wert_aktualisiert = datetime.utcnow()
                history = PreisHistorie(
                    karte_id=card.id,
                    wert_eur=price,
                    quelle="cardmarket",
                )
                db.add(history)
        db.commit()
        log.info("Preisupdate abgeschlossen für %d Karten", len(card_ids))
    except Exception as exc:
        log.error("Fehler beim Preisupdate: %s", exc)
        db.rollback()
    finally:
        db.close()
