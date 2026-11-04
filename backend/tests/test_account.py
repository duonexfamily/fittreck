from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message
from fastapi.testclient import TestClient

from app.bot.routers import account
from app.main import app

client = TestClient(app)


def _callback(action: str) -> tuple[SimpleNamespace, account.DeleteCallback]:
    data = account.DeleteCallback(action=action)
    # Методы Message синхронные и возвращают объект запроса, поэтому edit_text подменяем отдельно
    message = MagicMock(spec=Message)
    message.edit_text = AsyncMock()
    callback = SimpleNamespace(from_user=SimpleNamespace(id=7), message=message, answer=AsyncMock())
    return callback, data


async def test_delete_asks_confirmation() -> None:
    message = SimpleNamespace(answer=AsyncMock())
    await account.cmd_delete_me(message)  # type: ignore[arg-type]
    kwargs = message.answer.await_args.kwargs
    buttons = kwargs["reply_markup"].inline_keyboard[0]
    assert [b.callback_data for b in buttons] == ["del:confirm", "del:cancel"]


async def test_cancel_keeps_data(monkeypatch: pytest.MonkeyPatch) -> None:
    delete = AsyncMock()
    monkeypatch.setattr(account, "delete_user", delete)
    callback, data = _callback("cancel")

    await account.on_delete_button(callback, data, session=AsyncMock())  # type: ignore[arg-type]

    delete.assert_not_awaited()
    assert callback.message.edit_text.await_args.args[0] == account.CANCELLED_TEXT


async def test_confirm_deletes_user_who_pressed(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=1)
    lookup = AsyncMock(return_value=user)
    delete = AsyncMock()
    monkeypatch.setattr(account, "get_by_telegram_id", lookup)
    monkeypatch.setattr(account, "delete_user", delete)
    callback, data = _callback("confirm")

    await account.on_delete_button(callback, data, session=AsyncMock())  # type: ignore[arg-type]

    assert lookup.await_args.args[1] == 7
    assert delete.await_args.args[1] is user
    assert callback.message.edit_text.await_args.args[0] == account.DELETED_TEXT


def test_delete_me_endpoint_requires_auth() -> None:
    assert client.delete("/api/v1/me").status_code == 401
