from collections.abc import Generator

from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from utils.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()


def _ensure_sqlite_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "loan_applications" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("loan_applications")}
    if "approved_amount" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE loan_applications ADD COLUMN approved_amount FLOAT"))


def reset_db() -> None:
    from database import models  # noqa: F401

    reflected_metadata = MetaData()
    reflected_metadata.reflect(bind=engine)
    reflected_metadata.drop_all(bind=engine)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
