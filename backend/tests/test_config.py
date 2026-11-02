import re

import pytest

from app.core.config import Settings
from tests.conftest import TEST_BOT_TOKEN


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@host:5432/db",
        "postgres://u:p@host:5432/db",
        "postgresql+asyncpg://u:p@host:5432/db",
    ],
)
def test_database_url_uses_asyncpg(url: str) -> None:
    settings = Settings(bot_token=TEST_BOT_TOKEN, database_url=url)
    assert settings.database_url.get_secret_value() == "postgresql+asyncpg://u:p@host:5432/db"


def test_prod_requires_webhook_secret() -> None:
    with pytest.raises(ValueError, match="WEBHOOK_SECRET"):
        Settings(
            env="prod",
            bot_token=TEST_BOT_TOKEN,
            database_url="postgresql://u:p@host/db",
            webapp_url="https://example.up.railway.app",
        )


def test_webhook_token_is_telegram_safe() -> None:
    # Секрет в духе генератора Render: base64 с символами, которые Telegram не принимает
    settings = Settings(
        env="prod",
        bot_token="1:x",
        database_url="postgresql://u:p@h/db",
        webhook_secret="ab+/cd==",
        webapp_url="https://x.onrender.com",
    )
    token = settings.webhook_token
    assert token is not None
    assert re.fullmatch(r"[0-9a-f]{64}", token)


def test_render_external_url_is_used_as_webapp_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WEBAPP_URL", raising=False)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://fittrack.onrender.com/")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.webapp_url == "https://fittrack.onrender.com"
