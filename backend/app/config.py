from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://redis:6379"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    cardmarket_app_token: str = ""
    cardmarket_app_secret: str = ""
    cardmarket_access_token: str = ""
    cardmarket_access_secret: str = ""

    pokemontcg_api_key: str = ""

    images_dir: str = "/app/images"

    class Config:
        env_file = ".env"


settings = Settings()
