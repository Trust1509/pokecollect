"""
Bild-Proxy / -Cache (optional nutzbar).

Holt ein externes Kartenbild EINMAL serverseitig, legt es lokal ab und liefert
es danach vom eigenen Server aus. Vorteile:
  - Offline-Fähigkeit (Bild bleibt erhalten, auch wenn TCGdex nicht erreichbar)
  - Datenschutz (Client-IP wird nicht an TCGdex weitergegeben)

Sicherheit: Es werden ausschließlich https-URLs von erlaubten Bild-Hosts
(assets.tcgdex.net) akzeptiert – so kann über manipulierte Daten keine fremde
URL eingeschleust werden.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from app.config import settings
from app.services.tcgdex import is_allowed_image_url

router = APIRouter(prefix="/images", tags=["images"])

CACHE_DIR = Path(settings.images_dir) / "cache"
_ALLOWED_EXT = {".webp", ".png", ".jpg", ".jpeg"}
_CONTENT_TYPES = {
    ".webp": "image/webp",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


@router.get("/proxy")
async def proxy_image(u: str = Query(..., description="Bild-URL (nur erlaubte Hosts)")):
    if not is_allowed_image_url(u):
        raise HTTPException(status_code=400, detail="Bild-URL-Host nicht erlaubt")

    ext = os.path.splitext(u.split("?")[0])[1].lower()
    if ext not in _ALLOWED_EXT:
        ext = ".img"
    key = hashlib.sha256(u.encode("utf-8")).hexdigest()
    path = CACHE_DIR / f"{key}{ext}"
    media_type = _CONTENT_TYPES.get(ext, "application/octet-stream")

    if path.exists():
        return FileResponse(path, media_type=media_type)

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(u)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Bild nicht erreichbar: {exc}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Bild-Fehler HTTP {resp.status_code}")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(resp.content)
    tmp.replace(path)  # atomar – keine halben Dateien im Cache

    return Response(
        content=resp.content,
        media_type=resp.headers.get("content-type", media_type),
        headers={"Cache-Control": "public, max-age=86400"},
    )
