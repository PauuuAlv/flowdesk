"""add opportunity stage history and real close date

Revision ID: f72a2c6b0a75
Revises: f71e1b5a9f64
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f72a2c6b0a75"
down_revision: Union[str, None] = "f71e1b5a9f64"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_opportunities_closed_at", "opportunities", ["closed_at"])
    op.create_table(
        "opportunity_stage_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_stage_key", sa.String(length=50), nullable=True),
        sa.Column("to_stage_key", sa.String(length=50), nullable=False),
        sa.Column("probability", sa.Integer(), nullable=False),
        sa.Column("expected_close_date", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunity_stage_history_tenant_id", "opportunity_stage_history", ["tenant_id"])
    op.create_index("ix_opportunity_stage_history_opportunity_id", "opportunity_stage_history", ["opportunity_id"])
    op.create_index("ix_opportunity_stage_history_changed_by_user_id", "opportunity_stage_history", ["changed_by_user_id"])
    op.execute("""
        INSERT INTO opportunity_stage_history
            (id, tenant_id, opportunity_id, from_stage_key, to_stage_key, probability,
             expected_close_date, note, changed_by_user_id, created_at, updated_at)
        SELECT gen_random_uuid(), tenant_id, id, NULL, stage, probability,
               expected_close_date, 'Estado inicial migrado', owner_user_id, created_at, updated_at
        FROM opportunities
    """)
    op.execute("""
        UPDATE opportunities
        SET closed_at = updated_at
        WHERE stage IN ('won', 'lost') AND closed_at IS NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_opportunity_stage_history_changed_by_user_id", table_name="opportunity_stage_history")
    op.drop_index("ix_opportunity_stage_history_opportunity_id", table_name="opportunity_stage_history")
    op.drop_index("ix_opportunity_stage_history_tenant_id", table_name="opportunity_stage_history")
    op.drop_table("opportunity_stage_history")
    op.drop_index("ix_opportunities_closed_at", table_name="opportunities")
    op.drop_column("opportunities", "closed_at")
