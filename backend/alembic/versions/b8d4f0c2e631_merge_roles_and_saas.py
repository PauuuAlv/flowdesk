"""une las ramas de migración de roles por tenant y suscripciones SaaS

Ambas partían de f51c9f3e7d42 y no tocan las mismas tablas
(a7c3e9b1d520: permissions/roles/role_permissions/users;
f61d0a4f8e53: columnas de plan y suscripción en tenants), así que basta con
unirlas. Funciona tanto en bases que ya tenían aplicada una como la otra.

Revision ID: b8d4f0c2e631
Revises: a7c3e9b1d520, f61d0a4f8e53
"""

revision = "b8d4f0c2e631"
down_revision = ("a7c3e9b1d520", "f61d0a4f8e53")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
