from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Eine Projektversion pro Dev-Stand (nicht getrennt nach Front-/Backend).
    # Spiegelt web/src/lib/version.ts › APP_VERSION; bei jedem Release beide
    # hochzählen. Per Env-Var APP_VERSION überschreibbar.
    app_version: str = "1.3.0"

    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    # 30 Tage (Lock-Spec Issue #1): Single-User-LAN-App, keine Revocation —
    # der Web-Client hält das Token in localStorage und loggt sich bei 401 neu ein.
    jwt_expire_minutes: int = 60 * 24 * 30  # 30 Tage

    # Erlaubte CORS-Origins, kommagetrennt (Env CORS_ORIGINS). Leer/ungesetzt →
    # Default: Prod-Web (3011) + lokaler Teststand (3021). Kein "*" mehr —
    # seit Auth-Zwang (Issue #1) wäre eine Wildcard-Origin ein unnötiges Risiko.
    cors_origins: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return origins or ["http://localhost:3011", "http://localhost:3021"]

    # Cardmarket-OAuth ist seit v0.7.0 nur noch optionaler Preis-Fallback –
    # Primärquelle für Preise ist TCGdex (kein Key nötig).
    cardmarket_app_token: str = ""
    cardmarket_app_secret: str = ""
    cardmarket_access_token: str = ""
    cardmarket_access_secret: str = ""


    # Optional: aktiviert die stärkere Scan-Variante B (Gemini). Default aus.
    # Ist der Key gesetzt, nutzt der Scan Gemini; sonst lokale OCR als Fallback.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    images_dir: str = "/app/images"

    class Config:
        env_file = ".env"


settings = Settings()
