"""Проверка initData Telegram Mini App.

Алгоритм: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

# Допуск на расхождение часов между Telegram и сервером
CLOCK_SKEW_SECONDS = 60


class InitDataError(Exception):
    """initData отсутствует, подделан или устарел."""


@dataclass(frozen=True, slots=True)
class TelegramUser:
    id: int
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def sign_init_data(fields: dict[str, str], bot_token: str) -> str:
    """Подписывает поля как Telegram. Нужна для тестов."""
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    return hmac.new(_secret_key(bot_token), data_check_string.encode(), hashlib.sha256).hexdigest()


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age: int,
    now: float | None = None,
) -> TelegramUser:
    """Проверяет подпись и срок initData, возвращает пользователя Telegram."""
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise InitDataError("initData не разбирается") from exc

    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise InitDataError("повторяющиеся поля в initData")

    received_hash = fields.pop("hash", None)
    if not received_hash:
        raise InitDataError("нет hash")

    expected_hash = sign_init_data(fields, bot_token)
    if not hmac.compare_digest(expected_hash, received_hash):
        raise InitDataError("неверная подпись")

    try:
        auth_date = int(fields["auth_date"])
    except (KeyError, ValueError) as exc:
        raise InitDataError("нет auth_date") from exc

    current = time.time() if now is None else now
    if auth_date > current + CLOCK_SKEW_SECONDS or current - auth_date > max_age:
        raise InitDataError("initData устарел")

    try:
        raw_user = json.loads(fields["user"])
        return TelegramUser(
            id=int(raw_user["id"]),
            first_name=str(raw_user.get("first_name", "")),
            last_name=raw_user.get("last_name"),
            username=raw_user.get("username"),
            language_code=raw_user.get("language_code"),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise InitDataError("нет данных пользователя") from exc
