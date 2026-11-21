"""backfill platform audit

Revision ID: f76e6a0f4eb9
Revises: f75d5f9e3da8
"""
from typing import Sequence, Union

from alembic import op

revision: str = "f76e6a0f4eb9"
down_revision: Union[str, None] = "f75d5f9e3da8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """INSERT INTO platform_audit_logs
        (id, platform_admin_id, tenant_id, action, description, details, created_at, updated_at)
        SELECT gen_random_uuid(), NULL, tenants.id, 'tenant.created',
        'Registro histórico de la empresa ' || tenants.name || '.',
        jsonb_build_object('plan_key', tenants.plan_key, 'source', 'historical_backfill'),
        tenants.created_at, tenants.created_at
        FROM tenants
        WHERE NOT EXISTS (
            SELECT 1 FROM platform_audit_logs logs
            WHERE logs.tenant_id = tenants.id AND logs.action = 'tenant.created'
        )"""
    )


def downgrade() -> None:
    op.execute(
        """DELETE FROM platform_audit_logs
        WHERE details->>'source' = 'historical_backfill'"""
    )
