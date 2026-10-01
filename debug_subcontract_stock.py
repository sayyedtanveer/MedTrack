#!/usr/bin/env python3
"""Debug script to check stock availability for subcontract material issue."""
import asyncio
import uuid
import sys
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from backend.app.config import get_settings


async def debug_stock(engine, order_id_str: str):
    """Check stock availability for a subcontract order."""
    order_id = uuid.UUID(order_id_str)
    
    async with engine.begin() as conn:
        # Get the order
        order_result = await conn.execute(
            text("""
                SELECT order_number, tenant_id, status
                FROM subcontract_orders
                WHERE id = :order_id AND is_deleted = false
            """),
            {"order_id": order_id}
        )
        order_row = order_result.fetchone()
        
        if not order_row:
            print(f"❌ Order {order_id} not found")
            return
        
        order_number, tenant_id, status = order_row
        
        print(f"✅ Subcontract Order: {order_number}")
        print(f"   Tenant: {tenant_id}")
        print(f"   Status: {status}")
        print()
        
        # Get order lines
        lines_result = await conn.execute(
            text("""
                SELECT id, material_id, required_quantity, issued_quantity, returned_quantity
                FROM subcontract_order_lines
                WHERE subcontract_order_id = :order_id
                  AND tenant_id = :tenant_id
            """),
            {"order_id": order_id, "tenant_id": tenant_id}
        )
        lines = lines_result.fetchall()
        
        if not lines:
            print("ℹ️  No component lines found (order may not be approved)")
            return
        
        print(f"📋 Component Lines: {len(lines)}")
        print()
        
        # Check stock for each line
        for i, (line_id, material_id, required_qty, issued_qty, returned_qty) in enumerate(lines, 1):
            remaining = max(0, float(required_qty) - float(issued_qty) + float(returned_qty or 0))
            
            print(f"Component {i}: Material {material_id}")
            print(f"  Required: {required_qty}")
            print(f"  Issued: {issued_qty}")
            print(f"  Returned: {returned_qty or 0}")
            print(f"  Remaining: {remaining}")
            print()
            
            # Check stock levels for this material
            stock_result = await conn.execute(
                text("""
                    SELECT 
                        sl.location_id,
                        l.name as location_name,
                        l.type as location_type,
                        sl.stock_status,
                        sl.quantity
                    FROM stock_levels sl
                    JOIN locations l ON l.id = sl.location_id
                    WHERE sl.tenant_id = :tenant_id
                      AND sl.material_id = :material_id
                      AND sl.is_deleted = false
                      AND l.is_deleted = false
                      AND sl.quantity > 0
                    ORDER BY l.type, l.name
                """),
                {"tenant_id": tenant_id, "material_id": material_id}
            )
            
            stock_rows = stock_result.fetchall()
            
            if not stock_rows:
                print(f"  ❌ NO STOCK FOUND for this material!")
                print()
                continue
            
            print(f"  Stock Levels ({len(stock_rows)} locations):")
            
            total_available_internal = Decimal(0)
            internal_location_types = {"warehouse", "zone", "rack", "bin", "production"}
            
            for location_id, location_name, location_type, stock_status, quantity in stock_rows:
                is_internal = location_type in internal_location_types
                is_available = stock_status == "available"
                
                usable = "✓" if (is_internal and is_available) else "✗"
                
                print(f"    {usable} {location_name} ({location_type})")
                print(f"       Status: {stock_status}, Qty: {quantity}")
                
                if is_internal and is_available:
                    total_available_internal += Decimal(str(quantity))
            
            print()
            print(f"  📊 Total Available (Internal Locations): {total_available_internal}")
            print(f"  📊 Remaining to Issue: {remaining}")
            
            if total_available_internal >= Decimal(str(remaining)):
                print(f"  ✅ SUFFICIENT STOCK")
            else:
                shortage = Decimal(str(remaining)) - total_available_internal
                print(f"  ❌ INSUFFICIENT STOCK")
                print(f"     Shortage: {shortage}")
                print(f"     Available: {total_available_internal}")
                print(f"     Required: {remaining}")
            
            print()
            print("  ℹ️  Note: Only 'available' status at internal locations")
            print("     (warehouse, zone, rack, bin, production) can be issued.")
            print()
            print("─" * 70)
            print()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_subcontract_stock.py <order_id>")
        print("Example: python debug_subcontract_stock.py 4412fe8e-b123-4b2f-a766-b2d15db2c89e")
        return 1
    
    order_id = sys.argv[1]
    print("=" * 70)
    print("SUBCONTRACT STOCK AVAILABILITY DEBUG")
    print("=" * 70)
    print()
    
    engine = create_async_engine(get_settings().async_database_url)
    
    try:
        await debug_stock(engine, order_id)
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
