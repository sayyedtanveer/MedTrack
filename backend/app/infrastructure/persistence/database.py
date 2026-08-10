from __future__ import annotations

import time
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy ORM models."""
    pass

import backend.app.infrastructure.persistence.models


import contextvars
import re

SLOW_QUERY_THRESHOLD_MS = 100

query_count_ctx = contextvars.ContextVar("query_count_ctx", default=0)
sql_time_ctx = contextvars.ContextVar("sql_time_ctx", default=0.0)
conn_checkout_time_ctx = contextvars.ContextVar("conn_checkout_time_ctx", default=0.0)
query_tables_ctx = contextvars.ContextVar("query_tables_ctx", default=[])


def instrument_database(engine: AsyncEngine):
    """Instrument the database engine for performance auditing."""
    
    # 1. Connection Checkout Timing
    @event.listens_for(engine.sync_engine.pool, "checkout")
    def on_checkout(dbapi_connection, connection_record, connection_proxy):
        connection_record.info["checkout_start"] = time.monotonic()

    @event.listens_for(engine.sync_engine, "engine_connect")
    def on_engine_connect(connection, branch):
        if not branch:
            start_time = connection.info.get("checkout_start")
            if start_time:
                elapsed = (time.monotonic() - start_time) * 1000
                conn_checkout_time_ctx.set(conn_checkout_time_ctx.get() + elapsed)

    # 2. Query Timing, Counting, and N+1 Detection
    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.monotonic()
        query_count_ctx.set(query_count_ctx.get() + 1)
        
        # Extremely basic table extraction (looks for FROM table_name)
        match = re.search(r'FROM\s+([a-zA-Z0-9_]+)', statement, re.IGNORECASE)
        if match:
            table = match.group(1)
            tables = query_tables_ctx.get().copy()
            tables.append(table)
            query_tables_ctx.set(tables)

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after_execute(conn, cursor, statement, parameters, context, executemany):
        elapsed_ms = (time.monotonic() - context._query_start_time) * 1000
        sql_time_ctx.set(sql_time_ctx.get() + elapsed_ms)
        
        if elapsed_ms > SLOW_QUERY_THRESHOLD_MS:
            import logging
            logging.getLogger("slow_queries").warning(
                f"Slow query ({elapsed_ms:.1f}ms): {statement[:200]}..."
            )
            # Phase 1.5: Query Plan Analysis
            # In production/staging, you would log EXPLAIN ANALYZE here or run it manually.
            # We log a special prefix so the user can easily find it.
            logging.getLogger("slow_queries").warning(
                f"[PHASE 1.5] Action Required: Run EXPLAIN ANALYZE on the above query!"
            )


def create_engine(database_url: str) -> AsyncEngine:
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    instrument_database(engine)
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
