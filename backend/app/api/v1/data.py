"""
Daten-Export & Backup/Restore (Issue #17).

- GET  /data/export.csv  — alle Kartenfelder als CSV (UTF-8 mit BOM, Semikolon)
- GET  /data/backup      — ZIP: data.json (ALLE Tabellen, generisch) + images/
- POST /data/restore     — ZIP-Upload, validieren, DESTRUKTIV einspielen

Alles hängt unter dem Auth-Zwang (api/v1/__init__.py, Issue #1). Das Backup
ist ein PERSÖNLICHES Voll-Backup und enthält bewusst auch die Settings-Zeilen
inkl. Passwort-Hash (bcrypt — kein Klartext-Secret, aber nicht öffentlich
teilen). Restore ist destruktiv und verlangt confirm="JA_WIRKLICH".
"""

import codecs
import csv
import io
import json
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path, PurePosixPath

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import Integer, text
from starlette.background import BackgroundTask

from app.config import settings
from app.database import Base, engine
from app.models.card import PokemonCard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["data"])

# Versionsfeld des Backup-Formats — Restore prüft darauf. Bei inkompatiblen
# Format-Änderungen hochzählen und im Restore eine Migration/Absage einbauen.
BACKUP_FORMAT = 1
RESTORE_MAX_BYTES = 500 * 1024 * 1024  # 500 MB
RESTORE_CONFIRM = "JA_WIRKLICH"


# ── Hilfen ────────────────────────────────────────────────────────────────────

def _jsonify(value):
    """DB-Wert → JSON-serialisierbar (datetime/Decimal)."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _csv_cell(value) -> str:
    """DB-Wert → Excel-freundliche CSV-Zelle (deutsches Excel: Semikolon+Komma)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "ja" if value else "nein"
    if isinstance(value, Decimal):
        return str(value).replace(".", ",")
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    return str(value)


# ── CSV-Export ────────────────────────────────────────────────────────────────

