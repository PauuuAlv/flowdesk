from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import TenantScopedRepository


class UserRepository(TenantScopedRepository[User]):
    model = User

    def find_by_email_any_tenant(self, db: Session, email: str) -> User | None:
            """SOLO se usa en el login, donde todavía no sabemos el tenant_id.
            LIMITACIÓN CONOCIDA (ver nota original): email único por tenant, no global."""
            return db.query(User).filter(User.email == email).first()
    
    def find_by_invitation_token_hash(self, db: Session, token_hash: str) -> User | None:
            """El token de invitación SÍ es único globalmente (columna unique=True
            en el modelo), así que no hace falta acotar por tenant aquí."""
            return db.query(User).filter(User.invitation_token_hash == token_hash).first()
    
