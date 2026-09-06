from sqlalchemy.orm import Session

from app.models.platform_admin import PlatformAdmin


class PlatformAdminRepository:
    def find_by_email(self, db: Session, email: str) -> PlatformAdmin | None:
        return (
            db.query(PlatformAdmin)
            .filter(PlatformAdmin.email == email, PlatformAdmin.is_active.is_(True))
            .first()
        )
