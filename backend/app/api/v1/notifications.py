import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.activity import Activity
from app.models.notification import Notification
from app.models.opportunity import Opportunity
from app.models.quote import Quote
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.security.user_auth import get_current_user

router = APIRouter()


def _add_if_missing(db: Session, user: User, event_key: str, kind: str, title: str, message: str, route: str) -> None:
    exists = db.query(Notification.id).filter(
        Notification.tenant_id == user.tenant_id,
        Notification.user_id == user.id,
        Notification.event_key == event_key,
    ).first()
    if not exists:
        db.add(Notification(tenant_id=user.tenant_id, user_id=user.id, event_key=event_key,
            notification_type=kind, title=title, message=message, route=route, is_read=False))


def _sync_notifications(db: Session, user: User) -> None:
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
        _add_if_missing(db, user, f"activity:{item.id}:due", "activity_overdue" if overdue else "activity_upcoming",
            "Actividad vencida" if overdue else "Actividad próxima",
            f"{item.title} · {item.client.company_name}", "/panel/actividades")

    today = date.today()
    date_limit = today + timedelta(days=3)
    quotes = db.query(Quote).filter(
        Quote.tenant_id == user.tenant_id,
        Quote.owner_user_id == user.id,
        Quote.status.in_(["draft", "sent"]),
        Quote.valid_until.between(today, date_limit),
    ).all()
    for item in quotes:
        _add_if_missing(db, user, f"quote:{item.id}:expiry", "quote_expiring", "Cotización por vencer",
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
        _add_if_missing(db, user, f"opportunity:{item.id}:close", "opportunity_closing", "Cierre estimado próximo",
            f"{item.name} · {item.expected_close_date.strftime('%d/%m/%Y')}", "/panel/oportunidades")
    db.commit()


def _serialize(item: Notification) -> NotificationResponse:
    return NotificationResponse(id=str(item.id), notification_type=item.notification_type, title=item.title,
        message=item.message, route=item.route, is_read=item.is_read, created_at=item.created_at)


@router.get("", response_model=NotificationListResponse)
def list_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _sync_notifications(db, current_user)
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
