from __future__ import annotations

import time
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy ORM models."""
    pass


SLOW_QUERY_THRESHOLD_MS = 500


def add_slow_query_logging(engine: AsyncEngine):
    """Log queries that take longer than SLOW_QUERY_THRESHOLD_MS.
    Requirements: 40.1, 40.2, 40.5
    """
    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.monotonic()

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after_execute(conn, cursor, statement, parameters, context, executemany):
        elapsed_ms = (time.monotonic() - context._query_start_time) * 1000
        if elapsed_ms > SLOW_QUERY_THRESHOLD_MS:
            import logging
            logging.getLogger("slow_queries").warning(
                f"Slow query ({elapsed_ms:.1f}ms): {statement[:200]}"
            )


def create_engine(database_url: str) -> AsyncEngine:
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    add_slow_query_logging(engine)
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


async def get_db(session_factory: async_sessionmaker[AsyncSession]):
    """FastAPI dependency — yields an AsyncSession per request."""
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
