import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.client import Client
from app.models.notification import Notification
from app.models.opportunity import Opportunity
from app.models.opportunity_stage import OpportunityStage
from app.models.pipeline import Pipeline
from app.models.opportunity_stage_history import OpportunityStageHistory
from app.models.password_reset_token import PasswordResetToken
from app.models.plan_change_request import PlanChangeRequest
from app.models.product import Product
from app.models.product_catalog import Brand, MeasurementUnit, ProductCategory
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

    def create(self, db: Session, name: str, slug: str, **values) -> Tenant:
        tenant = Tenant(name=name, slug=slug, is_active=True, **values)
        db.add(tenant)
        db.flush()  # asigna el id sin hacer commit todavía (útil si el
        # caller quiere crear el tenant + el admin en la misma transacción)
        return tenant

    def count_data(self, db: Session, tenant_id: uuid.UUID) -> dict[str, int]:
        """Cuántos registros tiene la empresa en cada tabla (para el resumen de
        auditoría antes de un borrado masivo)."""
        models = (
            Activity, Quote, OpportunityStageHistory, Opportunity, OpportunityStage,
            Pipeline, Client, Product, Brand, ProductCategory, MeasurementUnit,
            PlanChangeRequest, User, Role,
        )
        counts = {
            model.__tablename__: db.query(func.count()).select_from(model).filter(model.tenant_id == tenant_id).scalar() or 0
            for model in models
        }
        return {table: total for table, total in counts.items() if total}

    def delete_with_data(self, db: Session, tenant_id: uuid.UUID) -> None:
        """Elimina la empresa y TODOS sus datos. La mayoría de las tablas no
        tienen llave foránea hacia `tenants`, así que se borran explícitamente
        en orden de dependencias (hijos primero). Las bitácoras de auditoría
        (de plataforma y de la empresa) se conservan: no tienen llaves foráneas.
        No hace commit: lo decide el caller."""
        quote_ids = select(Quote.id).where(Quote.tenant_id == tenant_id)

        db.execute(delete(Notification).where(Notification.tenant_id == tenant_id))
        db.execute(delete(Activity).where(Activity.tenant_id == tenant_id))
        db.execute(delete(QuoteItem).where(QuoteItem.quote_id.in_(quote_ids)))
        db.execute(delete(Quote).where(Quote.tenant_id == tenant_id))
        db.execute(delete(OpportunityStageHistory).where(OpportunityStageHistory.tenant_id == tenant_id))
        db.execute(delete(Opportunity).where(Opportunity.tenant_id == tenant_id))
        db.execute(delete(OpportunityStage).where(OpportunityStage.tenant_id == tenant_id))
        db.execute(delete(Pipeline).where(Pipeline.tenant_id == tenant_id))
        db.execute(delete(Client).where(Client.tenant_id == tenant_id))
        db.execute(delete(Product).where(Product.tenant_id == tenant_id))
        db.execute(delete(Brand).where(Brand.tenant_id == tenant_id))
        db.execute(delete(ProductCategory).where(ProductCategory.tenant_id == tenant_id))
        db.execute(delete(MeasurementUnit).where(MeasurementUnit.tenant_id == tenant_id))
        db.execute(delete(PlanChangeRequest).where(PlanChangeRequest.tenant_id == tenant_id))
        db.execute(delete(PasswordResetToken).where(PasswordResetToken.tenant_id == tenant_id))
        # Usuarios se referencian entre sí (invited_by_user_id): se limpia primero.
        db.execute(
            update(User).where(User.tenant_id == tenant_id).values(invited_by_user_id=None)
        )
        db.execute(delete(User).where(User.tenant_id == tenant_id))
        db.execute(delete(RolePermission).where(RolePermission.tenant_id == tenant_id))
        db.execute(delete(Role).where(Role.tenant_id == tenant_id))
        db.execute(delete(Tenant).where(Tenant.id == tenant_id))
