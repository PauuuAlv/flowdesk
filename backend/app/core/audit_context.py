"""Contexto de auditoría por request.

Un middleware ASGI crea un `AuditContext` al inicio de cada request (IP,
navegador, método, endpoint y, si viene un token, quién lo hace) y lo guarda
en un ContextVar. El objeto es MUTABLE a propósito: FastAPI ejecuta las
dependencias síncronas en un threadpool con una *copia* del contexto, así que
`ContextVar.set()` dentro de una dependencia no llegaría al endpoint, pero
modificar los atributos del mismo objeto sí (la copia apunta al mismo objeto).

Fuera de un request (workers, scripts, arranque) no hay contexto y todo se
atribuye al actor `system`.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass

# Identificador fijo para el actor "sistema" (los campos created_by/updated_by
# son NOT NULL, así que los procesos automáticos y los datos históricos usan este).
SYSTEM_ACTOR_ID = uuid.UUID(int=0)

ACTOR_USER = "user"
ACTOR_PLATFORM_ADMIN = "platform_admin"
ACTOR_SYSTEM = "system"


@dataclass
class AuditContext:
    actor_type: str = ACTOR_SYSTEM
    actor_id: uuid.UUID | None = None
    actor_email: str | None = None
    tenant_id: uuid.UUID | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    http_method: str | None = None
    endpoint: str | None = None

    @property
    def effective_actor_id(self) -> uuid.UUID:
        return self.actor_id or SYSTEM_ACTOR_ID

    def set_user(self, user_id, tenant_id, email: str | None = None) -> None:
        self.actor_type = ACTOR_USER
        self.actor_id = _as_uuid(user_id)
        self.tenant_id = _as_uuid(tenant_id)
        if email:
            self.actor_email = email

    def set_platform_admin(self, admin_id, email: str | None = None) -> None:
        self.actor_type = ACTOR_PLATFORM_ADMIN
        self.actor_id = _as_uuid(admin_id)
        self.tenant_id = None
        if email:
            self.actor_email = email


_current: ContextVar[AuditContext | None] = ContextVar("flowdesk_audit_context", default=None)


def get_audit_context() -> AuditContext:
    """Contexto del request actual; fuera de un request, un contexto `system`."""
    return _current.get() or AuditContext()


def bind_audit_context(ctx: AuditContext):
    return _current.set(ctx)


def reset_audit_context(token) -> None:
    _current.reset(token)


def _as_uuid(value) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None
