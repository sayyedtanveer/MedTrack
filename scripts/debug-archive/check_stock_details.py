"""Check stock details for raw materials in recent subcontracts"""
import asyncio
import asyncpg

DATABASE_URL = "postgresql://postgres:123@localhost:5432/medtrack"

async def check_stock():
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("\n" + "="*80)
        print("STOCK ANALYSIS FOR RECENT SUBCONTRACTS")
        print("="*80 + "\n")
        
        # Get raw materials from recent subcontract orders
        result = await conn.fetch("""
            SELECT DISTINCT
                m.code,
                m.name,
                m.current_stock as total_stock,
                sol.required_quantity,
                sol.issued_quantity,
                sol.consumed_quantity,
                sol.returned_quantity,
                so.order_number,
                so.status
            FROM materials m
            JOIN subcontract_order_lines sol ON sol.material_id = m.id
            JOIN subcontract_orders so ON so.id = sol.subcontract_order_id
            WHERE so.created_at >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY so.order_number, m.code
        """)
        
        print("Material Stock vs Subcontract Status:\n")
        print(f"{'Order':<20} {'Material':<12} {'Total':<10} {'Required':<10} {'Issued':<10} {'Consumed':<10} {'Status':<12}")
        print("-" * 100)
        
        for row in result:
            print(f"{row['order_number']:<20} {row['code']:<12} {float(row['total_stock']):<10.1f} {float(row['required_quantity']):<10.1f} {float(row['issued_quantity']):<10.1f} {float(row['consumed_quantity']):<10.1f} {row['status']:<12}")
        
        print("\n" + "="*80)
        print("STOCK BY LOCATION (Recent Materials)")
        print("="*80 + "\n")
        
        # Get stock by location for these materials
        stock_loc = await conn.fetch("""
            SELECT 
                m.code,
                m.name,
                l.name as location_name,
                l.type as location_type,
                sl.quantity,
                sl.stock_status
            FROM materials m
            JOIN stock_levels sl ON sl.material_id = m.id
            JOIN locations l ON l.id = sl.location_id
            WHERE m.id IN (
                SELECT DISTINCT material_id 
                FROM subcontract_order_lines sol
                JOIN subcontract_orders so ON so.id = sol.subcontract_order_id
                WHERE so.created_at >= CURRENT_DATE - INTERVAL '7 days'
            )
            AND sl.quantity > 0
            AND sl.is_deleted = FALSE
            ORDER BY m.code, l.type, l.name
        """)
        
        print(f"{'Material':<12} {'Location':<30} {'Type':<15} {'Quantity':<10} {'Status':<15}")
        print("-" * 90)
        
        for row in stock_loc:
            print(f"{row['code']:<12} {row['location_name']:<30} {row['location_type']:<15} {float(row['quantity']):<10.1f} {row['stock_status']:<15}")
        
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print("\nFor each raw material:")
        print("- Total Stock = materials.current_stock (aggregate)")
        print("- Warehouse Stock = SUM(stock_levels.quantity) WHERE location.type IN ('warehouse', ...)")
        print("- Subcontractor Stock = SUM(stock_levels.quantity) WHERE location.type = 'subcontractor'")
        print("\nAfter consumption:")
        print("- consumed_quantity increases")
        print("- stock_levels.quantity at subcontractor location DECREASES")
        print("- materials.current_stock DECREASES")
        print()
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_stock())