@router.get("/export.csv")
def export_csv():
    """
    Alle PokemonCard-Felder als CSV. UTF-8 MIT BOM + Semikolon-Delimiter,
    damit (deutsches) Excel die Datei per Doppelklick korrekt öffnet.
    """
    columns = [c.name for c in PokemonCard.__table__.columns]

    # Zeilen VOR dem Response-Bau materialisieren: seit FastAPI 0.106 werden
    # yield-Dependencies (get_db) geschlossen, bevor ein StreamingResponse-
    # Generator läuft — deshalb hier eine eigene, kurze Session.
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        rows = [
            [_csv_cell(getattr(card, c)) for c in columns]
            for card in db.query(PokemonCard).order_by(PokemonCard.id).all()
        ]
    finally:
        db.close()

    def _iter():
        yield codecs.BOM_UTF8  # BOM → Excel erkennt UTF-8
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";", lineterminator="\r\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow(row)
        yield buf.getvalue().encode("utf-8")

    filename = f"pokecollect-export-{date.today().isoformat()}.csv"
    return StreamingResponse(
        _iter(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Backup ───────────────────────────────────────────────────────────────────

def _dump_all_tables() -> dict[str, list[dict]]:
    """
    ALLE Tabellen generisch dumpen (Base.metadata.sorted_tables = FK-Ordnung).
    Erfasst damit auch n:m-Tabellen ohne Model-Klasse (collection_cards) und
    künftige Tabellen automatisch.
    """
    dump: dict[str, list[dict]] = {}
    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            result = conn.execute(table.select())
            dump[table.name] = [
                {k: _jsonify(v) for k, v in row.items()}
                for row in result.mappings()
            ]
    return dump


@router.get("/backup")
def backup():
    """
    Voll-Backup als ZIP: data.json (alle Tabellen + Versionsfeld) + der
    komplette images/-Ordner. Wird in eine Temp-Datei gebaut (Bilder können
    hunderte MB sein) und nach dem Senden gelöscht.
    """
    payload = {
        "format": BACKUP_FORMAT,
        "app_version": settings.app_version,
        "created_at": datetime.utcnow().isoformat(),
        "tables": _dump_all_tables(),
    }

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("data.json", json.dumps(payload, ensure_ascii=False))
            images_dir = Path(settings.images_dir)
            if images_dir.is_dir():
                for p in sorted(images_dir.rglob("*")):
                    if p.is_file():
                        rel = p.relative_to(images_dir).as_posix()
                        zf.write(p, arcname=f"images/{rel}")
        tmp.close()
    except Exception:
        tmp.close()
        os.unlink(tmp.name)
        raise

    filename = f"pokecollect-backup-{date.today().isoformat()}.zip"
    return FileResponse(
        tmp.name,
        media_type="application/zip",
        filename=filename,
        background=BackgroundTask(os.unlink, tmp.name),
    )


# ── Restore ──────────────────────────────────────────────────────────────────

def _validate_payload(raw: bytes) -> dict:
    """Struktur + Versionsfeld prüfen — VOR jeder destruktiven Aktion."""
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="data.json ist kein gültiges JSON")
    if not isinstance(payload, dict) or not isinstance(payload.get("tables"), dict):
        raise HTTPException(status_code=400, detail="data.json hat nicht die erwartete Struktur (tables fehlt)")
    if "app_version" not in payload:
        raise HTTPException(status_code=400, detail="data.json ohne Versionsfeld (app_version) — kein PokéCollect-Backup?")
    if payload.get("format") != BACKUP_FORMAT:
        raise HTTPException(
            status_code=400,
            detail=f"Backup-Format {payload.get('format')!r} wird nicht unterstützt (erwartet: {BACKUP_FORMAT})",
        )
    for name, rows in payload["tables"].items():
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            raise HTTPException(status_code=400, detail=f"Tabelle {name!r} in data.json ist keine Zeilenliste")
    return payload


def _restore_tables(payload: dict) -> dict[str, int]:
    """
    DESTRUKTIV: alle Tabellen leeren (umgekehrte FK-Ordnung), dann aus dem
    Backup befüllen (FK-Ordnung via sorted_tables). Eine Transaktion —
    schlägt etwas fehl, bleibt die alte DB unangetastet.
    """
    tables = list(Base.metadata.sorted_tables)
    counts: dict[str, int] = {}
    backup_tables: dict = payload["tables"]

    unknown = set(backup_tables) - {t.name for t in tables}
    if unknown:
        logger.warning("Restore: unbekannte Tabellen im Backup werden ignoriert: %s", sorted(unknown))

    with engine.begin() as conn:
        for table in reversed(tables):
            conn.execute(table.delete())
        for table in tables:
            rows = backup_tables.get(table.name, [])
            # Auf die Spalten der Tabelle normalisieren: fremde Keys fallen
            # weg, fehlende werden NULL (executemany braucht homogene Dicts).
            col_names = [c.name for c in table.columns]
            prepared = [{c: row.get(c) for c in col_names} for row in rows]
            if prepared:
                conn.execute(table.insert(), prepared)
            counts[table.name] = len(prepared)

        # PostgreSQL-Sequenzen auf MAX(id) nachziehen — sonst kollidiert der
        # nächste INSERT nach dem Restore mit bestehenden IDs.
        for table in tables:
            pk_cols = list(table.primary_key.columns)
            if len(pk_cols) != 1 or not isinstance(pk_cols[0].type, Integer):
                continue
            col = pk_cols[0]
            seq = conn.execute(
                text("SELECT pg_get_serial_sequence(:t, :c)"),
                {"t": table.name, "c": col.name},
            ).scalar()
            if seq:
                # Tabellen-/Spaltennamen stammen aus den eigenen Models (kein User-Input).
                conn.execute(text(
                    f"SELECT setval('{seq}', COALESCE((SELECT MAX({col.name}) FROM {table.name}), 1), "
                    f"(SELECT MAX({col.name}) FROM {table.name}) IS NOT NULL)"
                ))
    return counts


def _restore_images(zf: zipfile.ZipFile) -> int:
    """images/-Ordner leeren und aus dem ZIP zurückschreiben (Traversal-sicher)."""
    images_dir = Path(settings.images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)
    for child in images_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    written = 0
    for info in zf.infolist():
        name = info.filename
        if info.is_dir() or not name.startswith("images/"):
            continue
        rel = PurePosixPath(name).relative_to("images")
        if rel.is_absolute() or ".." in rel.parts:
            raise HTTPException(status_code=400, detail=f"Unsicherer Pfad im ZIP: {name}")
        target = images_dir.joinpath(*rel.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
        written += 1
    return written


@router.post("/restore")
async def restore(file: UploadFile = File(...), confirm: str = Form("")):
    """
    Backup-ZIP einspielen. DESTRUKTIV: ersetzt ALLE Daten und Bilder.
    Schutz: Pflichtfeld confirm="JA_WIRKLICH" (das UI verlangt zusätzlich
    Checkbox + Bestätigungsdialog).
    """
    if confirm != RESTORE_CONFIRM:
        raise HTTPException(
            status_code=400,
            detail='Restore nicht bestätigt — confirm="JA_WIRKLICH" ist Pflicht (ersetzt ALLE Daten).',
        )

    # Größenlimit 500 MB (Starlette hat den Upload bereits gespoolt).
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    if size > RESTORE_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Backup größer als 500 MB")

    # In Temp-Datei umkopieren — ZipFile braucht wahlfreien Zugriff.
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    try:
        shutil.copyfileobj(file.file, tmp)
        tmp.close()

        try:
            zf = zipfile.ZipFile(tmp.name)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Datei ist kein gültiges ZIP")
        with zf:
            if "data.json" not in zf.namelist():
                raise HTTPException(status_code=400, detail="ZIP enthält keine data.json — kein PokéCollect-Backup")
            payload = _validate_payload(zf.read("data.json"))

            # Erst NACH kompletter Validierung destruktiv werden.
            counts = _restore_tables(payload)
            images = _restore_images(zf)
    finally:
        os.unlink(tmp.name)

    logger.info("Restore eingespielt: %s Tabellen, %d Bilder (Backup-App-Version %s)",
                len(counts), images, payload.get("app_version"))
    return {
        "detail": "Backup eingespielt — alle Daten wurden ersetzt.",
        "backup_app_version": payload.get("app_version"),
        "restored": counts,
        "images": images,
    }
