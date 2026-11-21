"""une la rama de roles por tenant con la de catálogos comerciales y SaaS

- b8d4f0c2e631: roles por tenant + suscripciones SaaS.
- f79b9d3c7edc: etapas de oportunidad, catálogos, descuentos, auditoría,
  solicitudes de plan, equipo de plataforma y notificaciones.

No tocan las mismas tablas (f75d5f9e3da8 detecta si users.role existe), así
que basta con unirlas. Funciona en bases que ya tenían aplicada cualquiera
de las dos ramas.

Revision ID: c9e5a1d3f742
Revises: b8d4f0c2e631, f79b9d3c7edc
"""

revision = "c9e5a1d3f742"
down_revision = ("b8d4f0c2e631", "f79b9d3c7edc")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
