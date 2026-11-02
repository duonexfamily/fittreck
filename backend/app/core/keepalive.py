"""Самопинг для бесплатного хостинга.

Render усыпляет бесплатный сервис после 15 минут без входящих запросов, а Supabase
ставит на паузу базу без активности за неделю. Раз в N минут обращаемся к своему
/health через публичный адрес (это входящий запрос для Render) и делаем SELECT 1 в БД.
"""

import asyncio
import logging

import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


async def keepalive_loop(
    url: str, sessionmaker: async_sessionmaker[AsyncSession], minutes: int
) -> None:
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as http:
        while True:
            await asyncio.sleep(minutes * 60)
            # Ошибка одного пинга не должна останавливать цикл
            try:
                async with http.get(f"{url}/health") as response:
                    if response.status != 200:
                        logger.warning("Самопинг: /health ответил %s", response.status)
                async with sessionmaker() as session:
                    await session.execute(text("SELECT 1"))
            except Exception:
                logger.warning("Самопинг не удался", exc_info=True)
