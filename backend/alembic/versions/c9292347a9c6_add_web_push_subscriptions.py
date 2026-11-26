"""suscripciones Web Push y control de envío de notificaciones

Crea push_subscriptions (una fila por navegador suscrito) y agrega
notifications.push_sent_at. Las notificaciones que ya existían se marcan como
procesadas para que, al activar Web Push, no llegue de golpe todo el historial.

Revision ID: c9292347a9c6
Revises: c3d4e5f6a7b8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c9292347a9c6"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.String(255), nullable=False),
        sa.Column("auth", sa.String(255), nullable=False),
        sa.Column("user_agent", sa.String(300), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint", name="uq_push_subscriptions_endpoint"),
    )
    op.create_index("ix_push_subscriptions_tenant_id", "push_subscriptions", ["tenant_id"])
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])

    op.add_column("notifications", sa.Column("push_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_notifications_push_sent_at", "notifications", ["push_sent_at"])
    op.execute("UPDATE notifications SET push_sent_at = now() WHERE push_sent_at IS NULL")


def downgrade() -> None:
    op.drop_index("ix_notifications_push_sent_at", table_name="notifications")
    op.drop_column("notifications", "push_sent_at")
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_tenant_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
