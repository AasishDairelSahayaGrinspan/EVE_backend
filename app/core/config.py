"""Application settings loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://dairel@localhost:5432/eve"
    TEST_DATABASE_URL: str = "postgresql+psycopg://dairel@localhost:5432/eve_test"
    JWT_SECRET: str = "change-me-to-a-long-random-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    ENVIRONMENT: str = "dev"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def require_secret(self) -> None:
        # Fail fast if a default/weak secret is used outside dev/test.
        if self.ENVIRONMENT not in {"dev", "test"} and self.JWT_SECRET.startswith("change-me"):
            raise RuntimeError("JWT_SECRET must be set to a strong value in this environment")


@lru_cache
def get_settings() -> Settings:
    return Settings()
