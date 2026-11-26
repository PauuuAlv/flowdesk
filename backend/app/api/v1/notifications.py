import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.notification import Notification
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    PushConfigResponse,
    PushSubscriptionRequest,
    PushTestResponse,
    PushUnsubscribeRequest,
)
from app.security.user_auth import get_current_user
from app.services.notifications import sync_user_notifications
from app.services.web_push import mark_pending_as_processed, send_to_user

router = APIRouter()


def _serialize(item: Notification) -> NotificationResponse:
    return NotificationResponse(id=str(item.id), notification_type=item.notification_type, title=item.title,
        message=item.message, route=item.route, is_read=item.is_read, created_at=item.created_at)


@router.get("", response_model=NotificationListResponse)
def list_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sync_user_notifications(db, current_user)
    query = db.query(Notification).filter(Notification.tenant_id == current_user.tenant_id,
        Notification.user_id == current_user.id)
    unread = query.filter(Notification.is_read.is_(False)).count()
    items = query.order_by(Notification.is_read.asc(), Notification.created_at.desc()).limit(30).all()
    return NotificationListResponse(unread_count=unread, items=[_serialize(item) for item in items])


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(notification_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(Notification).filter(Notification.id == notification_id,
        Notification.tenant_id == current_user.tenant_id, Notification.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Notification not found")
    item.is_read = True
    db.commit(); db.refresh(item)
    return _serialize(item)


@router.post("/read-all", status_code=204)
def mark_all_notifications_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(Notification).filter(Notification.tenant_id == current_user.tenant_id,
        Notification.user_id == current_user.id, Notification.is_read.is_(False)).update({"is_read": True})
    db.commit()


# ---------------------------------------------------------------------------
# Web Push (W3C Push API + VAPID)
# ---------------------------------------------------------------------------

@router.get("/push/config", response_model=PushConfigResponse)
def push_config(_current_user: User = Depends(get_current_user)):
    """Clave pública VAPID que el navegador usa como `applicationServerKey`."""
    if not settings.push_enabled:
        return PushConfigResponse(enabled=False)
    return PushConfigResponse(enabled=True, public_key=settings.VAPID_PUBLIC_KEY)


@router.post("/push/subscriptions", status_code=204)
def save_push_subscription(payload: PushSubscriptionRequest, request: Request,
                           db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Registra (o reasigna al usuario actual) la suscripción de este navegador."""
    if not settings.push_enabled:
        raise HTTPException(status_code=503, detail="Web Push no está configurado")
    user_agent = (request.headers.get("user-agent") or "")[:300] or None
    subscription = db.query(PushSubscription).filter(PushSubscription.endpoint == payload.endpoint).first()
    is_new_for_user = (subscription is None or subscription.user_id != current_user.id
        or subscription.tenant_id != current_user.tenant_id)
    if subscription is None:
        subscription = PushSubscription(endpoint=payload.endpoint)
        db.add(subscription)
    subscription.tenant_id = current_user.tenant_id
    subscription.user_id = current_user.id
    subscription.p256dh = payload.keys.p256dh
    subscription.auth = payload.keys.auth
    subscription.user_agent = user_agent
    subscription.failure_count = 0
    if is_new_for_user:
        mark_pending_as_processed(db, current_user.tenant_id, current_user.id)
    db.commit()


@router.delete("/push/subscriptions", status_code=204)
def delete_push_subscription(payload: PushUnsubscribeRequest, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    db.query(PushSubscription).filter(
        PushSubscription.endpoint == payload.endpoint,
        PushSubscription.tenant_id == current_user.tenant_id,
        PushSubscription.user_id == current_user.id,
    ).delete(synchronize_session=False)
    db.commit()


@router.post("/push/test", response_model=PushTestResponse)
def send_test_push(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Envía una notificación de prueba a todos los navegadores del usuario."""
    if not settings.push_enabled:
        raise HTTPException(status_code=503, detail="Web Push no está configurado")
    result = send_to_user(db, current_user.tenant_id, current_user.id, {
        "id": f"test-{uuid.uuid4()}",
        "type": "push_test",
        "title": "Notificaciones activadas",
        "body": "Así verás los avisos de Flowdesk en este dispositivo.",
        "url": "/panel",
        "tag": "flowdesk-push-test",
    })
    return PushTestResponse(delivered=result.delivered, removed=result.removed, failed=result.failed)
