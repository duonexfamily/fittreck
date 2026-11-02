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
