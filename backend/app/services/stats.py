"""
Stats-Aggregation für die Sammlung (Issue #14).

Reine Leseaggregation über pokemon_cards — herausgelöst aus dem cards-Router,
damit der Router nur HTTP-Belange behält. Nimmt eine offene Session entgegen
(Kredo: Testbar by default).
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.card import PokemonCard
from app.models.sealed import SealedProduct
from app.schemas.card import StatsResponse


def _sum_or_none(*values: Optional[Decimal]) -> Optional[Decimal]:
    """Summe mehrerer Beträge; None (kein Wert) zählt als 0. Sind ALLE None,
    bleibt das Ergebnis None (dann gibt es schlicht nichts anzuzeigen)."""
    present = [v for v in values if v is not None]
    if not present:
        return None
    return sum(present, Decimal("0"))


def collect_stats(db: Session) -> StatsResponse:
    """Aggregiert Sammlungs-Statistiken (Zählungen, Gesamtwert, Top-10, zuletzt)."""
    total = db.scalar(select(func.count(PokemonCard.id)))
    besessen_count = db.scalar(
        select(func.count(PokemonCard.id)).where(PokemonCard.besessen == True)
    )
    gesamtwert = db.scalar(
        select(func.sum(PokemonCard.wert_eur)).where(PokemonCard.besessen == True)
    )
    # Persönlicher Einstand: Summe der Kaufpreise besessener Karten (#26).
    einstand = db.scalar(
        select(func.sum(PokemonCard.kaufpreis_eur)).where(
            PokemonCard.besessen == True,
            PokemonCard.kaufpreis_eur.isnot(None),
        )
    )
    # Unrealisierter G/V: nur Karten, bei denen BEIDE Werte gesetzt sind —
    # so bleibt die Aggregatzahl deckungsgleich mit der Karten-Definition
    # (wert_eur − kaufpreis_eur). Kein Verkauf-/realisiert-Konzept.
    unrealisierter_gv = db.scalar(
        select(func.sum(PokemonCard.wert_eur - PokemonCard.kaufpreis_eur)).where(
            PokemonCard.besessen == True,
            PokemonCard.wert_eur.isnot(None),
            PokemonCard.kaufpreis_eur.isnot(None),
        )
    )

    # ── Sealed-Produkte (#35) ────────────────────────────────────────────────
    # Analog zu Karten: Sealed-Wert (Σ wert_eur), Einstand (Σ kaufpreis_eur) und
    # unrealisierter G/V (Σ wert − kaufpreis, nur wo BEIDE gesetzt). Getrennt
    # ausgewiesen; kombiniert_* addiert Karten + Sealed.
    sealed_anzahl = db.scalar(select(func.count(SealedProduct.id))) or 0
    sealed_wert = db.scalar(select(func.sum(SealedProduct.wert_eur)))
    sealed_einstand = db.scalar(
        select(func.sum(SealedProduct.kaufpreis_eur)).where(
            SealedProduct.kaufpreis_eur.isnot(None)
        )
    )
    sealed_gv = db.scalar(
        select(func.sum(SealedProduct.wert_eur - SealedProduct.kaufpreis_eur)).where(
            SealedProduct.wert_eur.isnot(None),
            SealedProduct.kaufpreis_eur.isnot(None),
        )
    )

    def _count_group(col):
        rows = db.execute(
            select(col, func.count(PokemonCard.id))
            .where(col.isnot(None))
            .group_by(col)
            .order_by(func.count(PokemonCard.id).desc())
        ).all()
        return {r[0]: r[1] for r in rows}

    top10 = db.scalars(
        select(PokemonCard)
        .where(PokemonCard.wert_eur.isnot(None))
        .order_by(PokemonCard.wert_eur.desc())
        .limit(10)
    ).all()

    recent = db.scalars(
        select(PokemonCard)
        .order_by(PokemonCard.hinzugefuegt_am.desc())
        .limit(10)
    ).all()

    return StatsResponse(
        gesamt=total,
        besessen=besessen_count,
        nicht_besessen=total - besessen_count,
        gesamtwert_eur=gesamtwert,
        gesamt_einstand_eur=einstand,
        unrealisierter_gv_eur=unrealisierter_gv,
        sealed_anzahl=sealed_anzahl,
        sealed_wert_eur=sealed_wert,
        sealed_einstand_eur=sealed_einstand,
        sealed_unrealisierter_gv_eur=sealed_gv,
        kombiniert_wert_eur=_sum_or_none(gesamtwert, sealed_wert),
        kombiniert_einstand_eur=_sum_or_none(einstand, sealed_einstand),
        kombiniert_unrealisierter_gv_eur=_sum_or_none(unrealisierter_gv, sealed_gv),
        sets=_count_group(PokemonCard.set_edition),
        seltenheiten=_count_group(PokemonCard.seltenheit),
        sprachen=_count_group(PokemonCard.sprache),
        top10_teuerste=top10,
        zuletzt_hinzugefuegt=recent,
    )
