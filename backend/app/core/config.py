from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения и backend/.env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["dev", "prod"] = "dev"
    bot_token: SecretStr
    webhook_secret: SecretStr | None = None
    database_url: SecretStr
    webapp_url: str = ""
    admin_ids: Annotated[list[int], NoDecode] = Field(default_factory=list)
    log_level: str = "INFO"

    # Сколько секунд initData считается действительным
    init_data_max_age: int = 24 * 60 * 60

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _split_admin_ids(cls, value: object) -> object:
        if isinstance(value, str):
            return [int(item) for item in value.split(",") if item.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def _use_asyncpg(cls, value: object) -> object:
        # Railway выдаёт postgresql:// — драйверу нужен postgresql+asyncpg://
        if isinstance(value, str):
            for prefix in ("postgresql://", "postgres://"):
                if value.startswith(prefix):
                    return "postgresql+asyncpg://" + value.removeprefix(prefix)
        return value

    @field_validator("webapp_url")
    @classmethod
    def _strip_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @model_validator(mode="after")
    def _check_prod(self) -> "Settings":
        # В продакшене без секрета webhook и HTTPS-адреса запуск запрещён
        if self.env == "prod":
            if not self.webhook_secret or not self.webhook_secret.get_secret_value():
                raise ValueError("WEBHOOK_SECRET обязателен при ENV=prod")
            if not self.webapp_url.startswith("https://"):
                raise ValueError("WEBAPP_URL должен начинаться с https:// при ENV=prod")
        return self

    @property
    def webapp_is_https(self) -> bool:
        # Telegram открывает Mini App только по HTTPS
        return self.webapp_url.startswith("https://")


@lru_cache
def get_settings() -> Settings:
    return Settings()
