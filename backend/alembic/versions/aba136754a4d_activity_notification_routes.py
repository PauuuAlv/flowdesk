"""avisos de actividades apuntan a la actividad que los generó

Los avisos guardados antes solo abrían /panel/actividades. Se agrega
?actividad=<id> (tomado de event_key "activity:<id>:...") para que la lista se
desplace a ella y la resalte.

Revision ID: aba136754a4d
Revises: 1cdacef37e86
"""
from typing import Sequence, Union

from alembic import op

revision: str = "aba136754a4d"
down_revision: Union[str, None] = "1cdacef37e86"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE notifications
        SET route = '/panel/actividades?actividad=' || split_part(event_key, ':', 2)
        WHERE route = '/panel/actividades' AND event_key LIKE 'activity:%'
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE notifications SET route = '/panel/actividades'
        WHERE route LIKE '/panel/actividades?actividad=%'
    """)
