from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    first_name: str
    username: str | None
    sex: str | None
    birth_date: date | None
    height_cm: int | None
    goal: str | None
    activity_level: str | None
    timezone: str
    onboarded_at: datetime | None
