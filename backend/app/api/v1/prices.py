from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db, run_with_session
from app.models.card import PokemonCard, PreisHistorie
from app.schemas.card import PreisHistorieResponse
from app.services.pricing import refresh_prices_for_cards, refresh_sealed_prices

router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("/refresh")
async def trigger_price_refresh(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    ids = list(db.scalars(
        select(PokemonCard.id).where(PokemonCard.besessen == True)  # noqa: E712
    ).all())
    # Eigene Session für den Hintergrund-Job — die Request-Session ist beim
    # Ausführen der BackgroundTask bereits geschlossen.
    background_tasks.add_task(run_with_session, refresh_prices_for_cards, ids)
    # Sealed: Auto-Wert für katalog-verknüpfte Produkte (#46).
    background_tasks.add_task(run_with_session, refresh_sealed_prices)
    return {"message": f"Preisupdate für {len(ids)} Karten gestartet"}


@router.get("/history/{card_id}", response_model=list[PreisHistorieResponse])
def get_price_history(
    card_id: int,
    limit: int = 90,
    db: Session = Depends(get_db),
):
    if not db.get(PokemonCard, card_id):
        raise HTTPException(status_code=404, detail="Karte nicht gefunden")
    rows = db.scalars(
        select(PreisHistorie)
        .where(PreisHistorie.karte_id == card_id)
        # id als Tiebreak (gleicher Zeitstempel) — sonst könnten Chart und
        # Wert-Label auf verschiedene Einträge zeigen (Panel-Fund v1.8.2).
        .order_by(PreisHistorie.erfasst_am.desc(), PreisHistorie.id.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))
