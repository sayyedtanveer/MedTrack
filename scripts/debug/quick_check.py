"""Quick consumption check - simplified"""
import asyncio
import asyncpg

DATABASE_URL = "postgresql://postgres:123@localhost:5432/medtrack"

async def quick_check():
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("\n" + "="*80)
        print("SUBCONTRACT CONSUMPTION - QUICK CHECK")
        print("="*80 + "\n")
        
        # Check recent orders and their consumption
        result = await conn.fetch("""
            SELECT 
                so.order_number,
                so.status,
                so.quantity as ordered,
                so.received_quantity as received,
                so.created_at::date as created,
                COUNT(sol.id) as material_count,
                SUM(sol.consumed_quantity) as total_consumed,
                SUM(sol.issued_quantity) as total_issued
            FROM subcontract_orders so
            LEFT JOIN subcontract_order_lines sol ON sol.subcontract_order_id = so.id
            WHERE so.created_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY so.id, so.order_number, so.status, so.quantity, so.received_quantity, so.created_at
            ORDER BY so.created_at DESC
        """)
        
        if not result:
            print("❌ No subcontract orders in last 7 days")
            print("\n→ Create a NEW subcontract order to test consumption logic\n")
            return
        
        for row in result:
            print(f"Order: {row['order_number']}")
            print(f"Status: {row['status']}")
            print(f"Created: {row['created']}")
            print(f"Ordered/Received: {float(row['ordered']):.1f} / {float(row['received']):.1f}")
            print(f"Raw Materials: {row['material_count']} items")
            print(f"Total Issued: {float(row['total_issued']):.2f}")
            print(f"Total Consumed: {float(row['total_consumed']):.2f}")
            
            if float(row['received']) > 0 and float(row['total_consumed']) == 0:
                print("⚠️  WARNING: Receipt done but NO consumption recorded!")
                print("   → This receipt was done BEFORE backend restart")
            elif float(row['total_consumed']) > 0:
                print("✅ Consumption is working!")
            else:
                print("ℹ️  No receipt done yet (normal)")
            
            print("-" * 80)
        
        print("\n" + "="*80)
        print("NEXT STEPS:")
        print("="*80)
        
        has_old_receipt = any(
            float(r['received']) > 0 and float(r['total_consumed']) == 0
            for r in result
        )
        
        if has_old_receipt:
            print("\n1. OLD ORDER DETECTED (receipt done before restart)")
            print("   → Consumption will NOT work retroactively for this order")
            print("   → You need to create a NEW subcontract order\n")
            print("2. CREATE NEW ORDER:")
            print("   → Manufacturing → Subcontract Orders → Create New")
            print("   → Issue materials")
            print("   → Receive semi-finished product")
            print("   → Check consumption in Stock Locations tab\n")
        else:
            print("\n✅ No old receipts detected")
            print("→ Do a receipt on any order and consumption will trigger\n")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(quick_check())
