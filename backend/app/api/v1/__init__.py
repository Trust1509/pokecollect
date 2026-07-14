from fastapi import APIRouter

from app.api.v1 import auth, cards, catalog, collections, prices, scan, settings, sets

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(cards.router)
router.include_router(catalog.router)
router.include_router(collections.router)
router.include_router(prices.router)
router.include_router(scan.router)
router.include_router(settings.router)
router.include_router(sets.router)
