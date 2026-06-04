from fastapi import APIRouter

from app.api.v1 import auth, cards, prices

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(cards.router)
router.include_router(prices.router)
