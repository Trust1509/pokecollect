from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Eine Projektversion pro Dev-Stand (nicht getrennt nach Front-/Backend).
    # Spiegelt web/src/lib/version.ts › APP_VERSION; bei jedem Release beide
    # hochzählen. Per Env-Var APP_VERSION überschreibbar.
    app_version: str = "0.9.14"

    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

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
