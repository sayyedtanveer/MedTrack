#!/usr/bin/env python3
"""
Debug script to identify the subcontract approval error.
"""

import asyncio
import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.infrastructure.database import engine, AsyncSessionLocal
from backend.app.infrastructure.persistence.models.subcontract_model import SubcontractOrderModel
from backend.app.infrastructure.persistence.models.bom_model import BOMModel


async def debug_order(order_id_str: str):
    """Debug a specific subcontract order approval."""
    order_id = uuid.UUID(order_id_str)
    
    async with AsyncSessionLocal() as session:
        # Get the order
        o = await session.get(SubcontractOrderModel, order_id)
        if not o:
            print(f"❌ Order {order_id} not found")
            return
        
        print(f"✅ Order found: {o.order_number}")
        print(f"   Status: {o.status}")
        print(f"   Tenant: {o.tenant_id}")
        print(f"   BOM ID: {o.bom_id}")
        print(f"   Quantity: {o.quantity}")
        
        if not o.bom_id:
            print("   ℹ️  No BOM linked - approval should work")
            return
        
        # Try to load the BOM
        print(f"\n🔍 Loading BOM {o.bom_id}...")
        try:
            bom_result = await session.execute(
                select(BOMModel)
                .options(selectinload(BOMModel.lines))
                .where(
                    BOMModel.id == o.bom_id,
                    BOMModel.tenant_id == o.tenant_id,
                    BOMModel.is_deleted.is_(False)
                )
            )
            bom = bom_result.scalar_one_or_none()
            
            if not bom:
                print(f"   ❌ BOM not found or deleted")
                print(f"   ⚠️  This will cause approval to silently skip line creation")
                return
            
            print(f"   ✅ BOM found: version {bom.version}")
            print(f"   📋 BOM has {len(bom.lines)} lines")
            
            # Check each line
            material_lines = []
            for i, bl in enumerate(bom.lines, 1):
                print(f"\n   Line {i}:")
                print(f"     - ID: {bl.id}")
                print(f"     - Material ID: {bl.material_id}")
                print(f"     - Template ID: {bl.template_id}")
                print(f"     - Variant ID: {bl.variant_id}")
                print(f"     - Quantity: {bl.quantity}")
                print(f"     - Scrap %: {bl.scrap_percentage}")
                print(f"     - Is Deleted: {bl.is_deleted}")
                
                if bl.material_id and not bl.is_deleted:
                    material_lines.append(bl)
                    print(f"     ✅ Will create order line")
                else:
                    reason = "deleted" if bl.is_deleted else "no material_id"
                    print(f"     ⚠️  Skipped ({reason})")
            
            print(f"\n📊 Summary:")
            print(f"   Total BOM lines: {len(bom.lines)}")
            print(f"   Material lines to create: {len(material_lines)}")
            
            if len(material_lines) == 0:
                print(f"   ⚠️  No material lines! Check if BOM has only templates/variants")
            
        except Exception as e:
            print(f"   ❌ Error loading BOM: {e}")
            import traceback
            traceback.print_exc()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_subcontract_approval.py <order_id>")
        print("Example: python debug_subcontract_approval.py 4412fe8e-b123-4b2f-a766-b2d15db2c89e")
        return 1
    
    order_id = sys.argv[1]
    print(f"Debugging Subcontract Order: {order_id}")
    print("=" * 70)
    
    try:
        await debug_order(order_id)
        await engine.dispose()
        return 0
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        await engine.dispose()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
