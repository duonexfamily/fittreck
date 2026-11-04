"""user_settings, reminder_log

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[sa.DateTime]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "reminders",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_settings_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_settings")),
        sa.UniqueConstraint("user_id", name=op.f("uq_user_settings_user_id")),
    )
    op.execute("ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "reminder_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("sent_on", sa.Date(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_reminder_log_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reminder_log")),
        sa.UniqueConstraint("user_id", "type", "sent_on", name=op.f("uq_reminder_log_user_id")),
    )
    op.create_index(op.f("ix_reminder_log_user_id"), "reminder_log", ["user_id"])
    # Выборка «что уже обработано за последние дни» — по дате
    op.create_index(op.f("ix_reminder_log_sent_on"), "reminder_log", ["sent_on"])
    op.execute("ALTER TABLE reminder_log ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index(op.f("ix_reminder_log_sent_on"), table_name="reminder_log")
    op.drop_index(op.f("ix_reminder_log_user_id"), table_name="reminder_log")
    op.drop_table("reminder_log")
    op.drop_table("user_settings")
