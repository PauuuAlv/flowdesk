"""avisos de oportunidades apuntan a la oportunidad que los generó

Los avisos guardados antes solo abrían /panel/oportunidades. Se agrega
?oportunidad=<id> (tomado de event_key "opportunity:<id>:...") para que el
tablero se desplace a ella y la resalte.

Revision ID: 36979f1fc50a
Revises: 3774ec3a6f13
"""
from typing import Sequence, Union

from alembic import op

revision: str = "36979f1fc50a"
down_revision: Union[str, None] = "3774ec3a6f13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE notifications
        SET route = '/panel/oportunidades?oportunidad=' || split_part(event_key, ':', 2)
        WHERE route = '/panel/oportunidades' AND event_key LIKE 'opportunity:%'
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE notifications SET route = '/panel/oportunidades'
        WHERE route LIKE '/panel/oportunidades?oportunidad=%'
    """)
