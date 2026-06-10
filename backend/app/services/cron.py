"""
Tägliche Cron-Jobs:
  - Preisupdate aller besessenen Karten (Stunde aus Setting price_update_hour,
    Default 03:00; Änderung wird nach API-Neustart aktiv)
  - Katalog-Sync + Enrichment (04:00)
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.database import SessionLocal
from app.models.card import PokemonCard
from app.models.setting import AppSetting
from app.services.pricing import refresh_prices_for_cards

log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _daily_price_update():
    db = SessionLocal()
    try:
        enabled_row = db.get(AppSetting, "price_update_enabled")
        if enabled_row and enabled_row.value == "false":
            log.info("Preisupdate deaktiviert – übersprungen.")
            return
        log.info("Starte täglichen Preisupdate …")
        ids = list(db.scalars(
            select(PokemonCard.id).where(PokemonCard.besessen == True)
        ).all())
    finally:
        db.close()
    if ids:
        await refresh_prices_for_cards(ids)
    else:
        log.info("Keine besessenen Karten – nichts zu aktualisieren.")


async def _daily_catalog_sync():
    """Sets + Katalog-Basis aktualisieren und einen Schwung anreichern."""
    try:
        from app.services.set_sync import sync_sets
        from app.services.catalog import sync_catalog, enrich_catalog
        log.info("Starte täglichen Katalog-Sync …")
        await sync_sets()
        await sync_catalog()
        await enrich_catalog(limit=2000)  # in Etappen über mehrere Tage vollständig
    except Exception as exc:
        log.error("Katalog-Sync fehlgeschlagen: %s", exc)


def _price_update_hour() -> int:
    """Stunde aus dem Setting price_update_hour (0–23), Default 3."""
    try:
        db = SessionLocal()
        try:
            row = db.get(AppSetting, "price_update_hour")
        finally:
            db.close()
        if row and row.value and row.value.strip().isdigit():
            return min(23, max(0, int(row.value.strip())))
    except Exception as exc:  # DB evtl. noch nicht bereit → Default nutzen
        log.warning("price_update_hour nicht lesbar (%s) – nutze 03:00.", exc)
    return 3


def start_scheduler():
    hour = _price_update_hour()
    scheduler.add_job(_daily_price_update, "cron", hour=hour, minute=0)
    scheduler.add_job(_daily_catalog_sync, "cron", hour=4, minute=0)
    scheduler.start()
    log.info("Cron-Scheduler gestartet (Preise %02d:00, Katalog 04:00)", hour)
