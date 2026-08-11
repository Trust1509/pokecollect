"""
Preis-Aktualisierung über TCGdex (pricing.cardmarket, EUR).

Ersetzt die separate Cardmarket-OAuth-Integration als Primärquelle.
Die Preise kommen im Card-Objekt gratis mit – kein API-Key nötig.

Preisquelle (Setting `price_source`, Issue #12):
  - "30d_avg" (Default): 30-Tage-Durchschnitt (avg30, bisherige Logik)
  - "daily":             Tagespreis (avg1 = 1-Tages-Durchschnitt von TCGdex),
                         Fallback auf die avg30-Kette, wenn avg1 leer ist

Folierungs-Logik:
  - Holo-Variante besessen  → *-holo-Feld (Fallback auf Nicht-Holo)
  - sonst (Normal/Reverse)  → Basisfeld (Fallback auf avg7/avg/trend)

Chinesische Karten (zh-tw) haben oft keine Preise → Feld NICHT auf 0 setzen,
sondern unverändert lassen.

Cardmarket-OAuth bleibt optionaler Fallback; die vier Credentials kommen aus
den AppSettings (DB, Settings-Seite) und erst als Fallback aus der ENV.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.card import PokemonCard, PreisHistorie
from app.models.setting import AppSetting
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services import fx
from app.services.card_image_service import fetch_tcgdex_card, resolve_set_id
from app.services.cardmarket import CardmarketCredentials
from app.services.tcgdex import CardMarketPricing

log = logging.getLogger(__name__)

CARDMARKET_CREDENTIAL_KEYS = (
    "cardmarket_app_token",
    "cardmarket_app_secret",
    "cardmarket_access_token",
    "cardmarket_access_secret",
)


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


def normalize_price_source(value: Optional[str]) -> str:
    """
    Normalisiert das Setting `price_source` auf die zwei gültigen Werte.
    "current" ist der Alt-Wert des früheren UI-Selects und zählt als "daily"
    (Feldtyp-Wechsel: Alt-Daten in allen Konsumenten abfangen).
    """
    if value and value.strip() in ("daily", "current"):
        return "daily"
    return "30d_avg"


def pick_cardmarket_price(
    cm: CardMarketPricing,
    folierung: Optional[str],
    price_source: str = "30d_avg",
) -> Optional[Decimal]:
    """
    Wählt den Preis je nach Folierung und Preisquelle:
      - "30d_avg": 30-Tage-Durchschnitt (bisherige Logik)
      - "daily":   Tagespreis avg1 (TCGdex-Feld `avg1` bzw. `avg1-holo`),
                   Fallback auf die 30d-Kette, wenn kein Tagespreis vorliegt
    """
    if cm is None:
        return None
    daily = normalize_price_source(price_source) == "daily"
    if _is_holo(folierung):
        chain_30d = (cm.avg30_holo, cm.avg30, cm.avg7_holo, cm.avg7, cm.avg)
        val = _first(cm.avg1_holo, cm.avg1, *chain_30d) if daily else _first(*chain_30d)
    else:
        chain_30d = (cm.avg30, cm.avg7, cm.avg, cm.trend)
        val = _first(cm.avg1, *chain_30d) if daily else _first(*chain_30d)
    if val is None:
        return None
    return Decimal(str(val))


def _setting_value(db: Session, key: str) -> str:
    row = db.get(AppSetting, key)
    return (row.value or "").strip() if row else ""


def get_price_source(db: Session) -> str:
    """Liest das Setting `price_source` aus der DB (Default "30d_avg")."""
    return normalize_price_source(_setting_value(db, "price_source"))


def get_cardmarket_credentials(db: Session) -> Optional[CardmarketCredentials]:
    """
    Löst die vier Cardmarket-OAuth-Credentials auf: je Feld zuerst das
    AppSetting aus der DB (Settings-Seite), erst dann die ENV (.env/Config).
    None, wenn nicht alle vier Werte vorhanden sind.
    """
    values = [
        _setting_value(db, key) or (getattr(settings, key, "") or "").strip()
        for key in CARDMARKET_CREDENTIAL_KEYS
    ]
    if not all(values):
        return None
    return CardmarketCredentials(*values)


async def _price_for_card(
    db: Session, card: PokemonCard, price_source: str = "30d_avg"
) -> tuple[Optional[Decimal], bool]:
    """
    Holt den Cardmarket-Preis für eine Karte über TCGdex.

    Rückgabe (preis, eur_geprueft): eur_geprueft=False heißt, die €-Quelle war
    NICHT erreichbar (TCGdex-Ausfall/kaputte Referenz) — der Aufrufer darf dann
    nicht auf den $-Fallback ausweichen, sonst würde ein transienter Ausfall
    die ganze Sammlung still auf $-Basis umbewerten (Panel-Fund). Eine Karte
    ohne auflösbares Set gilt als geprüft: dort GIBT es keine €-Quelle.
    """
    set_id = card.set_id
    if not set_id:
        # set_id liegt evtl. noch nicht an der Karte – über das Set auflösen
        set_id = resolve_set_id(db, card.set_edition)
    if not set_id:
        return None, True
    tc = await fetch_tcgdex_card(set_id, card.karten_nr, card.sprache)
    if tc is None:
        return None, False   # Ausfall/nicht auffindbar → NICHT auf $ ausweichen
    if not tc.pricing or not tc.pricing.cardmarket:
        return None, True    # Karte da, aber ohne Cardmarket-€ (typisch JP)
    return pick_cardmarket_price(tc.pricing.cardmarket, card.folierung, price_source), True


def convert_usd_eur(usd: Decimal, rate: Decimal) -> Decimal:
    """$ → € mit Tageskurs, kaufmännisch auf Cent gerundet (pur, unit-testbar).

    Decimal(str(…)) wie in pick_cardmarket_price: schützt vor stiller
    float-Binärdarstellung, falls ein Aufrufer je einen float durchreicht.
    """
    return (Decimal(str(usd)) * Decimal(str(rate))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)


# Zulässiger Wertebereich für wert_eur (Numeric(8,2)). Preise außerhalb sind
# Datenfehler (0/negativ) oder würden den Commit des GANZEN Laufs sprengen
# (Überlauf → Rollback aller Karten) — beides überspringen (Panel-Fund).
_WERT_MIN = Decimal("0.01")
_WERT_MAX = Decimal("999999.99")


def _wert_plausibel(price: Decimal) -> bool:
    return _WERT_MIN <= price <= _WERT_MAX


# Maximalalter des gecachten $-Preises für den Fallback. JP-Preise frischt der
# tägliche Sync auf; West-$ entsteht bislang nur beim Einmal-Enrich und kann
# beliebig alt sein — ein Monate alter Preis darf nicht als heutiger Wert in
# den Verlauf (Panel-Fund). Unparsebare/fehlende Stände gelten als zu alt.
_MAX_USD_STAND_TAGE = 30


def _usd_stand_frisch(stand: Optional[str]) -> bool:
    if not stand:
        return False
    try:
        dt = datetime.fromisoformat(stand.replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days <= _MAX_USD_STAND_TAGE


def _usd_from_catalog(db: Session, card: PokemonCard) -> Optional[Decimal]:
    """
    TCGplayer-$-Marktpreis aus dem Katalog-Cache (Epic #41: West aus TCGdex,
    JP aus TCGCSV; im täglichen Sync gefüllt). None ohne Katalog-Referenz/-Preis
    oder wenn der Datenstand älter als _MAX_USD_STAND_TAGE ist.
    """
    if not card.tcgdex_card_id:
        return None
    row = db.get(TcgdexCatalog, card.tcgdex_card_id)
    if row is None or row.price_usd is None:
        return None
    if not _usd_stand_frisch(row.price_usd_updated):
        return None
    return Decimal(str(row.price_usd))


async def refresh_prices_for_cards(db: Session, card_ids: list[int]) -> None:
    """
    Aktualisiert Preise für die angegebenen Karten und schreibt Preisverlauf in
    preis_historie. Preis-Kette (Owner-Entscheid 2026-08-11, universell):
      1. Cardmarket-€ über TCGdex (wie bisher)
      2. Cardmarket-OAuth-Fallback (optional, wie bisher)
      3. TCGplayer-$ aus dem Katalog-Cache, mit EZB-Tageskurs in € umgerechnet
         (Quelle „tcgplayer-usd@<kurs>") — gibt v. a. japanischen Karten einen
         Wert, die Cardmarket gar nicht führt. Greift NICHT, wenn die €-Quelle
         nur gerade ausgefallen ist, und nicht für echte Holo-Varianten.
    Karten ganz ohne Preis bleiben unverändert (kein 0-Wert). Session kommt
    injiziert (Kredo „testbar by default"); Hintergrund-Aufrufer nutzen
    database.run_with_session. Gemeinsame Routine für Cron UND /prices/refresh.
    """
    updated = 0
    usd_rate: Optional[Decimal] = None
    usd_rate_geholt = False  # Kurs nur einmal je Lauf holen (nicht je Karte)
    try:
        price_source = get_price_source(db)
        for card_id in card_ids:
            card = db.get(PokemonCard, card_id)
            if not card:
                continue
            quelle = "tcgdex-cardmarket"
            price, eur_geprueft = await _price_for_card(db, card, price_source)
            if price is None:
                price = _cardmarket_oauth_fallback(db, card)
                if price is not None:
                    quelle = "cardmarket-oauth"
            # $-Fallback NUR wenn die €-Quelle wirklich geprüft wurde (nicht bei
            # TCGdex-Ausfall) und die Karte keine echte Holo ist — der gecachte $
            # ist der Normal-Varianten-Preis (Reverse zählt wie im €-Pfad als
            # Normal; Holo-$ je Variante = Folge-Issue).
            if price is None and eur_geprueft and not _is_holo(card.folierung):
                usd = _usd_from_catalog(db, card)
                # 0/negativ = Datenfehler in der Quelle, kein Preis (nie 0 schreiben)
                if usd is not None and usd > 0:
                    if not usd_rate_geholt:
                        usd_rate = await fx.usd_eur_rate()
                        usd_rate_geholt = True
                    if usd_rate is not None:
                        kandidat = convert_usd_eur(usd, usd_rate)
                        if _wert_plausibel(kandidat):
                            price = kandidat
                            # Kurs im Verlauf dokumentieren → $-Basis bleibt
                            # auditierbar (z. B. "tcgplayer-usd@0.8666")
                            quelle = f"tcgplayer-usd@{usd_rate}"
                        else:
                            log.warning("Karte %s: umgerechneter $-Preis %s außerhalb "
                                        "des Wertebereichs – übersprungen.", card.id, kandidat)
            if price is None:
                continue
            card.wert_eur = price
            card.wert_aktualisiert = datetime.utcnow()
            db.add(PreisHistorie(karte_id=card.id, wert_eur=price, quelle=quelle))
            updated += 1
        db.commit()
        log.info("Preisupdate (TCGdex, Quelle %s) abgeschlossen: %d/%d Karten aktualisiert",
                 price_source, updated, len(card_ids))
    except Exception as exc:
        log.error("Fehler beim Preisupdate: %s", exc)
        db.rollback()


def _cardmarket_oauth_fallback(db: Session, card: PokemonCard) -> Optional[Decimal]:
    """Optionaler Fallback auf die alte Cardmarket-OAuth-Integration."""
    creds = get_cardmarket_credentials(db)
    if creds is None:
        return None
    try:
        from app.services.cardmarket import _fetch_price
        return _fetch_price(card, creds)
    except Exception as exc:
        log.debug("Cardmarket-Fallback fehlgeschlagen für Karte %s: %s", card.id, exc)
        return None
