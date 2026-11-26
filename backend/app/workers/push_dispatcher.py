"""Despachador periódico de notificaciones (recordatorios + Web Push).

En cada ciclo:
  1. Convierte en notificaciones los recordatorios de actividades cuya hora
     llegó (siempre, aunque Web Push no esté configurado).
  2. Si hay claves VAPID: para cada usuario activo con un navegador suscrito,
     genera sus notificaciones nuevas y envía por Web Push las pendientes.

Corre dentro del proceso de la API (ver `app.main.lifespan`) o por separado:

    python -m app.workers.push_dispatcher          # ciclo continuo
    python -m app.workers.push_dispatcher --once   # un solo ciclo (cron)

Un candado consultivo de PostgreSQL evita que dos réplicas procesen a la vez.
"""
import argparse
import logging
import time

from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models.push_subscription import PushSubscription
from app.models.tenant import Tenant
from app.models.user import User
from app.services.activity_reminders import process_due_reminders
from app.services.notifications import sync_user_notifications
from app.services.web_push import dispatch_pending_notifications

logger = logging.getLogger("flowdesk.push")

# Identificador arbitrario y fijo del candado consultivo del despachador.
ADVISORY_LOCK_KEY = 7_340_211_902


def run_cycle() -> int:
    """Ejecuta un ciclo. Devuelve los mensajes push entregados (-1 si otro proceso tenía el candado)."""
    with engine.connect() as lock_conn:
        acquired = lock_conn.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": ADVISORY_LOCK_KEY}).scalar()
        lock_conn.commit()
        if not acquired:
            return -1
        try:
            _process_reminders()
            return _process_subscribed_users() if settings.push_enabled else 0
        finally:
            lock_conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": ADVISORY_LOCK_KEY})
            lock_conn.commit()


def _process_reminders() -> None:
    db = SessionLocal()
    try:
        process_due_reminders(db)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Falló el procesamiento de recordatorios de actividades")
    finally:
        db.close()


def _process_subscribed_users() -> int:
    db = SessionLocal()
    delivered = 0
    try:
        users = db.query(User).join(Tenant, Tenant.id == User.tenant_id).filter(
            User.status == "active",
            Tenant.is_active.is_(True),
            User.id.in_(db.query(PushSubscription.user_id)),
        ).all()
        for user in users:
            try:
                sync_user_notifications(db, user)
                delivered += dispatch_pending_notifications(db, user.tenant_id, user.id)
            except Exception:
                db.rollback()
                logger.exception("Falló el despacho Web Push del usuario %s", user.id)
    finally:
        db.close()
    return delivered


def main() -> None:
    parser = argparse.ArgumentParser(description="Despachador de notificaciones de Flowdesk")
    parser.add_argument("--once", action="store_true", help="ejecuta un solo ciclo y termina")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if not settings.push_enabled:
        logger.warning("Web Push deshabilitado: solo se procesarán recordatorios para el panel.")
    while True:
        delivered = run_cycle()
        logger.info("Ciclo de notificaciones terminado: %s mensajes push entregados", max(delivered, 0))
        if args.once:
            return
        time.sleep(max(settings.PUSH_SCAN_INTERVAL_SECONDS, 15))


if __name__ == "__main__":
    main()
