from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import InitDataError, TelegramUser, validate_init_data
from app.db.models import User
from app.services.users import register_user


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_telegram_user(
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
) -> TelegramUser:
    """Проверяет заголовок `Authorization: tma <initData>`. Без БД."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Нужна авторизация Telegram",
    )
    if not authorization:
        raise unauthorized

    scheme, _, init_data = authorization.partition(" ")
    if scheme.lower() != "tma" or not init_data:
        raise unauthorized

    try:
        return validate_init_data(
            init_data,
            settings.bot_token.get_secret_value(),
            settings.init_data_max_age,
        )
    except InitDataError as exc:
        raise unauthorized from exc


async def get_current_user(
    # Порядок важен: сначала проверка подписи, потом обращение к БД
    tg_user: Annotated[TelegramUser, Depends(get_telegram_user)],
    session: SessionDep,
) -> User:
    """Пользователь из проверенного initData. Другого способа узнать user_id нет."""
    return await register_user(session, tg_user)


CurrentUser = Annotated[User, Depends(get_current_user)]
