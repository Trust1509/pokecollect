"""
Täglicher Cron-Job um 03:00 Uhr: Preise aller besessenen Karten aktualisieren.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.database import SessionLocal
from app.models.card import PokemonCard
from app.services.pricing import refresh_prices_for_cards

log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _daily_price_update():
    db = SessionLocal()
    try:
        enabled_row = db.get(__import__("app.models.setting", fromlist=["AppSetting"]).AppSetting, "price_update_enabled")
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


def start_scheduler():
    scheduler.add_job(_daily_price_update, "cron", hour=3, minute=0)
    scheduler.add_job(_daily_catalog_sync, "cron", hour=4, minute=0)
    scheduler.start()
    log.info("Cron-Scheduler gestartet (Preise 03:00, Katalog 04:00)")
