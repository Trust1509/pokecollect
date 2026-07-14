"""
Tägliche Cron-Jobs:
  - Preisupdate aller besessenen Karten (Stunde aus Setting price_update_hour,
    Default 03:00; Änderung wird nach API-Neustart aktiv)
  - Katalog-Sync + Enrichment (04:00)
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal, run_with_session
from app.models.card import PokemonCard
from app.models.setting import AppSetting
from app.services.pricing import refresh_prices_for_cards

log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _daily_price_update(db: Session):
    enabled_row = db.get(AppSetting, "price_update_enabled")
    if enabled_row and enabled_row.value == "false":
        log.info("Preisupdate deaktiviert – übersprungen.")
        return
    log.info("Starte täglichen Preisupdate …")
    ids = list(db.scalars(
        select(PokemonCard.id).where(PokemonCard.besessen == True)  # noqa: E712
    ).all())
    if ids:
        await refresh_prices_for_cards(db, ids)
    else:
        log.info("Keine besessenen Karten – nichts zu aktualisieren.")


async def _daily_catalog_sync(db: Session):
    """Sets + Katalog-Basis aktualisieren und einen Schwung anreichern."""
    try:
        from app.services.set_sync import sync_sets
        from app.services.catalog import sync_catalog, enrich_catalog
        log.info("Starte täglichen Katalog-Sync …")
        await sync_sets()
        await sync_catalog(db)
        await enrich_catalog(db, limit=2000)  # in Etappen über mehrere Tage vollständig
    except Exception as exc:
        log.error("Katalog-Sync fehlgeschlagen: %s", exc)


def _price_update_hour(db: Session) -> int:
    """Stunde aus dem Setting price_update_hour (0–23), Default 3."""
    try:
        row = db.get(AppSetting, "price_update_hour")
        if row and row.value and row.value.strip().isdigit():
            return min(23, max(0, int(row.value.strip())))
    except Exception as exc:  # DB evtl. noch nicht bereit → Default nutzen
        log.warning("price_update_hour nicht lesbar (%s) – nutze 03:00.", exc)
    return 3


async def _price_update_job():
    await run_with_session(_daily_price_update)


async def _catalog_sync_job():
    await run_with_session(_daily_catalog_sync)


def start_scheduler():
    db = SessionLocal()
    try:
        hour = _price_update_hour(db)
    finally:
        db.close()
    scheduler.add_job(_price_update_job, "cron", hour=hour, minute=0)
    scheduler.add_job(_catalog_sync_job, "cron", hour=4, minute=0)
    scheduler.start()
    log.info("Cron-Scheduler gestartet (Preise %02d:00, Katalog 04:00)", hour)
