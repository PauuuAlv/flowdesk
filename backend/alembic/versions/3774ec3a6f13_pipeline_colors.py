"""color por pipeline

Agrega pipelines.color (#rrggbb) para distinguir las actividades en el
calendario. Los pipelines existentes reciben un color de la paleta según su
orden dentro de su empresa.

Revision ID: 3774ec3a6f13
Revises: aba136754a4d
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "3774ec3a6f13"
down_revision: Union[str, None] = "aba136754a4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Igual que STAGE_PALETTE en app/services/pipelines.py.
PALETTE = ("#3b82f6", "#06b6d4", "#8b5cf6", "#f59e0b", "#ec4899", "#14b8a6", "#6366f1", "#f97316")


def upgrade() -> None:
    op.add_column("pipelines", sa.Column("color", sa.String(7), nullable=False, server_default="#3b82f6"))
    palette = "ARRAY[" + ", ".join(f"'{c}'" for c in PALETTE) + "]"
    op.execute(f"""
        UPDATE pipelines AS p SET color = ({palette})[((o.n - 1) % {len(PALETTE)}) + 1]
        FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY tenant_id ORDER BY is_default DESC, position, name) AS n
            FROM pipelines
        ) AS o
        WHERE o.id = p.id
    """)


def downgrade() -> None:
    op.drop_column("pipelines", "color")
