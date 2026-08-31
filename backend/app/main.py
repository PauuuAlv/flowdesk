from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title="Flowdesk API",
    version="0.1.0",
)

# CORS: en dev, Angular corre en otro puerto/origen (vía nginx en :80,
# pero directo en :4200 si alguna vez pruebas sin nginx).
# Ajusta origins en core/config.py cuando definan el dominio real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Endpoint simple para confirmar que el backend está vivo.
    Útil para probar que docker compose levantó todo correctamente."""
    return {"status": "ok", "service": "flowdesk-api", "version": app.version}


# A partir de aquí se irán agregando los routers de cada módulo, ej:
# from app.api.v1 import auth, customers
# app.include_router(auth.router, prefix="/auth", tags=["auth"])
