from typing import Optional
from pydantic import BaseModel


class PokemonSetResponse(BaseModel):
    code: str
    name: str
    max_card_nr: Optional[int] = None

    model_config = {"from_attributes": True}


class PokemonSetCreate(BaseModel):
    code: str
    name: str
    max_card_nr: Optional[int] = None


class PokemonSetUpdate(BaseModel):
    name: Optional[str] = None
    max_card_nr: Optional[int] = None
