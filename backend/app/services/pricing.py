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
  - Reverse OHNE echte Holo-Variante der Karte → ebenfalls *-holo-Kette
    (Cardmarkets -holo-Felder bepreisen die Foil-Variante = dort die Reverse,
    v1.7.3); Reverse MIT echter Holo-Variante + Normal → Basisfeld

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
from app.services import fx
from app.services.card_image_service import fetch_tcgdex_card, resolve_set_id
from app.services.catalog_lookup import catalog_row_for
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
    *,
    hat_echtes_holo: bool = True,
) -> Optional[Decimal]:
    """
    Wählt den Preis je nach Folierung und Preisquelle:
      - "30d_avg": 30-Tage-Durchschnitt (bisherige Logik)
      - "daily":   Tagespreis avg1 (TCGdex-Feld `avg1` bzw. `avg1-holo`),
                   Fallback auf die 30d-Kette, wenn kein Tagespreis vorliegt

    Reverse-Holo (v1.7.3, empirisch verifiziert): Cardmarkets `-holo`-Felder
    bepreisen die FOIL-Variante der Karte. Existiert KEINE echte Holo-Variante
    (`hat_echtes_holo=False`, aus TCGdex `variants.holo`), ist die Foil-Variante
    die Reverse — dann gilt für Reverse-Folierungen die `-holo`-Kette (z. B.
    0,08 € statt 0,02 €). Mit echter Holo-Variante bleibt Reverse bei der
    Basis-Kette (der Reverse-Preis ist dort nicht separat verfügbar).
    """
    if cm is None:
        return None
    daily = normalize_price_source(price_source) == "daily"
    ist_reverse = bool(folierung) and "reverse" in folierung.lower()
    holo_kette = _is_holo(folierung) or (ist_reverse and not hat_echtes_holo)
    if holo_kette:
        # Panel-Fixes v1.7.3: (a) trend(_holo) als letzte Rettung anhängen —
        # sonst endete eine Karte mit NUR trend-Daten preislos, obwohl die
        # Basis-Kette sie früher bepreiste; (b) im daily-Modus stehen ALLE
        # Foil-Werte vor dem Normal-Tagespreis avg1 — sonst gewänne der
        # Normal-Tagespreis (0,02 €) über den Foil-30d-Wert (0,08 €) und der
        # Reverse-Fix wäre für daily-Nutzer wirkungslos.
        chain_30d = (cm.avg30_holo, cm.avg30, cm.avg7_holo, cm.avg7, cm.avg,
                     cm.trend_holo, cm.trend)
        if daily:
            val = _first(cm.avg1_holo, cm.avg30_holo, cm.avg7_holo,
                         cm.avg1, cm.avg30, cm.avg7, cm.avg,
                         cm.trend_holo, cm.trend)
        else:
            val = _first(*chain_30d)
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
    # Reverse-Semantik: ohne echte Holo-Variante sind die -holo-Felder der
    # Reverse-Preis (v1.7.3). FEHLT das variants-Objekt ganz → konservativ wie
    # bisher (Basis-Kette); ein vorhandenes variants ohne holo=True gilt als
    # „kein echtes Holo" (TCGdex liefert die Flags vollständig mit).
    hat_holo = bool(tc.variants.holo) if tc.variants else True
    return pick_cardmarket_price(tc.pricing.cardmarket, card.folierung, price_source,
                                 hat_echtes_holo=hat_holo), True


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


def _hat_muster_preisprodukt(card: PokemonCard) -> bool:
    """
    Pokéball-/Masterball-Muster haben EIGENE TCGplayer-Produkte (#63).
    RIEGEL (Panel-Fund): Muster zählt nur bei folierter Grundform — ein stale
    „muster" an einer Normal-Karte (UI-Wechsel zurück auf Normal) darf den
    Wert nicht auf den Muster-Preis reißen (12,78 € statt 0,02 €).
    """
    if "holo" not in (card.folierung or "").lower():
        return False
    m = (card.muster or "").lower()
    return "masterball" in m or "pokeball" in m or "pokéball" in m


