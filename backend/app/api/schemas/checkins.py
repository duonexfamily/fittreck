import datetime as dt

from pydantic import BaseModel, Field, model_validator


class CheckinIn(BaseModel):
    """Чек-ин заменяется целиком: не переданное поле очищается. Оценки 1–5."""

    bed_time: dt.time | None = None
    wake_time: dt.time | None = None
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    energy: int | None = Field(default=None, ge=1, le=5)
    stress: int | None = Field(default=None, ge=1, le=5)
    mood: int | None = Field(default=None, ge=1, le=5)
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _check(self) -> "CheckinIn":
        if (self.bed_time is None) != (self.wake_time is None):
            raise ValueError("укажите и время отхода ко сну, и время подъёма")
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("чек-ин пустой")
        return self


class CheckinOut(BaseModel):
    date: dt.date
    bed_time: dt.time | None
    wake_time: dt.time | None
    # Длительность сна — по bed_time и wake_time
    sleep_minutes: int | None
    sleep_quality: int | None
    energy: int | None
    stress: int | None
    mood: int | None
    note: str | None
