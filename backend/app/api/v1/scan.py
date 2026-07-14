"""
Karten-Scan (Web: Webcam/Foto-Upload).

POST /api/v1/scan          Bild + Modus → Kandidaten (Hybrid: Gemini, sonst OCR)
POST /api/v1/scan/commit   bestätigte Karten ablegen (Pokédex oder Sammlung)
GET  /api/v1/scan/status   welche Engine aktiv ist (für die UI)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.card import PokemonCard
from app.models.collection import Collection, collection_cards
from app.models.gemini_usage import GeminiUsage
from app.models.setting import AppSetting
from app.schemas.scan import (
    ScanCandidate, ScanCommitRequest, ScanCommitResponse, ScanMode,
    ScanRawRead, ScanResponse,
)
from app.services.card_creation import create_owned_card
from app.services.scan import gemini, ocr
from app.services.scan.resolver import resolve_one, resolve_reads
from app.services.tcgdex import is_allowed_image_url

log = logging.getLogger(__name__)
router = APIRouter(prefix="/scan", tags=["scan"])

_MAX_BYTES = 12 * 1024 * 1024  # 12 MB


def _setting(db: Session, key: str, env_default: str) -> str:
    """DB-Einstellung mit Fallback auf .env/Config."""
    row = db.get(AppSetting, key)
    return (row.value if row and row.value else env_default) or ""


def _gemini_config(db: Session) -> tuple[str, str]:
    key = _setting(db, "gemini_api_key", settings.gemini_api_key)
    model = _setting(db, "gemini_model", settings.gemini_model)
    return key, model


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _gemini_limit_reached(db: Session) -> bool:
    """
    Manuelles Tageslimit (Setting gemini_daily_limit) DURCHSETZEN (Issue #3).
    0 = unbegrenzt (bisherige Nur-Anzeige-Semantik bleibt für 0 erhalten).
    """
    limit = int(_setting(db, "gemini_daily_limit", "0") or 0)
    if limit <= 0:
        return False
    row = db.get(GeminiUsage, _today_utc())
    return bool(row and (row.requests or 0) >= limit)


@router.get("/status")
def scan_status(db: Session = Depends(get_db)):
    """Welche Erkennungs-Engine ist aktiv? (Hybrid-Anzeige im UI)"""
    key, _ = _gemini_config(db)
    gem = gemini.is_enabled(key)
    return {
        "gemini": gem,
        "ocr": ocr.is_enabled(),
        "active": "gemini" if gem else ("ocr" if ocr.is_enabled() else "none"),
    }


# Google-AI-Studio Free-Tier-Limits (Stand 2025/2026). Flash vs Pro.
_GEMINI_FREE_LIMITS = {
    "flash": {"rpd": 1500, "rpm": 15, "tpm": 1_000_000},
    "pro": {"rpd": 50, "rpm": 2, "tpm": 2_000_000},
}


@router.get("/usage")
def scan_usage(db: Session = Depends(get_db)):
    """Gemini-Nutzung + Free-Tier-Limits (zur Kostenkontrolle / Überblick)."""
    today = _today_utc()
    rows = db.scalars(
        select(GeminiUsage).order_by(GeminiUsage.day.desc()).limit(30)
    ).all()
    today_row = next((r for r in rows if r.day == today), None)
    total_req = int(db.scalar(select(func.coalesce(func.sum(GeminiUsage.requests), 0))) or 0)
    total_tok = int(db.scalar(select(func.coalesce(func.sum(GeminiUsage.tokens), 0))) or 0)

    _, model = _gemini_config(db)
    tier = "pro" if "pro" in (model or "").lower() else "flash"
    limits = dict(_GEMINI_FREE_LIMITS[tier])
    # Manuelles Tageslimit überschreibt (falls gesetzt > 0)
    manual = int(_setting(db, "gemini_daily_limit", "0") or 0)
    if manual > 0:
        limits["rpd"] = manual

    avg_tokens = round(total_tok / total_req) if total_req else 0
    return {
        "today": {
            "day": today,
            "requests": today_row.requests if today_row else 0,
            "tokens": today_row.tokens if today_row else 0,
        },
        "total": {"requests": total_req, "tokens": total_tok},
        "avg_tokens_per_scan": avg_tokens,
        "model": model,
        "limits": limits,
        "days": [{"day": r.day, "requests": r.requests, "tokens": r.tokens} for r in rows],
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

    mime = (file.content_type or "image/jpeg").lower()
    if not mime.startswith("image/"):
        raise HTTPException(status_code=400, detail="Content-Type muss image/* sein")

    engine = "none"
    reads = None
    hinweis: str | None = None
    limit_erreicht = False
    # Hybrid: Gemini bevorzugt (stark bei Binder/Multi), sonst lokale OCR.
    gemini_key, gemini_model = _gemini_config(db)
    if gemini.is_enabled(gemini_key):
        if _gemini_limit_reached(db):
            limit_erreicht = True
            hinweis = "Gemini-Tageslimit erreicht – Erkennung über lokale OCR."
            log.info("Gemini-Tageslimit erreicht – Scan fällt auf lokale OCR zurück.")
        else:
            reads = await gemini.extract(data, api_key=gemini_key, model=gemini_model, mime_type=mime)
            if reads is not None:
                engine = "gemini"
    if reads is None:
        reads = ocr.extract(data, mode=mode, rows=rows, cols=cols)
        engine = "ocr"

    reads = reads or []
    # Einzelkarten-Modus: nur die Hauptkarte behalten (größte Bounding-Box),
    # falls versehentlich eine Karte darunter mit erkannt wurde.
    if mode == "single" and len(reads) > 1:
        def _area(r) -> float:
            return (r.bbox[2] * r.bbox[3]) if (r.bbox and len(r.bbox) == 4) else 0.0
        reads = [max(reads, key=_area)]

    candidates = await resolve_reads(db, reads, default_lang=default_language)
    return ScanResponse(
        engine=engine, mode=mode, candidates=candidates,
        limit_erreicht=limit_erreicht, hinweis=hinweis,
    )


@router.post("/resolve", response_model=ScanCandidate)
async def scan_resolve(read: ScanRawRead, db: Session = Depends(get_db)):
    """
    Löst eine (manuell angepasste) Erkennung neu gegen TCGdex auf – für die
    Live-Vorschau im Bestätigungs-Dialog, wenn der Nutzer Set/Nummer ändert.
    """
    return await resolve_one(db, read, default_lang=read.language or "DE")


@router.post("/commit", response_model=ScanCommitResponse)
def scan_commit(payload: ScanCommitRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Legt die bestätigten Karten an. Ziel:
      - pokedex     → besessen, Pokédex-Vertreter automatisch (exklusiv)
      - collection  → besessen + Sammlung (mit Binder-Slot)
      - wishlist    → nicht besessen, auf Wunschliste (mit Priorität)
    Besessene Karten laufen über den Domain-Service (Adoption + Auto-Flag
    + Bild-Fetch, Issue #4).
    """
    is_wishlist = payload.target == "wishlist"

    collection: Collection | None = None
    if payload.target == "collection":
        if not payload.collection_id:
            raise HTTPException(status_code=400, detail="collection_id fehlt")
        collection = db.get(Collection, payload.collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Sammlung nicht gefunden")

    created_ids: list[int] = []
    for item in payload.items:
        fields = dict(
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
            tcgdex_card_id=item.tcgdex_card_id,
            set_id=item.set_id,
            dex_id=item.dex_id,
            bild_karte_url=item.bild_karte_url if is_allowed_image_url(item.bild_karte_url) else None,
        )
        if is_wishlist:
            card = PokemonCard(**fields, besessen=False, wunschliste=True, prioritaet=item.prioritaet)
            db.add(card)
            db.flush()  # ID
        else:
            card = create_owned_card(db, fields, background_tasks=background_tasks, commit=False)

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
