"""Seed default manufacturing operations for all tenants.

This script adds standard manufacturing operations to the database:
- 10: Cutting
- 20: Machining
- 30: Assembly
- 40: Calibration
- 50: Leak Testing
- 60: QC Inspection
- 70: Packaging

Idempotent: Safe to run multiple times.
"""

import asyncio
import uuid
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.infrastructure.persistence.models.operation_model import OperationModel
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel


# Default manufacturing operations seeded for each tenant
DEFAULT_OPERATIONS = [
    {
        "operation_code": "10",
        "name": "Cutting",
        "operation_type": "cutting",
        "description": "Cut raw materials to required dimensions",
        "default_sequence": 10,
        "estimated_time_minutes": Decimal("15.00"),
        "qc_required": False,
        "color": "#FF6B6B",
        "icon_code": "cut",
    },
    {
        "operation_code": "20",
        "name": "Machining",
        "operation_type": "machining",
        "description": "Machine components to precise specifications",
        "default_sequence": 20,
        "estimated_time_minutes": Decimal("30.00"),
        "qc_required": False,
        "color": "#4ECDC4",
        "icon_code": "hammer",
    },
    {
        "operation_code": "30",
        "name": "Assembly",
        "operation_type": "assembly",
        "description": "Assemble components into sub-assemblies or finished products",
        "default_sequence": 30,
        "estimated_time_minutes": Decimal("20.00"),
        "qc_required": False,
        "color": "#95E1D3",
        "icon_code": "box",
    },
    {
        "operation_code": "40",
        "name": "Calibration",
        "operation_type": "calibration",
        "description": "Calibrate and adjust assembled units",
        "default_sequence": 40,
        "estimated_time_minutes": Decimal("25.00"),
        "qc_required": True,
        "color": "#F38181",
        "icon_code": "sliders",
    },
    {
        "operation_code": "50",
        "name": "Leak Testing",
        "operation_type": "testing",
        "description": "Test for leaks and seal integrity",
        "default_sequence": 50,
        "estimated_time_minutes": Decimal("15.00"),
        "qc_required": True,
        "color": "#AA96DA",
        "icon_code": "droplet",
    },
    {
        "operation_code": "60",
        "name": "QC Inspection",
        "operation_type": "inspection",
        "description": "Final quality control inspection",
        "default_sequence": 60,
        "estimated_time_minutes": Decimal("10.00"),
        "qc_required": True,
        "color": "#FCBAD3",
        "icon_code": "check-circle",
    },
    {
        "operation_code": "70",
        "name": "Packaging",
        "operation_type": "packaging",
        "description": "Package finished products for shipment",
        "default_sequence": 70,
        "estimated_time_minutes": Decimal("10.00"),
        "qc_required": False,
        "color": "#A8D8EA",
        "icon_code": "package",
    },
]


async def seed_operations(session: AsyncSession, tenant_id: uuid.UUID, system_user_id: uuid.UUID):
    """Seed default operations for a tenant."""
    
    for op_data in DEFAULT_OPERATIONS:
        # Check if operation already exists
        stmt = select(OperationModel).where(
            OperationModel.tenant_id == tenant_id,
            OperationModel.operation_code == op_data["operation_code"],
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            # Create new operation
            operation = OperationModel(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                operation_code=op_data["operation_code"],
                name=op_data["name"],
                operation_type=op_data["operation_type"],
                description=op_data["description"],
                default_sequence=op_data["default_sequence"],
                estimated_time_minutes=op_data["estimated_time_minutes"],
                qc_required=op_data["qc_required"],
                is_active=True,
                color=op_data["color"],
                icon_code=op_data["icon_code"],
                created_by=system_user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_deleted=False,
            )
            session.add(operation)
            print(f"  ✓ Created operation: {op_data['operation_code']} - {op_data['name']}")
        else:
            print(f"  - Operation already exists: {op_data['operation_code']} - {op_data['name']}")

    await session.flush()


async def main():
    """Main seeding function."""
    from backend.app.infrastructure.persistence.database import create_engine
    from backend.app.config import settings

    print("\n" + "=" * 70)
    print("SEEDING DEFAULT MANUFACTURING OPERATIONS")
    print("=" * 70 + "\n")

    # Create async engine
    engine = create_engine()
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Get all tenants
            stmt = select(TenantModel).where(TenantModel.is_deleted.is_(False))
            result = await session.execute(stmt)
            tenants = result.scalars().all()

            if not tenants:
                print("⚠ No tenants found. Nothing to seed.")
                return

            print(f"Found {len(tenants)} tenant(s). Seeding operations...\n")

            # Seed operations for each tenant
            for tenant in tenants:
                print(f"Seeding tenant: {tenant.name} ({tenant.id})")
                
                # Use tenant owner as system user (or first admin)
                system_user_id = tenant.created_by or uuid.uuid4()
                
                await seed_operations(session, tenant.id, system_user_id)
                print()

            # Commit all changes
            await session.commit()
            print("=" * 70)
            print("✓ SEEDING COMPLETE")
            print("=" * 70 + "\n")

        except Exception as e:
            await session.rollback()
            print(f"\n✗ ERROR: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
