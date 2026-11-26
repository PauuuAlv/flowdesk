"""Generación de notificaciones internas a partir de eventos del CRM.

Las notificaciones se derivan de actividades, cotizaciones y oportunidades del
usuario. La generación es idempotente gracias a `event_key`: un mismo evento
nunca produce dos notificaciones para el mismo usuario.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.notification import Notification
from app.models.opportunity import Opportunity
from app.models.quote import Quote
from app.models.user import User


def add_notification_if_missing(db: Session, user: User, event_key: str, kind: str, title: str,
                                message: str, route: str) -> Notification | None:
    """Agrega la notificación si el evento todavía no existe. Devuelve la nueva fila o None."""
    exists = db.query(Notification.id).filter(
        Notification.tenant_id == user.tenant_id,
        Notification.user_id == user.id,
        Notification.event_key == event_key,
    ).first()
    if exists:
        return None
    item = Notification(tenant_id=user.tenant_id, user_id=user.id, event_key=event_key,
        notification_type=kind, title=title[:160], message=message[:300], route=route, is_read=False)
    db.add(item)
    return item


def sync_user_notifications(db: Session, user: User) -> list[Notification]:
    """Crea las notificaciones nuevas del usuario y confirma la transacción."""
    created: list[Notification] = []

    def add(*args) -> None:
        item = add_notification_if_missing(db, user, *args)
        if item is not None:
            created.append(item)

    now = datetime.now(timezone.utc)
    activity_limit = now + timedelta(hours=24)
    activities = db.query(Activity).filter(
        Activity.tenant_id == user.tenant_id,
        Activity.owner_user_id == user.id,
        Activity.status == "pending",
        Activity.scheduled_at <= activity_limit,
    ).all()
    for item in activities:
        overdue = item.scheduled_at < now
        add(f"activity:{item.id}:due", "activity_overdue" if overdue else "activity_upcoming",
            "Actividad vencida" if overdue else "Actividad próxima",
            f"{item.title} · {item.client.company_name}", activity_route(item.id))

    today = date.today()
    date_limit = today + timedelta(days=3)
    quotes = db.query(Quote).filter(
        Quote.tenant_id == user.tenant_id,
        Quote.owner_user_id == user.id,
        Quote.status.in_(["draft", "sent"]),
        Quote.valid_until.between(today, date_limit),
    ).all()
    for item in quotes:
        add(f"quote:{item.id}:expiry", "quote_expiring", "Cotización por vencer",
            f"{item.prefix}-{item.sequence:04d} vence el {item.valid_until.strftime('%d/%m/%Y')}",
            f"/panel/cotizaciones/{item.id}")

    opportunities = db.query(Opportunity).filter(
        Opportunity.tenant_id == user.tenant_id,
        Opportunity.owner_user_id == user.id,
        Opportunity.archived_at.is_(None),
        Opportunity.closed_at.is_(None),
        Opportunity.expected_close_date.between(today, date_limit),
    ).all()
    for item in opportunities:
        add(f"opportunity:{item.id}:close", "opportunity_closing", "Cierre estimado próximo",
            f"{item.name} · {item.expected_close_date.strftime('%d/%m/%Y')}", "/panel/oportunidades")

    # Respaldo del despachador: si la API estuvo dormida, los recordatorios
    # vencidos del usuario se generan al consultar sus notificaciones.
    from app.services.activity_reminders import process_due_reminders
    process_due_reminders(db, user_id=user.id, now=now)
    db.commit()
    return created


# ---------------------------------------------------------------------------
# Avisos inmediatos por asignación de actividades
# ---------------------------------------------------------------------------

def activity_route(activity_id) -> str:
    """Lista de actividades enfocada en una: la página se desplaza a ella y la resalta."""
    return f"/panel/actividades?actividad={activity_id}"


def _actor_name(user: User) -> str:
    return (user.full_name or "").strip() or user.email


def _activity_label(activity: Activity) -> str:
    client = activity.client.company_name if activity.client else ""
    return f"{activity.title} · {client}" if client else activity.title


def _event_notification(db: Session, activity: Activity, user_id, kind: str, title: str, message: str,
                        event_key: str) -> Notification:
    """Notificación de un hecho puntual: cada evento tiene su propia clave única."""
    item = Notification(tenant_id=activity.tenant_id, user_id=user_id, event_key=event_key[:180],
        notification_type=kind, title=title[:160], message=message[:300], route=activity_route(activity.id),
        is_read=False)
    db.add(item)
    return item


def notify_activity_assignment(db: Session, actor: User, activity: Activity, previous_owner_id=None,
                               changed: bool = True) -> set:
    """Crea los avisos por asignar, reasignar o modificar una actividad.

    - Nuevo responsable (al crear o reasignar): "Nueva actividad asignada".
    - Responsable anterior (al reasignar): "Se te retiró una actividad".
    - Mismo responsable y la actividad cambió: "Actividad actualizada".

    Nunca se avisa a quien hizo el cambio. No confirma la transacción; devuelve
    los ids de usuario que recibieron aviso para enviarles Web Push.
    """
    stamp = uuid.uuid4().hex
    actor_name = _actor_name(actor)
    label = _activity_label(activity)
    owner_id = activity.owner_user_id
    recipients = set()

    if previous_owner_id is None or previous_owner_id != owner_id:
        if owner_id != actor.id:
            _event_notification(db, activity, owner_id, "activity_assigned",
                "Nueva actividad asignada", f"{actor_name} te asignó: {label}",
                f"activity:{activity.id}:assigned:{stamp}")
            recipients.add(owner_id)
        if previous_owner_id is not None and previous_owner_id != actor.id:
            new_owner = db.query(User).filter(User.id == owner_id).first()
            new_owner_name = _actor_name(new_owner) if new_owner else "otro usuario"
            _event_notification(db, activity, previous_owner_id, "activity_unassigned",
                "Se te retiró una actividad", f"{actor_name} se la asignó a {new_owner_name}: {label}",
                f"activity:{activity.id}:unassigned:{stamp}")
            recipients.add(previous_owner_id)
    elif changed and owner_id != actor.id:
        _event_notification(db, activity, owner_id, "activity_updated",
            "Actividad actualizada", f"{actor_name} modificó: {label}",
            f"activity:{activity.id}:updated:{stamp}")
        recipients.add(owner_id)
    return recipients
