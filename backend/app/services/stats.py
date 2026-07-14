"""
Stats-Aggregation für die Sammlung (Issue #14).

Reine Leseaggregation über pokemon_cards — herausgelöst aus dem cards-Router,
damit der Router nur HTTP-Belange behält. Nimmt eine offene Session entgegen
(Kredo: Testbar by default).
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.card import PokemonCard
from app.schemas.card import StatsResponse


def collect_stats(db: Session) -> StatsResponse:
    """Aggregiert Sammlungs-Statistiken (Zählungen, Gesamtwert, Top-10, zuletzt)."""
    total = db.scalar(select(func.count(PokemonCard.id)))
    besessen_count = db.scalar(
        select(func.count(PokemonCard.id)).where(PokemonCard.besessen == True)
    )
    gesamtwert = db.scalar(
        select(func.sum(PokemonCard.wert_eur)).where(PokemonCard.besessen == True)
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
        sets=_count_group(PokemonCard.set_edition),
        seltenheiten=_count_group(PokemonCard.seltenheit),
        sprachen=_count_group(PokemonCard.sprache),
        top10_teuerste=top10,
        zuletzt_hinzugefuegt=recent,
    )
