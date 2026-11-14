from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.middleware.tenant import TenantContextMiddleware
from app.api.v1 import activities, auth, clients, company_settings, dashboard, opportunities, platform_admin, products, quotes, roles, users

app = FastAPI(
    title="Flowdesk API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TenantContextMiddleware)


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(platform_admin.router, prefix="/api/platform-admin", tags=["platform-admin"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(roles.router, prefix="/api/roles", tags=["roles"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(opportunities.router, prefix="/api/opportunities", tags=["opportunities"])
app.include_router(activities.router, prefix="/api/activities", tags=["activities"])
app.include_router(quotes.router, prefix="/api/quotes", tags=["quotes"])
app.include_router(company_settings.router, prefix="/api/company-settings", tags=["company-settings"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(products.router, prefix="/api/products", tags=["products"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
