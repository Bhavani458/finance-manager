from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "dev"
    DATABASE_URL: str = "${DATABASE_URL}"
    TEST_DATABASE_URL: str | None = None
    JWT_SECRET: str = "${JWT_SECRET}"
    JWT_ALGORITHM: str = "${JWT_ALGORITHM}"
    CLERK_JWKS_URL: str | None = None
    AMFI_BASE_URL: str = "https://api.mfapi.in"
    CORS_ORIGINS: str = "http://localhost:5173"
    AI_MODEL: str = "gpt-4.1-nano-2025-04-14"
    AI_NEWS_CACHE_TTL_HOURS: int = 24


settings = Settings()
