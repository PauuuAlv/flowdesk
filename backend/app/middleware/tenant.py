from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from jose import JWTError

from app.security.jwt import decode_token

# Rutas que NO requieren autenticación (login, refresh, docs, health).
# Todo lo que no esté aquí exige un Bearer token válido.
PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/auth/register",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
}


class TenantContextMiddleware(BaseHTTPMiddleware):
    """US-005 AC-01/AC-02: inyecta tenant_id (y user_id, role) en request.state
    a partir del JWT. NINGÚN endpoint debe leer tenant_id de otro lado
    (ni query param, ni body, ni header custom) — siempre request.state.tenant_id.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/api/platform-admin/"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = decode_token(token)
        except JWTError:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

        if payload.get("type") != "access":
            return JSONResponse(status_code=401, content={"detail": "Invalid token type"})

        # Disponible en cualquier endpoint vía request.state.*
        request.state.user_id = payload["sub"]
        request.state.tenant_id = payload["tenant_id"]
        request.state.role = payload.get("role")

        return await call_next(request)
