import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.password_reset_token import PasswordResetToken


class PasswordResetRepository:
    def create(
        self, db: Session, tenant_id: uuid.UUID, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> PasswordResetToken:
        row = PasswordResetToken(
            tenant_id=tenant_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def find_valid_by_token_hash(self, db: Session, token_hash: str) -> PasswordResetToken | None:
        """Válido = existe, no usado, y no expirado."""
        row = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
        if not row:
            return None
        if row.used_at is not None:
            return None
        if row.expires_at < datetime.now(timezone.utc):
            return None
        return row

    def invalidate_all_for_user(self, db: Session, user_id: uuid.UUID) -> None:
        """Después de un reset exitoso, invalida cualquier otro link de reset
        que hubiera quedado pendiente para ese usuario (por si pidió varios)."""
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None)
        ).update({"used_at": datetime.now(timezone.utc)})
        db.commit()
