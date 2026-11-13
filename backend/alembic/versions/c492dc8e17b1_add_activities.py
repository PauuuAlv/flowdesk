"""add activities

Revision ID: c492dc8e17b1
Revises: b718a5c309d2
Create Date: 2026-11-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c492dc8e17b1"
down_revision: Union[str, None] = "b718a5c309d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("activities",
        sa.Column("client_id",sa.UUID(),nullable=False),sa.Column("opportunity_id",sa.UUID(),nullable=True),
        sa.Column("owner_user_id",sa.UUID(),nullable=False),sa.Column("activity_type",sa.String(20),nullable=False),
        sa.Column("title",sa.String(140),nullable=False),sa.Column("description",sa.Text(),nullable=True),
        sa.Column("scheduled_at",sa.DateTime(timezone=True),nullable=False),sa.Column("status",sa.String(20),nullable=False),
        sa.Column("completed_at",sa.DateTime(timezone=True),nullable=True),sa.Column("id",sa.UUID(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("now()")),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.text("now()")),
        sa.Column("tenant_id",sa.UUID(),nullable=False),sa.ForeignKeyConstraint(["client_id"],["clients.id"]),
        sa.ForeignKeyConstraint(["opportunity_id"],["opportunities.id"]),sa.ForeignKeyConstraint(["owner_user_id"],["users.id"]),sa.PrimaryKeyConstraint("id"))
    for column in ("client_id","opportunity_id","owner_user_id","activity_type","scheduled_at","status","tenant_id"):
        op.create_index(op.f(f"ix_activities_{column}"),"activities",[column])
    op.execute("""INSERT INTO role_permissions (role_id,permission_code) SELECT id,permission FROM roles CROSS JOIN LATERAL unnest(ARRAY['activities.view','activities.create','activities.update','activities.complete']) permission WHERE origin='template' ON CONFLICT DO NOTHING""")


def downgrade() -> None:
    op.execute("DELETE FROM role_permissions WHERE permission_code LIKE 'activities.%'")
    op.drop_table("activities")
