from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from app.config import settings

bearer = HTTPBearer(auto_error=False)


# Seit Issue #1 auf allen Fach-Routern verdrahtet (api/v1/__init__.py).
# Auth-frei bleiben nur /auth/login, /health und der /images-StaticFiles-Mount
# (<img> kann keine Authorization-Header senden).
def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nicht eingeloggt")
    try:
        jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ungültiges Token")
