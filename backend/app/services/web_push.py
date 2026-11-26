"""Entrega de notificaciones mediante Web Push estándar con VAPID.

Flujo:
  1. El navegador se suscribe con la clave pública VAPID y nos envía su
     `endpoint` y las claves `p256dh`/`auth` (PushSubscription del W3C).
  2. Para entregar, se cifra el contenido (RFC 8291, aes128gcm) y se envía al
     endpoint firmando con la clave privada VAPID (RFC 8292). Lo hace
     `pywebpush`.
  3. Si el servicio push responde 404/410 la suscripción ya no existe y se
     elimina; otros fallos se cuentan y, tras varios seguidos, también.
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification
from app.models.push_subscription import PushSubscription

logger = logging.getLogger("flowdesk.push")

MAX_CONSECUTIVE_FAILURES = 5
HIGH_URGENCY_TYPES = {"activity_overdue", "activity_reminder"}


@dataclass
class PushResult:
    delivered: int = 0
    removed: int = 0
    failed: int = 0


def build_payload(item: Notification) -> dict:
    """Contenido que recibe el service worker (`frontend/app/public/sw.js`)."""
    return {
        "id": str(item.id),
        "type": item.notification_type,
        "title": item.title,
        "body": item.message,
        "url": item.route,
        "tag": f"flowdesk-{item.id}",
    }


def send_to_subscription(db: Session, subscription: PushSubscription, payload: dict,
                         urgency: str = "normal") -> str:
    """Envía un mensaje a una suscripción. Devuelve "delivered", "removed" o "failed"."""
    if not settings.push_enabled:
        return "failed"
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            # pywebpush modifica el diccionario (aud/exp): siempre uno nuevo.
            vapid_claims={"sub": settings.VAPID_SUBJECT},
            ttl=settings.PUSH_TTL_SECONDS,
            headers={"Urgency": urgency},
            timeout=10,
        )
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):
            db.delete(subscription)
            return "removed"
        subscription.failure_count = (subscription.failure_count or 0) + 1
        logger.warning("Web Push rechazado (%s) para la suscripción %s: %s", status, subscription.id, exc)
        if subscription.failure_count >= MAX_CONSECUTIVE_FAILURES:
            db.delete(subscription)
            return "removed"
        return "failed"
    except Exception:  # red caída, timeout, endpoint mal formado...
        subscription.failure_count = (subscription.failure_count or 0) + 1
        logger.exception("No fue posible entregar Web Push a la suscripción %s", subscription.id)
        return "failed"
    subscription.failure_count = 0
    subscription.last_success_at = datetime.now(timezone.utc)
    return "delivered"


def send_to_user(db: Session, tenant_id, user_id, payload: dict, urgency: str = "normal") -> PushResult:
    """Envía el mismo mensaje a todos los navegadores suscritos del usuario."""
    result = PushResult()
    subscriptions = db.query(PushSubscription).filter(
        PushSubscription.tenant_id == tenant_id,
        PushSubscription.user_id == user_id,
    ).all()
    for subscription in subscriptions:
        outcome = send_to_subscription(db, subscription, payload, urgency)
        setattr(result, outcome, getattr(result, outcome) + 1)
    db.commit()
    return result


def mark_pending_as_processed(db: Session, tenant_id, user_id) -> None:
    """Evita que una suscripción nueva reciba de golpe notificaciones ya visibles en el panel."""
    db.query(Notification).filter(
        Notification.tenant_id == tenant_id,
        Notification.user_id == user_id,
        Notification.push_sent_at.is_(None),
    ).update({"push_sent_at": datetime.now(timezone.utc)}, synchronize_session=False)


def dispatch_pending_notifications(db: Session, tenant_id, user_id) -> int:
    """Envía por Web Push las notificaciones del usuario que aún no se procesaron.

    Cada notificación se marca con `push_sent_at` aunque no se entregue (por
    ejemplo, si el navegador ya no existe): Web Push es un canal adicional y la
    notificación sigue disponible dentro del panel.
    """
    now = datetime.now(timezone.utc)
    pending = db.query(Notification).filter(
        Notification.tenant_id == tenant_id,
        Notification.user_id == user_id,
        Notification.push_sent_at.is_(None),
    ).order_by(Notification.created_at.asc()).with_for_update(skip_locked=True).all()
    if not pending:
        db.commit()
        return 0
    oldest_allowed = now - timedelta(hours=settings.PUSH_MAX_AGE_HOURS)
    subscriptions = db.query(PushSubscription).filter(
        PushSubscription.tenant_id == tenant_id,
        PushSubscription.user_id == user_id,
    ).all()
    sent = 0
    for item in pending:
        item.push_sent_at = now
        if item.is_read or (item.created_at and item.created_at < oldest_allowed):
            continue
        payload = build_payload(item)
        urgency = "high" if item.notification_type in HIGH_URGENCY_TYPES else "normal"
        for subscription in list(subscriptions):
            outcome = send_to_subscription(db, subscription, payload, urgency)
            if outcome == "delivered":
                sent += 1
            elif outcome == "removed":
                subscriptions.remove(subscription)
    db.commit()
    return sent


def dispatch_for_users(tenant_id, user_ids) -> None:
    """Envía al momento los avisos pendientes de varios usuarios.

    Pensado para `BackgroundTasks` (corre después de responder la petición,
    con su propia sesión). Si falla, el despachador periódico lo reintenta.
    """
    if not settings.push_enabled or not user_ids:
        return
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        for user_id in user_ids:
            try:
                dispatch_pending_notifications(db, tenant_id, user_id)
            except Exception:
                db.rollback()
                logger.exception("Falló el envío inmediato de Web Push al usuario %s", user_id)
    finally:
        db.close()
