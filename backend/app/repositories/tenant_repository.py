from sqlalchemy.orm import Session

from app.models.tenant import Tenant


class TenantRepository:
    def find_by_slug(self, db: Session, slug: str) -> Tenant | None:
        return db.query(Tenant).filter(Tenant.slug == slug).first()

    def create(self, db: Session, name: str, slug: str) -> Tenant:
        tenant = Tenant(name=name, slug=slug, is_active=True)
        db.add(tenant)
        db.flush()  # asigna el id sin hacer commit todavía (útil si el
        # caller quiere crear el tenant + el admin en la misma transacción)
        return tenant
