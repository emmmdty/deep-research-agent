"""SQLAlchemy database boundary for the multi-user product context."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def _sqlite_connect_pragmas(dbapi_connection, _connection_record) -> None:
    """SQLite 连接启用 WAL journal 与 foreign key 约束（仅 sqlite backend 注册）。"""

    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL").fetchone()
        cursor.execute("PRAGMA foreign_keys=ON").fetchone()
    finally:
        cursor.close()


@dataclass(frozen=True)
class ProductDatabase:
    """Database engine and short-lived session factory."""

    engine: Engine
    sessions: sessionmaker[Session]
    offline_mode: bool

    def create_schema(self) -> None:
        """Create the product schema for tests and initial deployments."""

        from deep_research_agent.product.tables import Base

        Base.metadata.create_all(self.engine)


def create_database(database_url: str, *, offline_mode: bool = False) -> ProductDatabase:
    """Create a database handle while enforcing PostgreSQL in production."""

    if not database_url or not database_url.strip():
        raise ValueError("a database URL is required for the product API")
    url = make_url(database_url)
    backend = url.get_backend_name()
    if backend != "postgresql" and not (offline_mode and backend == "sqlite"):
        raise ValueError("the production product database must use PostgreSQL")
    connect_args = {"check_same_thread": False} if backend == "sqlite" else {}
    engine_options = {"pool_pre_ping": backend == "postgresql"}
    if backend == "sqlite" and url.database in {None, ":memory:"}:
        engine_options["poolclass"] = StaticPool
    engine = create_engine(url, connect_args=connect_args, **engine_options)
    if backend == "sqlite":
        event.listen(engine, "connect", _sqlite_connect_pragmas)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    return ProductDatabase(engine=engine, sessions=sessions, offline_mode=offline_mode)


__all__ = ["ProductDatabase", "_sqlite_connect_pragmas", "create_database"]
