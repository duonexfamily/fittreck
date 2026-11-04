"""seed system exercises

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-04

Системный каталог упражнений (owner_id = NULL).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (название, группа мышц, вид)
EXERCISES: list[tuple[str, str, str]] = [
    # Грудь
    ("Жим штанги лёжа", "chest", "strength"),
    ("Жим штанги на наклонной скамье", "chest", "strength"),
    ("Жим гантелей лёжа", "chest", "strength"),
    ("Жим гантелей на наклонной скамье", "chest", "strength"),
    ("Разводка гантелей лёжа", "chest", "strength"),
    ("Сведение рук в кроссовере", "chest", "strength"),
    ("Отжимания от пола", "chest", "strength"),
    ("Отжимания на брусьях", "chest", "strength"),
    ("Жим в тренажёре от груди", "chest", "strength"),
    # Спина
    ("Подтягивания", "back", "strength"),
    ("Тяга верхнего блока к груди", "back", "strength"),
    ("Тяга штанги в наклоне", "back", "strength"),
    ("Тяга гантели в наклоне одной рукой", "back", "strength"),
    ("Тяга горизонтального блока", "back", "strength"),
    ("Становая тяга", "back", "strength"),
    ("Гиперэкстензия", "back", "strength"),
    ("Пуловер с гантелью", "back", "strength"),
    # Плечи
    ("Жим штанги стоя", "shoulders", "strength"),
    ("Жим гантелей сидя", "shoulders", "strength"),
    ("Махи гантелями в стороны", "shoulders", "strength"),
    ("Махи гантелями в наклоне", "shoulders", "strength"),
    ("Подъём гантелей перед собой", "shoulders", "strength"),
    ("Тяга штанги к подбородку", "shoulders", "strength"),
    ("Шраги с гантелями", "shoulders", "strength"),
    # Руки
    ("Подъём штанги на бицепс", "arms", "strength"),
    ("Подъём гантелей на бицепс", "arms", "strength"),
    ("Молотки с гантелями", "arms", "strength"),
    ("Сгибание рук на скамье Скотта", "arms", "strength"),
    ("Французский жим лёжа", "arms", "strength"),
    ("Разгибание рук на блоке", "arms", "strength"),
    ("Жим штанги узким хватом", "arms", "strength"),
    ("Обратные отжимания от скамьи", "arms", "strength"),
    # Ноги
    ("Приседания со штангой", "legs", "strength"),
    ("Приседания без веса", "legs", "strength"),
    ("Гоблет-приседания с гантелью", "legs", "strength"),
    ("Жим ногами в тренажёре", "legs", "strength"),
    ("Выпады с гантелями", "legs", "strength"),
    ("Болгарские сплит-приседания", "legs", "strength"),
    ("Румынская тяга", "legs", "strength"),
    ("Разгибание ног в тренажёре", "legs", "strength"),
    ("Сгибание ног в тренажёре", "legs", "strength"),
    ("Ягодичный мост со штангой", "legs", "strength"),
    ("Подъём на носки стоя", "legs", "strength"),
    # Кор
    ("Скручивания", "core", "strength"),
    ("Подъём ног в висе", "core", "strength"),
    ("Обратные скручивания", "core", "strength"),
    ("Русские скручивания", "core", "strength"),
    ("Планка", "core", "stretch"),
    ("Боковая планка", "core", "stretch"),
    # Всё тело
    ("Берпи", "full_body", "strength"),
    ("Махи гирей", "full_body", "strength"),
    ("Толчок гири", "full_body", "strength"),
    # Кардио
    ("Бег", "full_body", "cardio"),
    ("Бег на дорожке", "full_body", "cardio"),
    ("Ходьба", "full_body", "cardio"),
    ("Велосипед", "legs", "cardio"),
    ("Велотренажёр", "legs", "cardio"),
    ("Эллипсоид", "full_body", "cardio"),
    ("Гребной тренажёр", "full_body", "cardio"),
    ("Плавание", "full_body", "cardio"),
    ("Скакалка", "full_body", "cardio"),
    ("Лестница (степпер)", "legs", "cardio"),
    # Растяжка
    ("Растяжка всего тела", "full_body", "stretch"),
    ("Растяжка задней поверхности бедра", "legs", "stretch"),
    ("Растяжка грудных мышц", "chest", "stretch"),
    ("Растяжка спины (поза ребёнка)", "back", "stretch"),
    ("Йога", "full_body", "stretch"),
]

exercises = sa.table(
    "exercises",
    sa.column("name", sa.String),
    sa.column("muscle_group", sa.String),
    sa.column("kind", sa.String),
    sa.column("owner_id", sa.BigInteger),
)


def upgrade() -> None:
    op.bulk_insert(
        exercises,
        [
            {"name": name, "muscle_group": muscle, "kind": kind, "owner_id": None}
            for name, muscle, kind in EXERCISES
        ],
    )


def downgrade() -> None:
    # Подходы с этими упражнениями удалятся каскадом
    op.execute(
        exercises.delete().where(
            exercises.c.owner_id.is_(None), exercises.c.name.in_([e[0] for e in EXERCISES])
        )
    )
