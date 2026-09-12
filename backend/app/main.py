from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.middleware.tenant import TenantContextMiddleware
from app.api.v1 import auth, platform_admin, users

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


@app.get("/health")
def health_check():
    return {"status": "ok"}