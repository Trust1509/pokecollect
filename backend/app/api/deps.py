from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.config import settings

bearer = HTTPBearer(auto_error=False)


# ACHTUNG: Wird aktuell von KEINEM Endpoint verwendet – die API ist im LAN
# offen, extern schützt Authelia (siehe deploy/README). Für v1.0 vorgesehen:
# Login-Seite im Web + dependencies=[Depends(require_auth)] auf den Routern
# (Bild-Routen ausgenommen, da <img> keine Authorization-Header senden kann).
def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nicht eingeloggt")
    try:
        jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ungültiges Token")
