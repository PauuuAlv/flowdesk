import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.middleware.audit import AuditContextMiddleware
from app.middleware.tenant import TenantContextMiddleware
from app.api.v1 import activities, audit, auth, clients, company_settings, contacts, dashboard, data_transfer, notifications, opportunities, opportunity_stages, pipelines, platform_admin, platform_roles, product_catalogs, products, quotes, roles, tenant_plan, users

logger = logging.getLogger("flowdesk")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Mantiene la tabla `permissions` alineada con PERMISSION_CATALOG y garantiza
    # que el rol Administrador de cada empresa tenga todos los permisos.
    from app.core.database import SessionLocal
    from app.services.access_control import sync_permission_catalog
    from app.services.platform_access import sync_platform_access

    db = SessionLocal()
    try:
        sync_permission_catalog(db)
        sync_platform_access(db)
    except Exception:  # la API debe arrancar aunque la DB aun no este migrada
        logger.exception("No fue posible sincronizar el catalogo de permisos")
        db.rollback()
    finally:
        db.close()

    push_task = None
    if settings.PUSH_WORKER_ENABLED:
        push_task = asyncio.create_task(_push_dispatcher_loop())
    try:
        yield
    finally:
        if push_task:
            push_task.cancel()
            with suppress(asyncio.CancelledError):
                await push_task


async def _push_dispatcher_loop() -> None:
    """Ejecuta el despachador (recordatorios + Web Push) periódicamente sin bloquear la API."""
    from app.workers.push_dispatcher import run_cycle

    interval = max(settings.PUSH_SCAN_INTERVAL_SECONDS, 15)
    await asyncio.sleep(10)  # deja terminar el arranque antes del primer ciclo
    while True:
        try:
            await asyncio.to_thread(run_cycle)
        except Exception:
            logger.exception("Falló el ciclo del despachador Web Push")
        await asyncio.sleep(interval)


app = FastAPI(
    title="Flowdesk API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TenantContextMiddleware)
# Se agrega al final para que sea el más externo: el contexto de auditoría
# (IP, navegador, endpoint, actor) existe antes que cualquier otra cosa.
app.add_middleware(AuditContextMiddleware)


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(platform_admin.router, prefix="/api/platform-admin", tags=["platform-admin"])
app.include_router(platform_roles.router, prefix="/api/platform-admin/roles", tags=["platform-roles"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(roles.router, prefix="/api/roles", tags=["roles"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(contacts.router, prefix="/api/clients/{client_id}/contacts", tags=["contacts"])
app.include_router(opportunities.router, prefix="/api/opportunities", tags=["opportunities"])
app.include_router(opportunity_stages.router, prefix="/api/opportunity-stages", tags=["opportunity-stages"])
app.include_router(pipelines.router, prefix="/api/pipelines", tags=["pipelines"])
app.include_router(activities.router, prefix="/api/activities", tags=["activities"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(quotes.router, prefix="/api/quotes", tags=["quotes"])
app.include_router(company_settings.router, prefix="/api/company-settings", tags=["company-settings"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(product_catalogs.router, prefix="/api/product-catalogs", tags=["product-catalogs"])
app.include_router(tenant_plan.router, prefix="/api/tenant-plan", tags=["tenant-plan"])
app.include_router(data_transfer.router, prefix="/api/data-transfer", tags=["data-transfer"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
