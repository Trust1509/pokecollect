"""
Cardmarket API Integration (OAuth 1.0a).
Docs: https://api.cardmarket.com/ws/documentation

Seit v0.7.0 nur noch optionaler Preis-Fallback (Primärquelle: TCGdex).
Genutzt wird ausschließlich _fetch_price() aus services/pricing.py; die
Credentials kommen injiziert (DB-Settings zuerst, ENV als Fallback —
aufgelöst in pricing.get_cardmarket_credentials, Issue #12).
"""

import logging
from decimal import Decimal
from typing import NamedTuple

from requests_oauthlib import OAuth1

from app.models.card import PokemonCard

log = logging.getLogger(__name__)

CM_BASE = "https://api.cardmarket.com/ws/v2.0/output.json"


class CardmarketCredentials(NamedTuple):
    app_token: str
    app_secret: str
    access_token: str
    access_secret: str


def _oauth(creds: CardmarketCredentials) -> OAuth1:
    return OAuth1(
        creds.app_token,
        creds.app_secret,
        creds.access_token,
        creds.access_secret,
    )


def _fetch_price(card: PokemonCard, creds: CardmarketCredentials) -> Decimal | None:
    if not all(creds):
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
        resp = requests.get(search_url, params=params, auth=_oauth(creds), timeout=10)
        resp.raise_for_status()
        data = resp.json()

        products = data.get("product", [])
        if not products:
            return None

        # Erstes passendes Produkt nehmen
        product_id = products[0]["idProduct"]
        price_url = f"{CM_BASE}/products/{product_id}"
        resp2 = requests.get(price_url, auth=_oauth(creds), timeout=10)
        resp2.raise_for_status()
        product_data = resp2.json().get("product", {})
        price_info = product_data.get("priceGuide", {})
        avg30 = price_info.get("avg30")
        return Decimal(str(avg30)) if avg30 else None

    except Exception as exc:
        log.error("Cardmarket-Fehler für Karte %d (%s): %s", card.id, card.kartenname, exc)
        return None
