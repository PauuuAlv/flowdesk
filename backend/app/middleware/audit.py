"""Middleware ASGI que arma el contexto de auditoría de cada request.

Es un middleware ASGI "puro" (no BaseHTTPMiddleware) para que el ContextVar se
propague sin problemas hasta los endpoints y sus dependencias.

El token solo se DECODIFICA aquí para saber a quién atribuir los cambios; la
validación real (usuario activo, empresa activa, permisos) sigue ocurriendo en
TenantContextMiddleware y en las dependencias de seguridad, que además
completan el correo del actor en el contexto.
"""

from jose import JWTError

from app.core.audit_context import AuditContext, bind_audit_context, reset_audit_context
from app.security.jwt import decode_token


def _header(scope, name: bytes) -> str | None:
    for key, value in scope.get("headers") or []:
        if key.lower() == name:
            return value.decode("latin-1")
    return None


def _client_ip(scope) -> str | None:
    # nginx define X-Real-IP con $remote_addr (no lo puede falsificar el cliente).
    real_ip = _header(scope, b"x-real-ip")
    if real_ip:
        return real_ip.strip()[:64]
    forwarded = _header(scope, b"x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    client = scope.get("client")
    return client[0][:64] if client else None


class AuditContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        ctx = AuditContext(
            ip_address=_client_ip(scope),
            user_agent=(_header(scope, b"user-agent") or "")[:500] or None,
            http_method=scope.get("method"),
            endpoint=scope.get("path", "")[:255],
        )

        auth = _header(scope, b"authorization") or ""
        if auth.startswith("Bearer "):
            try:
                payload = decode_token(auth.removeprefix("Bearer ").strip())
            except JWTError:
                payload = None
            if payload:
                if payload.get("type") == "access":
                    ctx.set_user(payload.get("sub"), payload.get("tenant_id"))
                elif payload.get("type") == "platform_admin":
                    ctx.set_platform_admin(payload.get("sub"))

        token = bind_audit_context(ctx)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_audit_context(token)