def _usd_from_catalog(db: Session, card: PokemonCard) -> Optional[Decimal]:
    """
    TCGplayer-$-Marktpreis aus dem Katalog-Cache, passend zur (Folierung,
    Muster)-Kombination der Karte (#63):
      - Muster Pokéball/Masterball → Preis des Muster-PRODUKTS; KEIN Fallback
        auf andere Spalten (materiell anderes Produkt, $0.60/$12.78 vs $0.26).
      - echtes Holo → Holofoil-Subtyp; kein Fallback auf Normal (falsche Variante).
      - Reverse → Reverse-Subtyp, ersatzweise Normal (dokumentierte Näherung —
        JP-Produkte führen oft keinen Reverse-Subtyp).
      - Normal → Basispreis.
    None ohne Katalog-Referenz/-Preis oder wenn der Datenstand älter als
    _MAX_USD_STAND_TAGE ist. Case-toleranter Lookup (v1.7.3).
    """
    row = catalog_row_for(db, card.tcgdex_card_id)
    if row is None:
        return None
    if not _usd_stand_frisch(row.price_usd_updated):
        return None
    # Muster nur bei folierter Grundform honorieren (Riegel wie in
    # _hat_muster_preisprodukt — stale muster an Normal-Karten ignorieren).
    f = (card.folierung or "").lower()
    m = (card.muster or "").lower() if "holo" in f else ""
    if "masterball" in m:
        val = row.price_usd_masterball
    elif "pokeball" in m or "pokéball" in m:
        val = row.price_usd_pokeball
    elif _is_holo(card.folierung):
        val = row.price_usd_holo
    elif "reverse" in f:
        val = row.price_usd_reverse if row.price_usd_reverse is not None else row.price_usd
    else:
        val = row.price_usd
    return Decimal(str(val)) if val is not None else None


async def refresh_prices_for_cards(db: Session, card_ids: list[int]) -> None:
    """
    Aktualisiert Preise für die angegebenen Karten und schreibt Preisverlauf in
    preis_historie. Preis-Kette (Owner-Entscheide 2026-08-11/12):
      0. Muster-Karten (Pokéball/Masterball, #63) ZUERST über ihr eigenes
         TCGplayer-Produkt ($ × EZB-Kurs) — Cardmarket kennt keine Muster-
         Preise, der Basis-€ läge um ein Vielfaches daneben ($12.78 vs 0,08 €).
         Ohne Muster-$ fällt die Karte in die normale Kette (Näherung).
      1. Cardmarket-€ über TCGdex (Folierungs-bewusst, v1.7.3)
      2. Cardmarket-OAuth-Fallback (optional, wie bisher)
      3. TCGplayer-$ aus dem Katalog-Cache, varianten-bewusst (#63: Holo-/
         Reverse-Subtyp bzw. Basis), mit EZB-Tageskurs in € umgerechnet
         (Quelle „tcgplayer-usd@<kurs>"). Greift NICHT, wenn die €-Quelle nur
         gerade ausgefallen ist.
    Karten ganz ohne Preis bleiben unverändert (kein 0-Wert). Session kommt
    injiziert (Kredo „testbar by default"); Hintergrund-Aufrufer nutzen
    database.run_with_session. Gemeinsame Routine für Cron UND /prices/refresh.
    """
    updated = 0
    usd_rate: Optional[Decimal] = None
    usd_rate_geholt = False  # Kurs nur einmal je Lauf holen (nicht je Karte)

    async def usd_in_eur(card: PokemonCard) -> Optional[Decimal]:
        """Varianten-$ der Karte in € (Kurs je Lauf gecacht); None wenn nicht
        bepreisbar (kein $/kein Kurs/außerhalb des Wertebereichs)."""
        nonlocal usd_rate, usd_rate_geholt
        usd = _usd_from_catalog(db, card)
        # 0/negativ = Datenfehler in der Quelle, kein Preis (nie 0 schreiben)
        if usd is None or usd <= 0:
            return None
        if not usd_rate_geholt:
            usd_rate = await fx.usd_eur_rate()
            usd_rate_geholt = True
        if usd_rate is None:
            return None
        kandidat = convert_usd_eur(usd, usd_rate)
        if not _wert_plausibel(kandidat):
            log.warning("Karte %s: umgerechneter $-Preis %s außerhalb des "
                        "Wertebereichs – übersprungen.", card.id, kandidat)
            return None
        return kandidat

    try:
        price_source = get_price_source(db)
        for card_id in card_ids:
            card = db.get(PokemonCard, card_id)
            if not card:
                continue
            quelle = "tcgdex-cardmarket"
            price: Optional[Decimal] = None
            eur_geprueft = True
            # Kette 0: Muster-Produktpreis hat Vorrang vor Cardmarket-Basis-€.
            if _hat_muster_preisprodukt(card):
                price = await usd_in_eur(card)
                if price is not None:
                    # Kurs im Verlauf dokumentieren → $-Basis bleibt auditierbar
                    quelle = f"tcgplayer-usd@{usd_rate}"
            if price is None:
                price, eur_geprueft = await _price_for_card(db, card, price_source)
            if price is None:
                price = _cardmarket_oauth_fallback(db, card)
                if price is not None:
                    quelle = "cardmarket-oauth"
            # $-Fallback NUR wenn die €-Quelle wirklich geprüft wurde (nicht
            # bei TCGdex-Ausfall). Varianten-Wahl (inkl. echtem Holo über den
            # Holofoil-Subtyp) übernimmt _usd_from_catalog (#63).
            if price is None and eur_geprueft:
                price = await usd_in_eur(card)
                if price is not None:
                    quelle = f"tcgplayer-usd@{usd_rate}"
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
