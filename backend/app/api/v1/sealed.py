"""
CRUD-Router für Sealed-Produkte (Issue #35) — Booster/Display/ETB/…

Eigene Entität (models/sealed.py). Set-Bezug ist n:m (Join-Tabelle
sealed_product_sets) — die Zuordnung wird hier manuell gepflegt (wie
collection_cards). Alles hängt unter dem Auth-Zwang (api/v1/__init__.py,
ADR-0003). Bild-Upload nutzt die bestehende Bild-Pipeline (services/card_images
über services/sealed_images, DRY).
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sealed import SealedProduct, sealed_product_sets
from app.schemas.sealed import (
    SEALED_TYP_VALUES,
    SEALED_ZUSTAND_VALUES,
    SealedEnumsResponse,
    SealedProductCreate,
    SealedProductResponse,
    SealedProductUpdate,
)
from app.services.card_images import ImageValidationError
from app.services.sealed_images import (
    cleanup_sealed_orphans,
    clear_sealed_image,
    store_sealed_image,
    unlink_media_files,
)

router = APIRouter(prefix="/sealed", tags=["sealed"])


# ── Hilfen ────────────────────────────────────────────────────────────────────

def _product_or_404(product_id: int, db: Session) -> SealedProduct:
    product = db.get(SealedProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Sealed-Produkt nicht gefunden")
    return product


def _sets_by_products(db: Session, ids: list[int]) -> dict[int, list[str]]:
    """set_codes je Produkt-Id (eine Query für die Listenansicht, DRY)."""
    if not ids:
        return {}
    rows = db.execute(
        select(sealed_product_sets.c.sealed_product_id, sealed_product_sets.c.set_code)
        .where(sealed_product_sets.c.sealed_product_id.in_(ids))
    ).all()
    out: dict[int, list[str]] = {}
    for pid, code in rows:
        out.setdefault(pid, []).append(code)
    for codes in out.values():
        codes.sort()
    return out


def _replace_sets(db: Session, product_id: int, set_codes: list[str]) -> None:
    """Set-Zuordnung eines Produkts vollständig ersetzen (deduped, leere raus)."""
    db.execute(
        delete(sealed_product_sets).where(
            sealed_product_sets.c.sealed_product_id == product_id
        )
    )
    seen: set[str] = set()
    for code in set_codes:
        c = (code or "").strip()
        if not c or c in seen:
            continue
        seen.add(c)
        db.execute(
            sealed_product_sets.insert().values(sealed_product_id=product_id, set_code=c)
        )


def _response(product: SealedProduct, set_codes: list[str]) -> SealedProductResponse:
    gv: Optional[Decimal] = None
    if product.wert_eur is not None and product.kaufpreis_eur is not None:
        gv = product.wert_eur - product.kaufpreis_eur
    return SealedProductResponse(
        id=product.id,
        name=product.name,
        typ=product.typ,
        zustand=product.zustand,
        kaufpreis_eur=product.kaufpreis_eur,
        kaufdatum=product.kaufdatum,
        wert_eur=product.wert_eur,
        notizen=product.notizen,
        bild_pfad=product.bild_pfad,
        bild_thumbnail_pfad=product.bild_thumbnail_pfad,
        hinzugefuegt_am=product.hinzugefuegt_am,
        set_codes=set_codes,
        unrealisierter_gv_eur=gv,
    )


# ── Enums ─────────────────────────────────────────────────────────────────────

@router.get("/meta/enums", response_model=SealedEnumsResponse)
def get_enums():
    return SealedEnumsResponse(typ=SEALED_TYP_VALUES, zustand=SEALED_ZUSTAND_VALUES)


# ── Liste ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[SealedProductResponse])
def list_sealed(
    typ: Optional[str] = None,
    set: Optional[str] = None,
    zustand: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = select(SealedProduct)
    if typ:
        q = q.where(SealedProduct.typ == typ)
    if zustand:
        q = q.where(SealedProduct.zustand == zustand)
    if set:
        # Set-Filter matcht, wenn das Set in der n:m-Zuordnung enthalten ist.
        # Case-insensitiv (#38): Neuware wird upper gespeichert, Altbestand kann
        # gemischt sein → beidseitig upper vergleichen, „obf" findet „OBF".
        sub = select(sealed_product_sets.c.sealed_product_id).where(
            func.upper(sealed_product_sets.c.set_code) == set.strip().upper()
        )
        q = q.where(SealedProduct.id.in_(sub))
    q = q.order_by(SealedProduct.hinzugefuegt_am.desc(), SealedProduct.id.desc())

    items = db.scalars(q).all()
    sets_map = _sets_by_products(db, [p.id for p in items])
    return [_response(p, sets_map.get(p.id, [])) for p in items]


# ── Anlegen / Lesen / Ändern / Löschen ────────────────────────────────────────

@router.post("", response_model=SealedProductResponse, status_code=201)
def create_sealed(data: SealedProductCreate, db: Session = Depends(get_db)):
    payload = data.model_dump()
    set_codes = payload.pop("set_codes", []) or []
    product = SealedProduct(**payload)
    db.add(product)
    db.flush()  # id für die Join-Zeilen
    _replace_sets(db, product.id, set_codes)
    db.commit()
    db.refresh(product)
    return _response(product, _sets_by_products(db, [product.id]).get(product.id, []))


@router.get("/{product_id}", response_model=SealedProductResponse)
def get_sealed(product_id: int, db: Session = Depends(get_db)):
    product = _product_or_404(product_id, db)
    return _response(product, _sets_by_products(db, [product_id]).get(product_id, []))


@router.put("/{product_id}", response_model=SealedProductResponse)
def update_sealed(product_id: int, data: SealedProductUpdate, db: Session = Depends(get_db)):
    product = _product_or_404(product_id, db)
    updated = data.model_dump(exclude_unset=True)
    # Leer/Whitespace fängt bereits der Schema-Validator (_validate_name) ab.
    # Bleibt der eine Fall, den ein Optional-Feld nicht ausdrücken kann:
    # explizites {"name": null} → name ist NOT NULL, sonst IntegrityError/500. #38
    if "name" in updated and updated["name"] is None:
        raise HTTPException(status_code=422, detail="Name darf nicht leer sein")
    # set_codes getrennt behandeln: None = unverändert, [] = alle entfernen.
    new_sets = updated.pop("set_codes", None)
    for field, value in updated.items():
        setattr(product, field, value)
    if new_sets is not None:
        _replace_sets(db, product_id, new_sets)
    db.commit()
    db.refresh(product)
    return _response(product, _sets_by_products(db, [product_id]).get(product_id, []))


@router.delete("/{product_id}", status_code=204)
def delete_sealed(product_id: int, db: Session = Depends(get_db)):
    product = _product_or_404(product_id, db)
    # Join-Zeilen explizit räumen (nicht auf DB-CASCADE verlassen — SQLite
    # erzwingt FKs nicht; hier Postgres, aber defensiv, feedback_tests_migrierte_db).
    db.execute(
        delete(sealed_product_sets).where(
            sealed_product_sets.c.sealed_product_id == product_id
        )
    )
    # Atomar (#38): alles in EINEM Commit, Dateien erst NACH dem Commit löschen.
    image_paths = clear_sealed_image(product)
    db.delete(product)
    db.commit()
    unlink_media_files(image_paths)


# ── Bild ──────────────────────────────────────────────────────────────────────

@router.post("/{product_id}/image", response_model=SealedProductResponse)
async def upload_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    product = _product_or_404(product_id, db)
    try:
        product = store_sealed_image(db, product, file)
    except ImageValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    # Service ist commit-frei (#38); Router steuert Atomarität: erst DB durabel,
    # DANN Endungswechsel-Waisen entfernen (nie Datei vor DB löschen).
    db.commit()
    cleanup_sealed_orphans(product)
    db.refresh(product)
    return _response(product, _sets_by_products(db, [product_id]).get(product_id, []))


@router.delete("/{product_id}/image", response_model=SealedProductResponse)
def delete_image(product_id: int, db: Session = Depends(get_db)):
    product = _product_or_404(product_id, db)
    # Erst DB-Felder leeren + committen, dann die Dateien entfernen (#38).
    # unlink VOR refresh — so läuft das Aufräumen auch, falls refresh scheitert.
    image_paths = clear_sealed_image(product)
    db.commit()
    unlink_media_files(image_paths)
    db.refresh(product)
    return _response(product, _sets_by_products(db, [product_id]).get(product_id, []))
