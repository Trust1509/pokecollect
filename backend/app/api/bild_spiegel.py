"""
Auth-freier Spiegel-Pfad für fremde Bilder (#120) — Begründung und Grenzen
in services/bild_spiegel.py.

Bewusst NICHT unter dem Auth-Zwang von api/v1 (CLAUDE.md „Auth-Zwang"): Der
Browser lädt diese Pfade per <img>, das keinen Authorization-Header schickt —
wie beim /images-Mount (ADR-0003). Statt der Anmeldung schützt die Signatur:
Ein Abruf beim fremden Host findet nur für Quellen statt, die das Backend
selbst signiert hat; einen unsignierten Pfad gibt es nicht.

Nicht im OpenAPI-Schema (wie der /images-Mount): Die Pfade sind kein Teil der
Fach-Schnittstelle, und ein Fuzzer erreicht ohne Signatur ohnehin nur 404.
Ein Fehlschlag beim fremden Host ist ebenfalls 404, nicht 502 — für den
Aufrufer (Optimizer, Browser) ist das Bild schlicht nicht da.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services import bild_spiegel

router = APIRouter(include_in_schema=False)

_MEDIENTYP = {".webp": "image/webp", ".jpg": "image/jpeg", ".png": "image/png"}
_KOPF = {
    # Der Spiegel holt eine Quelle nur einmal und liefert danach immer
    # dieselbe Datei — eine Woche Zwischenspeicher im Browser ist genug.
    "Cache-Control": "public, max-age=604800",
    "X-Content-Type-Options": "nosniff",
}


async def _ausliefern(url: str) -> FileResponse:
    datei: Path | None = await bild_spiegel.datei_fuer(url)
    if datei is None:
        raise HTTPException(status_code=404, detail="Bild nicht verfügbar")
    return FileResponse(datei, media_type=_MEDIENTYP[datei.suffix], headers=_KOPF)


@router.get(f"{bild_spiegel.PRAEFIX}/{{signatur}}/{{kodiert}}")
async def gespiegeltes_bild(signatur: str, kodiert: str) -> FileResponse:
    url = bild_spiegel.url_aus_pfad(signatur, kodiert)
    if url is None:
        raise HTTPException(status_code=404, detail="Bild nicht verfügbar")
    return await _ausliefern(url)
