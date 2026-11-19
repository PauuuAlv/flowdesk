"""add saas subscriptions

Revision ID: f61d0a4f8e53
Revises: f51c9f3e7d42
"""
from alembic import op
import sqlalchemy as sa

revision = "f61d0a4f8e53"
down_revision = "f51c9f3e7d42"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tenants", sa.Column("plan_key", sa.String(30), nullable=False, server_default="basic"))
    op.add_column("tenants", sa.Column("subscription_status", sa.String(30), nullable=False, server_default="trial"))
    op.add_column("tenants", sa.Column("max_users", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("tenants", sa.Column("max_clients", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("tenants", sa.Column("max_products", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("tenants", sa.Column("subscription_started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column("tenants", sa.Column("subscription_renews_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_tenants_plan_key"), "tenants", ["plan_key"])
    op.create_index(op.f("ix_tenants_subscription_status"), "tenants", ["subscription_status"])


def downgrade():
    op.drop_index(op.f("ix_tenants_subscription_status"), table_name="tenants")
    op.drop_index(op.f("ix_tenants_plan_key"), table_name="tenants")
    for name in ("subscription_renews_at", "subscription_started_at", "max_products", "max_clients", "max_users", "subscription_status", "plan_key"):
        op.drop_column("tenants", name)
