"""Recordatorios de actividades.

Cada actividad puede tener varios recordatorios ("15 minutos antes", "1 día
antes"...). Al llegar la hora se crea una notificación para el responsable
actual de la actividad, que se ve en el panel y se entrega por Web Push.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.activity_reminder import ActivityReminder
from app.models.notification import Notification
from app.schemas.activity import MAX_REMINDER_MINUTES, ActivityReminderInput
from app.services.notifications import activity_route

# Un recordatorio que no se pudo enviar a tiempo (API apagada) ya no se manda
# si pasó más de esto: avisar "empieza en 15 min" horas después confunde.
STALE_AFTER = timedelta(hours=2)


def describe_offset(minutes: int) -> str:
    """"Comienza en 1 día 2 horas", "Comienza en 15 minutos", "Comienza ahora"."""
    if minutes <= 0:
        return "Comienza ahora"
    days, rest = divmod(minutes, 1440)
    hours, mins = divmod(rest, 60)
    parts = []
    if days:
        parts.append(f"{days} día{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hora{'s' if hours != 1 else ''}")
    if mins and not days:  # con días, los minutos sobran
        parts.append(f"{mins} minuto{'s' if mins != 1 else ''}")
    return "Comienza en " + " ".join(parts)


def _effective_time(reminder: ActivityReminder, activity: Activity) -> datetime:
    if reminder.fixed_at is not None:
        return reminder.fixed_at
    return activity.scheduled_at - timedelta(minutes=reminder.minutes_before)


def _schedule(reminder: ActivityReminder, activity: Activity, now: datetime) -> None:
    """Recalcula `remind_at`. Si cambió, el recordatorio vuelve a quedar pendiente,
    salvo que su hora ya haya pasado (no se avisa tarde de algo recién guardado)."""
    remind_at = _effective_time(reminder, activity)
    if reminder.remind_at is not None and reminder.remind_at == remind_at:
        return
    reminder.remind_at = remind_at
    reminder.sent_at = now if remind_at <= now else None


def _validate_fixed(fixed_at: datetime, activity: Activity) -> None:
    if fixed_at > activity.scheduled_at:
        raise HTTPException(status_code=422, detail="Reminder must be before the activity")
    if fixed_at < activity.scheduled_at - timedelta(minutes=MAX_REMINDER_MINUTES):
        raise HTTPException(status_code=422, detail="Reminder can be at most 30 days before the activity")


def apply_reminders(activity: Activity, inputs: list[ActivityReminderInput] | None,
                    now: datetime | None = None) -> None:
    """Sincroniza los recordatorios de la actividad con los del formulario.

    `inputs=None` conserva los actuales y solo los reprograma (por si cambió la
    fecha; los de fecha exacta no se mueven). Con lista: los que traen `id` se
    modifican, los nuevos se crean y los que ya no vienen se eliminan.
    Recordatorios repetidos (misma anticipación o misma fecha) se ignoran.
    """
    now = now or datetime.now(timezone.utc)
    if inputs is not None:
        current = {str(item.id): item for item in activity.reminders}
        kept: list[ActivityReminder] = []
        seen: set = set()
        for data in inputs:
            key = ("fixed", data.fixed_at) if data.fixed_at is not None else ("before", data.minutes_before)
            if key in seen:
                continue
            seen.add(key)
            if data.fixed_at is not None:
                _validate_fixed(data.fixed_at, activity)
            reminder = current.get(data.id) if data.id else None
            if data.id and reminder is None:
                raise HTTPException(status_code=404, detail="Reminder not found")
            if reminder is None:
                reminder = ActivityReminder(id=uuid.uuid4(), tenant_id=activity.tenant_id)
            reminder.minutes_before = data.minutes_before
            reminder.fixed_at = data.fixed_at
            kept.append(reminder)
        activity.reminders = kept  # delete-orphan elimina los que ya no están
    for reminder in activity.reminders:
        _schedule(reminder, activity, now)


def process_due_reminders(db: Session, user_id=None, now: datetime | None = None) -> set:
    """Convierte en notificaciones los recordatorios cuya hora llegó.

    Solo actividades pendientes; avisa al responsable actual. Si `user_id` se
    indica, procesa únicamente las actividades de ese usuario. No confirma la
    transacción. Devuelve {(tenant_id, user_id)} de quienes recibieron aviso.
    """
    now = now or datetime.now(timezone.utc)
    query = db.query(ActivityReminder, Activity).join(Activity, Activity.id == ActivityReminder.activity_id).filter(
        ActivityReminder.sent_at.is_(None),
        ActivityReminder.remind_at <= now,
        Activity.status == "pending",
    )
    if user_id is not None:
        query = query.filter(Activity.owner_user_id == user_id)
    rows = query.with_for_update(of=ActivityReminder, skip_locked=True).all()
    recipients = set()
    for reminder, activity in rows:
        reminder.sent_at = now
        if reminder.remind_at < now - STALE_AFTER:
            continue
        client = activity.client.company_name if activity.client else ""
        minutes_left = max(0, round((activity.scheduled_at - reminder.remind_at).total_seconds() / 60))
        when = describe_offset(minutes_left)
        db.add(Notification(
            tenant_id=activity.tenant_id,
            user_id=activity.owner_user_id,
            event_key=f"activity:{activity.id}:reminder:{reminder.id}:{int(reminder.remind_at.timestamp())}",
            notification_type="activity_reminder",
            title=f"Recordatorio: {activity.title}"[:160],
            message=(f"{when} · {client}" if client else when)[:300],
            route=activity_route(activity.id),
            is_read=False,
        ))
        recipients.add((activity.tenant_id, activity.owner_user_id))
    return recipients
