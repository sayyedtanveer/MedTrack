from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Ensure imports resolve from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app.config import get_settings
from backend.app.infrastructure.persistence.database import Base

# Import all models so Alembic sees them for autogenerate
from backend.app.infrastructure.persistence.models import (  # noqa: F401
    tenant_model,
    user_model,
    audit_log_model,
    material_model,
    inventory_transaction_model,
    material_category_model,
    unit_of_measure_model,
    uom_conversion_model,
    location_model,
    batch_model,
    serial_number_model,
    item_template_model,
    item_variant_model,
    item_code_sequence_model,
    bom_model,
    workstation_model,
    operation_model,
    bom_operation_model,
    work_order_model,
    sales_models,
    quality_model,
    purchase_order_model,
    grn_model,
    supplier_model,
    po_sequence_model,
    material_request_model,
    mrp_model,
    subcontract_model,
    finance_models,
    inventory_management_models,
    document_model,
)

# Import error logging models for Alembic autogenerate
from backend.app.infrastructure.logging.models import ErrorLogModel  # noqa: F401

config = context.config
settings = get_settings()

# Override sqlalchemy.url from env/settings (sync driver for migrations)
config.set_main_option("sqlalchemy.url", settings.sync_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(
        settings.async_database_url,
        poolclass=pool.NullPool,
    )
    async with engine.connect() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
