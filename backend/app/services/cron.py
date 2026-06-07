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


def start_scheduler():
    scheduler.add_job(_daily_price_update, "cron", hour=3, minute=0)
    scheduler.start()
    log.info("Cron-Scheduler gestartet (täglich 03:00 Uhr)")
