"""checkins

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "checkins",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("bed_time", sa.Time(), nullable=True),
        sa.Column("wake_time", sa.Time(), nullable=True),
        sa.Column("sleep_quality", sa.SmallInteger(), nullable=True),
        sa.Column("energy", sa.SmallInteger(), nullable=True),
        sa.Column("stress", sa.SmallInteger(), nullable=True),
        sa.Column("mood", sa.SmallInteger(), nullable=True),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_checkins_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_checkins")),
        sa.UniqueConstraint("user_id", "date", name=op.f("uq_checkins_user_id")),
    )
    op.create_index(op.f("ix_checkins_user_id"), "checkins", ["user_id"])
    op.execute("ALTER TABLE checkins ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("checkins")
