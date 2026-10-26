from pydantic import BaseModel, field_validator

from app.schemas._validators import require_utf8


class LoginRequest(BaseModel):
    username: str
    password: str

    # #117: nicht kodierbares Passwort → 422 statt 500 aus bcrypt
    _v_utf8 = field_validator("*", mode="before")(require_utf8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
