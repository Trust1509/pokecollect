from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas._validators import reject_control_chars


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
    # code ist der Primärschlüssel, name NOT NULL — beide dürfen weder leer
    # sein noch Steuerzeichen tragen (#55: endete sonst als 500).
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    max_card_nr: Optional[int] = Field(default=None, ge=0, le=100000)
    set_id: Optional[str] = Field(default=None, max_length=64)

    _v_ctrl = field_validator("*", mode="before")(reject_control_chars)

    @field_validator("code", "name")
    @classmethod
    def _nicht_nur_leerzeichen(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Darf nicht leer sein")
        return v

