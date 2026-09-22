from urllib.parse import quote_plus

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database (compose from parts; never put the password in a URL) ---
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "db"
    postgres_port: int = 5432

    # --- Test database (runs on host; different port, same password) ---
    test_postgres_host: str = "localhost"
    test_postgres_port: int = 5433
    test_postgres_db: str = "notes_test"

    # --- App ---
    secret_key: str
    db_pool_size: int = 5
    db_max_overflow: int = 10
    log_level: str = "INFO"
    environment: str = "development"

    # Optional. Set to "require" for managed databases like Neon.
    postgres_sslmode: str | None = None

    redis_url: str = "redis://redis:6379/0"

    @computed_field
    @property
    def database_url(self) -> str:
        pwd = quote_plus(self.postgres_password)
        url = (
            f"postgresql+psycopg://{self.postgres_user}:{pwd}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
        if self.postgres_sslmode:
            url += f"?sslmode={self.postgres_sslmode}"
        return url

    @computed_field
    @property
    def test_database_url(self) -> str:
        pwd = quote_plus(self.postgres_password)
        url = (
            f"postgresql+psycopg://{self.postgres_user}:{pwd}"
            f"@{self.test_postgres_host}:{self.test_postgres_port}/{self.test_postgres_db}"
        )
        if self.postgres_sslmode:
            url += f"?sslmode={self.postgres_sslmode}"
        return url

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()