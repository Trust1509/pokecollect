from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.card import PokemonCard, PreisHistorie
from app.schemas.card import PreisHistorieResponse
from app.services.cardmarket import refresh_prices_for_cards

router = APIRouter(prefix="/prices", tags=["prices"])


@router.post("/refresh")
async def trigger_price_refresh(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    cards = db.scalars(
        select(PokemonCard).where(PokemonCard.besessen == True)
    ).all()
    background_tasks.add_task(refresh_prices_for_cards, [c.id for c in cards])
    return {"message": f"Preisupdate für {len(cards)} Karten gestartet"}


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
        .order_by(PreisHistorie.erfasst_am.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))
