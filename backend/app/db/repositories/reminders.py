from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ReminderLog, User, UserSettings


class ReminderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_reminders(self, user_id: int) -> dict[str, Any]:
        result = await self.session.execute(
            select(UserSettings.reminders).where(UserSettings.user_id == user_id)
        )
        return result.scalar_one_or_none() or {}

    async def save_reminders(self, user_id: int, reminders: dict[str, Any]) -> None:
        stmt = insert(UserSettings).values(user_id=user_id, reminders=reminders)
        stmt = stmt.on_conflict_do_update(
            index_elements=[UserSettings.user_id],
            set_={"reminders": stmt.excluded.reminders, "updated_at": func.now()},
        )
        await self.session.execute(stmt)

    async def list_recipients(self) -> list[tuple[User, dict[str, Any]]]:
        """Пользователи, прошедшие анкету, и их настройки напоминаний."""
        result = await self.session.execute(
            select(User, UserSettings.reminders)
            .outerjoin(UserSettings, UserSettings.user_id == User.id)
            .where(User.onboarded_at.is_not(None))
        )
        return [(user, reminders or {}) for user, reminders in result.tuples()]

    async def handled_since(self, since: date) -> set[tuple[int, str, date]]:
        """Что уже обработано начиная с даты: (user_id, type, sent_on)."""
        result = await self.session.execute(
            select(ReminderLog.user_id, ReminderLog.type, ReminderLog.sent_on).where(
                ReminderLog.sent_on >= since
            )
        )
        return set(result.tuples())

    async def mark_handled(self, user_id: int, type_: str, day: date) -> bool:
        """Отмечает напоминание за день. False — его уже отметил кто-то другой."""
        stmt = (
            insert(ReminderLog)
            .values(user_id=user_id, type=type_, sent_on=day)
            .on_conflict_do_nothing(
                index_elements=[ReminderLog.user_id, ReminderLog.type, ReminderLog.sent_on]
            )
            .returning(ReminderLog.id)
        )
        result = await self.session.execute(stmt)
        return result.first() is not None
