import hashlib
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения и backend/.env."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )

    env: Literal["dev", "prod"] = "dev"
    bot_token: SecretStr
    webhook_secret: SecretStr | None = None
    database_url: SecretStr
    # Render сам задаёт RENDER_EXTERNAL_URL — адрес сервиса. WEBAPP_URL важнее, если задан
    webapp_url: str = Field(
        default="", validation_alias=AliasChoices("WEBAPP_URL", "RENDER_EXTERNAL_URL")
    )
    admin_ids: Annotated[list[int], NoDecode] = Field(default_factory=list)
    log_level: str = "INFO"
    # Самопинг раз в N минут, чтобы бесплатный хостинг не усыплял сервис. 0 — выключено
    keepalive_minutes: int = Field(default=0, ge=0)

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
    def webhook_token(self) -> str | None:
        """Значение X-Telegram-Bot-Api-Secret-Token.

        Telegram допускает в нём только A-Z, a-z, 0-9, _ и -, а сгенерированный хостингом
        секрет может содержать +/=. Поэтому передаём SHA-256 от секрета в hex.
        """
        if self.webhook_secret is None or not self.webhook_secret.get_secret_value():
            return None
        return hashlib.sha256(self.webhook_secret.get_secret_value().encode()).hexdigest()

    @property
    def webapp_is_https(self) -> bool:
        # Telegram открывает Mini App только по HTTPS
        return self.webapp_url.startswith("https://")


@lru_cache
def get_settings() -> Settings:
    return Settings()
