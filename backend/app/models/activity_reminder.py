from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel, TenantMixin


class ActivityReminder(BaseModel, TenantMixin):
    """Recordatorio de una actividad para su responsable.

    Dos modos (exactamente uno):
      - Relativo: `minutes_before` antes de la actividad; se mueve con ella.
      - Fecha exacta: `fixed_at`; no cambia aunque se reprograme la actividad.

    `remind_at` guarda la hora efectiva para que el despachador busque los
    vencidos con un índice. `sent_at` marca que ya se procesó; se limpia si la
    hora efectiva cambia.
    """

    __tablename__ = "activity_reminders"
    __table_args__ = (
        CheckConstraint("(minutes_before IS NULL) <> (fixed_at IS NULL)", name="ck_activity_reminder_mode"),
    )

    activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    minutes_before = Column(Integer, nullable=True)
    fixed_at = Column(DateTime(timezone=True), nullable=True)
    remind_at = Column(DateTime(timezone=True), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True, index=True)
