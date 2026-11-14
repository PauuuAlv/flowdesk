"""add quotes
Revision ID: e8a731df409c
Revises: c492dc8e17b1
Create Date: 2026-11-13
"""
from typing import Sequence,Union
from alembic import op
import sqlalchemy as sa
revision="e8a731df409c";down_revision="c492dc8e17b1";branch_labels:Union[str,Sequence[str],None]=None;depends_on:Union[str,Sequence[str],None]=None
def upgrade():
    op.create_table("quotes",sa.Column("sequence",sa.Integer(),nullable=False),sa.Column("client_id",sa.UUID(),nullable=False),sa.Column("opportunity_id",sa.UUID(),nullable=True),sa.Column("owner_user_id",sa.UUID(),nullable=False),sa.Column("issue_date",sa.Date(),nullable=False),sa.Column("valid_until",sa.Date(),nullable=False),sa.Column("currency",sa.String(3),nullable=False),sa.Column("discount",sa.Numeric(14,2),nullable=False),sa.Column("tax_rate",sa.Numeric(5,2),nullable=False),sa.Column("subtotal",sa.Numeric(14,2),nullable=False),sa.Column("tax",sa.Numeric(14,2),nullable=False),sa.Column("total",sa.Numeric(14,2),nullable=False),sa.Column("status",sa.String(20),nullable=False),sa.Column("notes",sa.Text(),nullable=True),sa.Column("id",sa.UUID(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("now()")),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.text("now()")),sa.Column("tenant_id",sa.UUID(),nullable=False),sa.ForeignKeyConstraint(["client_id"],["clients.id"]),sa.ForeignKeyConstraint(["opportunity_id"],["opportunities.id"]),sa.ForeignKeyConstraint(["owner_user_id"],["users.id"]),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("tenant_id","sequence",name="uq_quote_tenant_sequence"))
    for c in ("client_id","opportunity_id","owner_user_id","valid_until","status","tenant_id"):op.create_index(op.f(f"ix_quotes_{c}"),"quotes",[c])
    op.create_table("quote_items",sa.Column("quote_id",sa.UUID(),nullable=False),sa.Column("position",sa.Integer(),nullable=False),sa.Column("description",sa.String(240),nullable=False),sa.Column("quantity",sa.Numeric(12,2),nullable=False),sa.Column("unit_price",sa.Numeric(14,2),nullable=False),sa.Column("amount",sa.Numeric(14,2),nullable=False),sa.Column("id",sa.UUID(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("now()")),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.text("now()")),sa.ForeignKeyConstraint(["quote_id"],["quotes.id"],ondelete="CASCADE"),sa.PrimaryKeyConstraint("id"));op.create_index(op.f("ix_quote_items_quote_id"),"quote_items",["quote_id"])
    op.execute("""INSERT INTO role_permissions(role_id,permission_code) SELECT id,p FROM roles CROSS JOIN LATERAL unnest(CASE WHEN template_key IN ('admin','supervisor') THEN ARRAY['quotes.view','quotes.create','quotes.update','quotes.status'] ELSE ARRAY['quotes.view'] END) p WHERE origin='template' ON CONFLICT DO NOTHING""")
def downgrade():
    op.execute("DELETE FROM role_permissions WHERE permission_code LIKE 'quotes.%'");op.drop_table("quote_items");op.drop_table("quotes")
