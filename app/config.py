from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "dev"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/finance"
    TEST_DATABASE_URL: str | None = None
    JWT_SECRET: str = "dev-insecure-change-me"
    JWT_ALGORITHM: str = "HS256"
    CLERK_JWKS_URL: str | None = None
    AMFI_BASE_URL: str = "https://api.mfapi.in"
    CORS_ORIGINS: str = "http://localhost:5173"


settings = Settings()
