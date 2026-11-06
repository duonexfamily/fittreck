"""seed leg adduction/abduction exercises

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-06

Добавляет в системный каталог сведение и разведение ног в тренажёре.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (название, группа мышц, вид)
EXERCISES: list[tuple[str, str, str]] = [
    ("Сведение ног в тренажёре", "legs", "strength"),
    ("Разведение ног в тренажёре", "legs", "strength"),
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
