import json
import os
import time
from urllib.parse import urlencode

import pytest

# Тестовые настройки — до импорта приложения. Реальные токены в тестах не нужны
TEST_BOT_TOKEN = "123456:TEST-token-for-tests-only"
os.environ.update(
    {
        "ENV": "dev",
        "BOT_TOKEN": TEST_BOT_TOKEN,
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "WEBAPP_URL": "",
    }
)

from app.core.security import sign_init_data  # noqa: E402


def make_init_data(
    user_id: int = 42,
    auth_date: int | None = None,
    bot_token: str = TEST_BOT_TOKEN,
) -> str:
    """Собирает initData, подписанный так же, как это делает Telegram."""
    fields = {
        "auth_date": str(int(time.time()) if auth_date is None else auth_date),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps({"id": user_id, "first_name": "Тест", "username": "tester"}),
    }
    fields["hash"] = sign_init_data(fields, bot_token)
    return urlencode(fields)


@pytest.fixture
def init_data() -> str:
    return make_init_data()
