"""
TCGdex-Katalog: durchsuchbares Nachschlagewerk aller Karten.
Read-only; per Stern auf die Wunschliste / in Sammlungen übernehmbar.
"""

import math

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db, run_with_session
from app.domain.pokedex import GEN_RANGES
from app.domain.search import parse_kurzcode
from app.models.card import PokemonCard
from app.models.tcgdex_catalog import TcgdexCatalog
from app.schemas.catalog import CatalogAddRequest, CatalogDetail, CatalogItem, CatalogListResponse
from app.services import catalog as catalog_svc, catalog_images, tcgdex
from app.services.set_sync import sync_sets
from app.services.settings import get_setting

router = APIRouter(prefix="/catalog", tags=["catalog"])

@router.get("", response_model=CatalogListResponse)
def list_catalog(
    request: Request,
    q: str | None = None,
    set_code: str | None = None,
    set_id: str | None = None,
    illustrator: str | None = None,
    generation: int | None = None,
    region: str | None = None,   # "west" | "ja" | … (None = alle)
    sort: str = Query("set", pattern="^(set|name|dex)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(60, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = select(TcgdexCatalog)
    if q:
        # Kurzcode „PFL 001" → Set-Kürzel + Nummer, aber nur wenn das Kürzel
        # wirklich ein Set im Katalog ist (sonst kapert „Mew 151" die
        # Namenssuche). Andernfalls normale Volltextsuche.
        kc = parse_kurzcode(q)
        kc_hit = False
        if kc:
            exists = db.scalar(
                select(TcgdexCatalog.card_id)
                .where(TcgdexCatalog.set_code == kc.code)
                .limit(1)
            )
            if exists:
                query = query.where(
                    TcgdexCatalog.set_code == kc.code,
                    func.ltrim(TcgdexCatalog.local_id, "0") == kc.nr,
                )
                kc_hit = True
        if not kc_hit:
            term = f"%{q.strip()}%"
            query = query.where(or_(
                TcgdexCatalog.name.ilike(term),
                TcgdexCatalog.name_en.ilike(term),
                TcgdexCatalog.illustrator.ilike(term),
                TcgdexCatalog.local_id.ilike(term),
            ))
    if set_code:
        query = query.where(TcgdexCatalog.set_code == set_code)
    if set_id:
        query = query.where(TcgdexCatalog.set_id == set_id)
    if region:
        query = query.where(TcgdexCatalog.region == region)
    if illustrator:
        query = query.where(TcgdexCatalog.illustrator.ilike(f"%{illustrator}%"))
    if generation and generation in GEN_RANGES:
        lo, hi = GEN_RANGES[generation]
        query = query.where(TcgdexCatalog.dex_id.between(lo, hi))

    if sort == "name":
        query = query.order_by(TcgdexCatalog.name.nulls_last())
    elif sort == "dex":
        query = query.order_by(TcgdexCatalog.dex_id.nulls_last(), TcgdexCatalog.set_id)
    else:  # set + Kartennummer
        query = query.order_by(
            TcgdexCatalog.set_id,
            TcgdexCatalog.local_id_num.nulls_last(),
            TcgdexCatalog.local_id,
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.offset((page - 1) * limit).limit(limit)).all()

    # Besitz-/Pokédex-Status der angezeigten Karten ermitteln (grüner/roter
    # Punkt). CASE-TOLERANT (#67): der Scan schreibt TCGdex-IDs klein
    # („me03-029"), der JP-Katalog führt sie groß — sonst gälte eine
    # scan-erfasste JP-Karte hier als nicht besessen. Beidseitig upper();
    # die Katalog-Seite hat dafür den Ausdrucks-Index (v1.7.3), die
    # Karten-Seite bekommt ihn in den Light-Migrations.
    ids_upper = {r.card_id.upper() for r in rows if r.card_id}
    owned_ids: set[str] = set()
    pokedex_ids: set[str] = set()
    if ids_upper:
        owned_ids = set(db.scalars(
            select(func.upper(PokemonCard.tcgdex_card_id)).where(
                func.upper(PokemonCard.tcgdex_card_id).in_(ids_upper),
                PokemonCard.besessen == True)  # noqa: E712
        ).all())
        pokedex_ids = set(db.scalars(
            select(func.upper(PokemonCard.tcgdex_card_id)).where(
                func.upper(PokemonCard.tcgdex_card_id).in_(ids_upper),
                PokemonCard.im_pokedex == True)  # noqa: E712
        ).all())

    base_url = str(request.base_url)
    items = []
    for r in rows:
        ci = CatalogItem.model_validate(r)
        # #43: lokal gecachtes Bild bevorzugen, sonst unverändert die CDN-URL
        # (EINE Hilfsfunktion für Liste/Detail/Soll-Slots, DRY).
        ci.image_url = catalog_images.resolve_catalog_image_url(r.image_pfad, r.image_url, base_url)
        key = r.card_id.upper() if r.card_id else ""
        ci.owned = key in owned_ids
        ci.in_pokedex = key in pokedex_ids
        items.append(ci)

    return CatalogListResponse(
        items=items, total=total, page=page, limit=limit,
        pages=math.ceil(total / limit) if total else 1,
    )


@router.get("/meta")
def catalog_meta(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(TcgdexCatalog)) or 0
    enriched = db.scalar(
        select(func.count()).select_from(TcgdexCatalog).where(TcgdexCatalog.enriched == True)  # noqa: E712
    ) or 0
    # #43: Zahl der bereits lokal gecachten Katalogbilder — die Größenschätzung
    # (Stufe "all") rechnet das Frontend aus `total` (kein zweites Backend-Feld
    # für dieselbe Information, DRY).
    cached_images = db.scalar(
        select(func.count()).select_from(TcgdexCatalog).where(TcgdexCatalog.image_pfad.isnot(None))
    ) or 0
    return {"total": int(total), "enriched": int(enriched), "cached_images": int(cached_images)}


@router.post("/sync")
async def trigger_catalog_sync(background_tasks: BackgroundTasks):
    """Sets voll-syncen + Katalog-Basis aufbauen (Hintergrund). Danach ggf. /enrich."""
    async def _job(db: Session):
        await sync_sets()
        await catalog_svc.sync_catalog(db)
    background_tasks.add_task(run_with_session, _job)
    return {"detail": "Katalog-Sync gestartet (Sets + Katalog-Basis) – läuft im Hintergrund."}


# Das Enrichment (Volldetails) läuft täglich im Katalog-Cron in Etappen —
# die manuellen POST /catalog/enrich(-all)-Endpoints wurden entfernt (Issue #12).


@router.get("/illustrators")
def list_illustrators(db: Session = Depends(get_db)):
    """Alle bekannten Illustratoren (für das Filter-Dropdown)."""
    rows = db.scalars(
        select(TcgdexCatalog.illustrator)
        .where(TcgdexCatalog.illustrator.isnot(None))
        .distinct()
        .order_by(TcgdexCatalog.illustrator)
    ).all()
    return [r for r in rows if r]


@router.get("/{card_id}/detail", response_model=CatalogDetail)
async def catalog_card_detail(
    card_id: str, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db),
):
    """Angereichertes Katalog-Detail fürs Popup: die gespeicherte Zeile plus ein
    LIVE-Abruf bei TCGdex (Regionssprache) — füllt fehlende Felder (dex/rarity/
    illustrator/kategorie/varianten) noch nicht angereicherter Karten und liefert
    aktuelle Preise (€ Cardmarket + $ TCGplayer). Read-only, fehlertolerant: bei
    TCGdex-Ausfall kommen die gespeicherten Felder ohne Preise zurück.

    #43: cached bei Bedarf das Katalogbild NACH dem Response-Versand (Background-
    Task, siehe catalog_images.cache_one_on_demand) — GET bleibt lesend/schnell,
    die Stufe entscheidet NUR, ob der Task überhaupt registriert wird."""
    row = db.get(TcgdexCatalog, card_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Karte nicht im Katalog")

    detail = CatalogDetail.model_validate(row)
    # #43: lokal gecachtes Bild bevorzugen, sonst unverändert die CDN-URL.
    detail.image_url = catalog_images.resolve_catalog_image_url(
        row.image_pfad, row.image_url, str(request.base_url))
    # Case-tolerant wie in der Liste (#67)
    cid_upper = card_id.upper()
    detail.owned = bool(db.scalar(select(PokemonCard.id).where(
        func.upper(PokemonCard.tcgdex_card_id) == cid_upper,
        PokemonCard.besessen == True).limit(1)))  # noqa: E712
    detail.in_pokedex = bool(db.scalar(select(PokemonCard.id).where(
        func.upper(PokemonCard.tcgdex_card_id) == cid_upper,
        PokemonCard.im_pokedex == True).limit(1)))  # noqa: E712

    try:
        tc = await tcgdex.get_card(card_id, catalog_svc._catalog_lang(row.region))
    except Exception:
        tc = None  # externe Quelle darf das Popup nicht kippen
    if tc:
        # Fehlende (noch nicht angereicherte) Felder aus dem Live-Abruf auffüllen.
        if detail.dex_id is None:
            detail.dex_id = tc.dex_id
        detail.rarity = detail.rarity or tc.rarity
        detail.illustrator = detail.illustrator or tc.illustrator
        detail.category = detail.category or tc.category
        if tc.variants:
            if detail.variants_normal is None:
                detail.variants_normal = tc.variants.normal
            if detail.variants_reverse is None:
                detail.variants_reverse = tc.variants.reverse
            if detail.variants_holo is None:
                detail.variants_holo = tc.variants.holo
            if detail.variants_firstedition is None:
                detail.variants_firstedition = tc.variants.firstEdition
        # „Beides": model_validate hat oben die GECACHTEN Preise + Zeitstempel
        # gesetzt; ein frischer Live-€ überschreibt sie (mit low/trend). Für $ hat
        # der Live-Abruf bei JP-Karten None → der aus TCGCSV gecachte $ bleibt.
        pr = catalog_svc.catalog_prices(tc.pricing)
        if pr["eur"] is not None:
            detail.price_eur = pr["eur"]
            detail.price_eur_low = pr["eur_low"]
            detail.price_eur_trend = pr["eur_trend"]
            detail.price_eur_updated = pr["eur_updated"]
        if pr["usd"] is not None:
            detail.price_usd = pr["usd"]
            detail.price_usd_updated = pr["usd_updated"]

    # #43: On-demand-Cache NUR registrieren, wenn die Stufe überhaupt Downloads
    # erlaubt — bei "urls" (Default) bleibt der Detail-GET ohne jede
    # Schreib-Nebenwirkung. Die feinere Prüfung (welche Karten "owned" erlaubt)
    # macht der Task selbst (stage_allows), mit dem zu diesem Zeitpunkt
    # frischesten Setting-Wert. Panel-Nacharbeit #43: UND nur, wenn die Zeile
    # noch keinen Pfad hat (row liegt hier bereits vor, ganz oben geladen) —
    # spart je Popup-Öffnung einer längst gecachten Karte eine No-op-
    # Background-Session (der Task würde ohnehin sofort an
    # cache_one_on_demand()s eigenem Bereits-gecacht-Check verpuffen, aber
    # erst NACH dem Session-Aufbau).
    stage = get_setting(db, "catalog_image_cache_level")
    if stage != "urls" and not row.image_pfad:
        background_tasks.add_task(catalog_images.cache_one_on_demand, card_id)

    return detail


@router.post("/{card_id}/wishlist")
async def catalog_to_wishlist(
    card_id: str,
    payload: CatalogAddRequest | None = Body(None),
    db: Session = Depends(get_db),
):
    p = payload or CatalogAddRequest()
    new_id = await catalog_svc.add_to_wishlist(
        db, card_id, p.prioritaet,
        sprache=p.sprache, zustand=p.zustand, folierung=p.folierung, erste_edition=p.erste_edition,
    )
    if not new_id:
        raise HTTPException(status_code=404, detail="Katalog-Karte nicht gefunden")
    return {"card_id": new_id}


@router.post("/{card_id}/collection")
async def catalog_to_collection(
    card_id: str,
    background_tasks: BackgroundTasks,
    collection_id: int = Query(...),
    payload: CatalogAddRequest | None = Body(None),
    db: Session = Depends(get_db),
):
    p = payload or CatalogAddRequest()
    new_id = await catalog_svc.add_to_collection(
        db, card_id, collection_id,
        sprache=p.sprache, zustand=p.zustand, folierung=p.folierung, erste_edition=p.erste_edition,
        background_tasks=background_tasks,
    )
    if not new_id:
        raise HTTPException(status_code=404, detail="Katalog-Karte oder Sammlung nicht gefunden")
    return {"card_id": new_id}
