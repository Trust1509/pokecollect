from typing import Optional
from pydantic import BaseModel


class CatalogItem(BaseModel):
    card_id: str
    set_id: Optional[str] = None
    set_code: Optional[str] = None
    set_name: Optional[str] = None
    local_id: Optional[str] = None
    name: Optional[str] = None
    name_en: Optional[str] = None
    dex_id: Optional[int] = None
    rarity: Optional[str] = None
    illustrator: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    variants_normal: Optional[bool] = None
    variants_reverse: Optional[bool] = None
    variants_holo: Optional[bool] = None
    variants_firstedition: Optional[bool] = None
    enriched: Optional[bool] = None
    owned: bool = False
    in_pokedex: bool = False

    model_config = {"from_attributes": True}


class CatalogListResponse(BaseModel):
    items: list[CatalogItem]
    total: int
    page: int
    limit: int
    pages: int
