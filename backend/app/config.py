from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://redis:6379"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Cardmarket-OAuth ist seit v0.7.0 nur noch optionaler Preis-Fallback –
    # Primärquelle für Preise ist TCGdex (kein Key nötig).
    cardmarket_app_token: str = ""
    cardmarket_app_secret: str = ""
    cardmarket_access_token: str = ""
    cardmarket_access_secret: str = ""

    pokemontcg_api_key: str = ""

    # Optional: aktiviert die stärkere Scan-Variante B (Gemini). Default aus.
    gemini_api_key: str = ""

    images_dir: str = "/app/images"

    class Config:
        env_file = ".env"


settings = Settings()
