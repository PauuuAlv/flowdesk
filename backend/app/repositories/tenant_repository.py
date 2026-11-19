import uuid

from sqlalchemy import case, delete, func, select, update
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.client import Client
from app.models.opportunity import Opportunity
from app.models.password_reset_token import PasswordResetToken
from app.models.product import Product
from app.models.quote import Quote, QuoteItem
from app.models.role import Role, RolePermission
from app.models.tenant import Tenant
from app.models.user import User


class TenantRepository:
    def find_by_slug(self, db: Session, slug: str) -> Tenant | None:
        return db.query(Tenant).filter(Tenant.slug == slug).first()

    def get(self, db: Session, tenant_id: uuid.UUID) -> Tenant | None:
        return db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def is_active(self, db: Session, tenant_id: uuid.UUID) -> bool:
        active = db.query(Tenant.is_active).filter(Tenant.id == tenant_id).scalar()
        return bool(active)

    def create(self, db: Session, name: str, slug: str) -> Tenant:
        tenant = Tenant(name=name, slug=slug, is_active=True)
        db.add(tenant)
        db.flush()  # asigna el id sin hacer commit todavía (útil si el
        # caller quiere crear el tenant + el admin en la misma transacción)
        return tenant

    def list_with_stats(self, db: Session) -> list[dict]:
        """Lista todas las empresas con conteo de usuarios y su administrador
        principal (el primer admin creado), en una sola consulta por bloque."""
        tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).all()

        counts = {
            row.tenant_id: (row.total, row.active)
            for row in db.execute(
                select(
                    User.tenant_id,
                    func.count(User.id).label("total"),
                    func.sum(case((User.status == "active", 1), else_=0)).label("active"),
                ).group_by(User.tenant_id)
            )
        }

        admins: dict[uuid.UUID, User] = {}
        for admin in (
            db.query(User)
            .join(Role, Role.id == User.role_id)
            .filter(Role.template_key == "admin")
            .order_by(User.created_at.asc())
            .all()
        ):
            admins.setdefault(admin.tenant_id, admin)

        result = []
        for tenant in tenants:
            total, active = counts.get(tenant.id, (0, 0))
            admin = admins.get(tenant.id)
            result.append(
                {
                    "tenant": tenant,
                    "users_count": int(total or 0),
                    "active_users_count": int(active or 0),
                    "admin": admin,
                }
            )
        return result

    def delete_with_data(self, db: Session, tenant_id: uuid.UUID) -> None:
        """Elimina la empresa y TODOS sus datos. Las tablas no tienen llave
        foránea hacia `tenants`, así que se borran explícitamente en orden
        de dependencias (hijos primero). No hace commit: lo decide el caller."""
        quote_ids = select(Quote.id).where(Quote.tenant_id == tenant_id)

        db.execute(delete(Activity).where(Activity.tenant_id == tenant_id))
        db.execute(delete(QuoteItem).where(QuoteItem.quote_id.in_(quote_ids)))
        db.execute(delete(Quote).where(Quote.tenant_id == tenant_id))
        db.execute(delete(Opportunity).where(Opportunity.tenant_id == tenant_id))
        db.execute(delete(Client).where(Client.tenant_id == tenant_id))
        db.execute(delete(Product).where(Product.tenant_id == tenant_id))
        db.execute(delete(PasswordResetToken).where(PasswordResetToken.tenant_id == tenant_id))
        # Usuarios se referencian entre sí (invited_by_user_id): se limpia primero.
        db.execute(
            update(User).where(User.tenant_id == tenant_id).values(invited_by_user_id=None)
        )
        db.execute(delete(User).where(User.tenant_id == tenant_id))
        db.execute(delete(RolePermission).where(RolePermission.tenant_id == tenant_id))
        db.execute(delete(Role).where(Role.tenant_id == tenant_id))
        db.execute(delete(Tenant).where(Tenant.id == tenant_id))
