from typing import Optional
from pydantic import BaseModel


class PokemonSetResponse(BaseModel):
    code: str
    name: str
    max_card_nr: Optional[int] = None
    # TCGdex-Anreicherung
    set_id: Optional[str] = None
    name_en: Optional[str] = None
    series_id: Optional[str] = None
    card_count_official: Optional[int] = None
    card_count_total: Optional[int] = None
    logo_url: Optional[str] = None
    symbol_url: Optional[str] = None

    model_config = {"from_attributes": True}


class PokemonSetCreate(BaseModel):
    code: str
    name: str
    max_card_nr: Optional[int] = None
    set_id: Optional[str] = None


class PokemonSetUpdate(BaseModel):
    name: Optional[str] = None
    max_card_nr: Optional[int] = None
    set_id: Optional[str] = None
