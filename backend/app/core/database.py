from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency de FastAPI: abre una sesión de DB por request y la cierra al final.
    Uso: def endpoint(db: Session = Depends(get_db)): ..."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Registra los eventos del ORM que llenan created_by/updated_by y escriben la
# auditoría (ver app/core/audit.py). Se importa aquí para que aplique a toda
# sesión creada con SessionLocal: API, workers y scripts.
import app.core.audit  # noqa: E402,F401
