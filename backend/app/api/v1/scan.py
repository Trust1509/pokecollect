"""
Karten-Scan – gemeinsame API für Web (Webcam) UND Android.

POST /api/v1/scan          Bild + Modus → Kandidaten (Hybrid: Gemini, sonst OCR)
POST /api/v1/scan/commit   bestätigte Karten ablegen (Pokédex oder Sammlung)
GET  /api/v1/scan/status   welche Engine aktiv ist (für die UI)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.card import PokemonCard
from app.models.collection import Collection, collection_cards
from app.schemas.scan import (
    ScanCommitRequest, ScanCommitResponse, ScanMode, ScanResponse,
)
from app.services.scan import gemini, ocr
from app.services.scan.resolver import resolve_reads
from app.services.tcgdex import is_allowed_image_url

log = logging.getLogger(__name__)
router = APIRouter(prefix="/scan", tags=["scan"])

_MAX_BYTES = 12 * 1024 * 1024  # 12 MB


@router.get("/status")
def scan_status():
    """Welche Erkennungs-Engine ist aktiv? (Hybrid-Anzeige im UI)"""
    return {
        "gemini": gemini.is_enabled(),
        "ocr": ocr.is_enabled(),
        "active": "gemini" if gemini.is_enabled() else ("ocr" if ocr.is_enabled() else "none"),
    }


@router.post("", response_model=ScanResponse)
async def scan(
    file: UploadFile = File(...),
    mode: ScanMode = Form("single"),
    rows: int = Form(0),
    cols: int = Form(0),
    default_language: str = Form("DE"),
    db: Session = Depends(get_db),
):
    """
    Erkennt Karten auf einem Foto.
    - mode=single  : eine Karte
    - mode=multi   : mehrere lose Karten (Gemini empfohlen)
    - mode=binder  : ganze Mappenseite; rows×cols = Raster (z.B. 3×3)
    """
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Leeres Bild")
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="Bild zu groß (max. 12 MB)")

    mime = file.content_type or "image/jpeg"

    engine = "none"
    reads = None
    # Hybrid: Gemini bevorzugt (stark bei Binder/Multi), sonst lokale OCR.
    if gemini.is_enabled():
        reads = await gemini.extract(data, mime_type=mime)
        if reads is not None:
            engine = "gemini"
    if reads is None:
        reads = ocr.extract(data, mode=mode, rows=rows, cols=cols)
        engine = "ocr"

    candidates = await resolve_reads(db, reads or [], default_lang=default_language)
    return ScanResponse(engine=engine, mode=mode, candidates=candidates)


@router.post("/commit", response_model=ScanCommitResponse)
def scan_commit(payload: ScanCommitRequest, db: Session = Depends(get_db)):
    """
    Legt die bestätigten Karten an (besessen=True), weist sie optional einer
    Sammlung zu (mit Binder-Slot) und setzt optional den Pokédex-Vertreter.
    """
    collection: Collection | None = None
    if payload.target == "collection":
        if not payload.collection_id:
            raise HTTPException(status_code=400, detail="collection_id fehlt")
        collection = db.get(Collection, payload.collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Sammlung nicht gefunden")

    created_ids: list[int] = []
    for item in payload.items:
        card = PokemonCard(
            kartenname=item.kartenname,
            pokedex_nr=item.pokedex_nr,
            englischer_name=item.englischer_name,
            set_edition=item.set_edition,
            karten_nr=item.karten_nr,
            seltenheit=item.seltenheit,
            kartenversion=item.kartenversion,
            folierung=item.folierung,
            sprache=item.sprache or "DE",
            zustand=item.zustand,
            notizen=item.notizen,
            besessen=True,
            tcgdex_card_id=item.tcgdex_card_id,
            set_id=item.set_id,
            dex_id=item.dex_id,
            bild_karte_url=item.bild_karte_url if is_allowed_image_url(item.bild_karte_url) else None,
        )
        db.add(card)
        db.flush()  # ID

        # Pokédex-Vertreter setzen (exklusiv pro pokedex_nr)
        if payload.set_im_pokedex and card.pokedex_nr:
            existing = db.scalar(
                select(func.count(PokemonCard.id))
                .where(PokemonCard.pokedex_nr == card.pokedex_nr)
                .where(PokemonCard.im_pokedex == True)
                .where(PokemonCard.id != card.id)
            )
            if existing == 0:
                card.im_pokedex = True

        # Sammlung + Binder-Slot
        if collection:
            db.execute(
                collection_cards.insert().values(
                    collection_id=collection.id,
                    card_id=card.id,
                    position=item.position,
                )
            )

        created_ids.append(card.id)

    db.commit()
    return ScanCommitResponse(created=len(created_ids), card_ids=created_ids)
