"""Фоновые задачи бота: то, что пользователю ждать не нужно."""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)

# Держим ссылки на задачи, иначе сборщик мусора может прервать их на середине
_tasks: set[asyncio.Task[Any]] = set()


def _done(task: asyncio.Task[Any]) -> None:
    _tasks.discard(task)
    if not task.cancelled() and task.exception() is not None:
        logger.error("Ошибка в фоновой задаче", exc_info=task.exception())


def spawn(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
    """Запускает корутину в фоне и не ждёт её."""
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_done)
    return task


async def drain(wait_seconds: float = 5.0) -> None:
    """Дожидается фоновых задач при остановке приложения."""
    if _tasks:
        await asyncio.wait(set(_tasks), timeout=wait_seconds)
