from fastapi import APIRouter, Depends

from app.api.deps import require_auth
from app.api.v1 import auth, cards, catalog, collections, prices, scan, settings, sets

router = APIRouter(prefix="/api/v1")

# Auth-frei: nur der Login selbst. /health und der /images-StaticFiles-Mount
# liegen außerhalb dieses Routers (main.py) und bleiben ebenfalls offen —
# <img>-Tags können keine Authorization-Header senden (Issue #1).
router.include_router(auth.router)

# Alle Fach-Router erzwingen ein gültiges JWT (require_auth, Issue #1).
for protected in (
    cards.router,
    catalog.router,
    collections.router,
    prices.router,
    scan.router,
    settings.router,
    sets.router,
):
    router.include_router(protected, dependencies=[Depends(require_auth)])
