from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pokemon_set import PokemonSet
from app.schemas.pokemon_set import PokemonSetCreate, PokemonSetResponse
from app.services.set_sync import sync_sets

router = APIRouter(prefix="/sets", tags=["sets"])


@router.get("", response_model=list[PokemonSetResponse])
def list_sets(db: Session = Depends(get_db)):
    return db.scalars(select(PokemonSet).order_by(PokemonSet.code)).all()


@router.post("/sync")
async def trigger_set_sync():
    """
    Reichert die Set-Tabelle mit TCGdex-Daten an (/en/sets + /de/sets).
    Liefert die aufgelösten set_id-Werte sowie Sets ohne Zuordnung zurück
    (zur Verifikation der ptcgo_code-Brücke).
    """
    return await sync_sets()


@router.post("", response_model=PokemonSetResponse, status_code=201)
def create_set(data: PokemonSetCreate, db: Session = Depends(get_db)):
    existing = db.get(PokemonSet, data.code)
    if existing:
        raise HTTPException(status_code=409, detail=f"Set '{data.code}' existiert bereits")
    s = PokemonSet(**data.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

