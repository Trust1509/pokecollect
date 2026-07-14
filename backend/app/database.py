from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def run_with_session(fn, *args, **kwargs):
    """
    Führt eine async Service-Funktion mit eigener, frischer Session aus —
    EINE Routine für alle Hintergrund-/Cron-Einstiege (Issue #9). Services
    nehmen `db` als ersten Parameter statt SessionLocal selbst zu erzeugen;
    BackgroundTasks laufen nach dem Schließen der Request-Session und
    brauchen deshalb diese eigene.
    """
    db = SessionLocal()
    try:
        return await fn(db, *args, **kwargs)
    finally:
        db.close()
