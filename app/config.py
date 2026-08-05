from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "dev"
    DATABASE_URL: str = "${DATABASE_URL}"

    @field_validator("DATABASE_URL")
    @classmethod
    def _force_asyncpg(cls, v: str) -> str:
        # Accept plain `postgresql://` / `postgres://` (what Supabase/Heroku hand out)
        # and rewrite to the asyncpg driver our stack uses.
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v[len("postgresql://"):]
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://"):]
        return v
    TEST_DATABASE_URL: str | None = None
    JWT_SECRET: str = "${JWT_SECRET}"
    JWT_ALGORITHM: str = "${JWT_ALGORITHM}"
    CLERK_JWKS_URL: str | None = None
    AMFI_BASE_URL: str = "https://api.mfapi.in"
    CORS_ORIGINS: str = "http://localhost:5173"
    AI_MODEL: str = "gpt-4.1-nano-2025-04-14"
    AI_NEWS_CACHE_TTL_HOURS: int = 24


settings = Settings()
