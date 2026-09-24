import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from backend.app.config import get_settings
from backend.app.infrastructure.persistence.database import Base

settings = get_settings()

# Import all models to ensure they are registered with Base.metadata
from backend.app.infrastructure.persistence.models import (
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
    bom_model,
    workstation_model,
    operation_model,
    bom_operation_model,
    work_order_model,
    sales_models,
    quality_model,
    purchase_order_model,
    supplier_model,
    po_sequence_model,
    material_request_model,
    subcontract_model,
    finance_models,
    technical_document_model,
)

# Import error logging models
from backend.app.infrastructure.logging.models import ErrorLogModel  # noqa: F401

async def init_db():
    print(f"Connecting to database: {settings.database_url}")
    engine = create_async_engine(settings.database_url, echo=True)
    
    print("Creating any missing tables (this uses IF NOT EXISTS safely)...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database sync complete. All phase 8-12 tables have been created!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
