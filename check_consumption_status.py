"""
Check Subcontract Consumption Status
Run after backend restart to verify consumption logic is working
"""
import asyncio
import asyncpg
from datetime import datetime, timedelta

DATABASE_URL = "postgresql://postgres:123@localhost:5432/medtrack"


def simple_table(headers, rows):
    """Simple table formatter without external dependencies"""
    if not rows:
        return "No data"
    
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Format header
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    separator = "-+-".join("-" * w for w in col_widths)
    
    # Format rows
    result = [header_line, separator]
    for row in rows:
        result.append(" | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)))
    
    return "\n".join(result)


async def check_consumption_status():
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("=" * 80)
        print("SUBCONTRACT CONSUMPTION STATUS CHECK")
        print("=" * 80)
        print()
        
        # 1. Check consumed_quantity column exists
        print("1. Checking consumed_quantity column...")
        result = await conn.fetch("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns 
            WHERE table_name = 'subcontract_order_lines' 
              AND column_name = 'consumed_quantity'
        """)
        if result:
            print("✓ consumed_quantity column exists")
            print(f"  Type: {result[0]['data_type']}, Default: {result[0]['column_default']}")
        else:
            print("✗ consumed_quantity column NOT FOUND!")
            return
        print()
        
        # 2. Recent subcontract orders
        print("2. Recent Subcontract Orders (last 7 days):")
        orders = await conn.fetch("""
            SELECT 
                so.order_number,
                so.status,
                so.created_at::date as order_date,
                m.code as semi_finished_code,
                m.name as semi_finished_name,
                so.quantity as ordered_quantity,
                so.received_quantity,
                s.name as subcontractor_name
            FROM subcontract_orders so
            JOIN materials m ON so.product_id = m.id
            JOIN suppliers s ON so.supplier_id = s.id
            WHERE so.created_at >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY so.created_at DESC
        """)
        if orders:
            table_data = [
                [
                    o['order_number'],
                    o['status'],
                    str(o['order_date']),
                    o['semi_finished_code'],
                    f"{o['ordered_quantity']}/{o['received_quantity']}",
                    o['subcontractor_name'][:20]
                ]
                for o in orders
            ]
            print(simple_table(
                ['Order#', 'Status', 'Date', 'Semi-FG', 'Ordered/Received', 'Subcontractor'],
                table_data
            ))
        else:
            print("  No orders in last 7 days")
        print()
        
        # 3. Raw material consumption details
        print("3. Raw Material Consumption Status:")
        lines = await conn.fetch("""
            SELECT 
                so.order_number,
                sol.material_id,
                rm.code as raw_material_code,
                rm.name as raw_material_name,
                sol.required_quantity,
                sol.issued_quantity,
                sol.consumed_quantity,
                sol.returned_quantity,
                (sol.issued_quantity - sol.consumed_quantity - sol.returned_quantity) as remaining
            FROM subcontract_order_lines sol
            JOIN subcontract_orders so ON sol.subcontract_order_id = so.id
            JOIN materials rm ON sol.material_id = rm.id
            WHERE so.created_at >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY so.created_at DESC, sol.material_id
        """)
        if lines:
            table_data = [
                [
                    l['order_number'],
                    l['raw_material_code'],
                    f"{float(l['required_quantity']):.2f}",
                    f"{float(l['issued_quantity']):.2f}",
                    f"{float(l['consumed_quantity']):.2f}",
                    f"{float(l['returned_quantity']):.2f}",
                    f"{float(l['remaining']):.2f}"
                ]
                for l in lines
            ]
            print(simple_table(
                ['Order#', 'Material', 'Required', 'Issued', 'Consumed', 'Returned', 'Remaining'],
                table_data
            ))
            
            # Check if any consumption happened
            total_consumed = sum(float(l['consumed_quantity']) for l in lines)
            if total_consumed > 0:
                print(f"\n✓ Consumption is working! Total consumed: {total_consumed:.2f}")
            else:
                print("\n⚠ WARNING: No consumption recorded yet. consumed_quantity = 0 for all lines.")
                print("  This is expected if no receipts have been done since backend restart.")
        else:
            print("  No raw material lines in recent orders")
        print()
        
        # 4. Recent inventory transactions
        print("4. Recent Subcontract Inventory Transactions:")
        transactions = await conn.fetch("""
            SELECT 
                it.transaction_date,
                it.transaction_type,
                m.code as material_code,
                it.quantity,
                l.name as location_name,
                it.notes
            FROM inventory_transactions it
            JOIN materials m ON it.material_id = m.id
            LEFT JOIN locations l ON it.location_id = l.id
            WHERE it.transaction_type IN ('SUBCONTRACT_ISSUE', 'SUBCONTRACT_CONSUMPTION', 'SUBCONTRACT_RETURN')
              AND it.transaction_date >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY it.transaction_date DESC
            LIMIT 20
        """)
        if transactions:
            table_data = [
                [
                    t['transaction_date'].strftime('%Y-%m-%d %H:%M'),
                    t['transaction_type'],
                    t['material_code'],
                    f"{float(t['quantity']):.2f}",
                    (t['location_name'] or 'N/A')[:30]
                ]
                for t in transactions
            ]
            print(simple_table(
                ['Date/Time', 'Type', 'Material', 'Qty', 'Location'],
                table_data
            ))
            
            # Check if consumption transactions exist
            consumption_txns = [t for t in transactions if t['transaction_type'] == 'SUBCONTRACT_CONSUMPTION']
            if consumption_txns:
                print(f"\n✓ Found {len(consumption_txns)} CONSUMPTION transactions")
            else:
                print("\n⚠ No SUBCONTRACT_CONSUMPTION transactions found")
        else:
            print("  No subcontract transactions in last 7 days")
        print()
        
        # 5. Stock by location for recent materials
        print("5. Stock by Location (Recent Subcontract Materials):")
        stock_by_loc = await conn.fetch("""
            SELECT 
                m.code,
                m.name,
                l.name as location_name,
                l.location_type,
                SUM(sl.quantity) as quantity_at_location
            FROM stock_levels sl
            JOIN materials m ON sl.material_id = m.id
            JOIN locations l ON sl.location_id = l.id
            WHERE m.id IN (
                SELECT DISTINCT material_id 
                FROM subcontract_order_lines
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            )
            GROUP BY m.code, m.name, l.name, l.location_type
            ORDER BY m.code, l.location_type, l.name
        """)
        if stock_by_loc:
            table_data = [
                [
                    s['code'],
                    s['name'][:30],
                    s['location_name'][:30],
                    s['location_type'],
                    f"{float(s['quantity_at_location']):.2f}"
                ]
                for s in stock_by_loc
            ]
            print(simple_table(
                ['Code', 'Material', 'Location', 'Type', 'Quantity'],
                table_data
            ))
        else:
            print("  No stock data for recent materials")
        print()
        
        print("=" * 80)
        print("RECOMMENDATIONS:")
        print("=" * 80)
        
        # Generate recommendations
        if not orders:
            print("• Create a NEW subcontract order to test consumption logic")
        elif lines and sum(float(l['consumed_quantity']) for l in lines) == 0:
            print("• Consumption not yet triggered. Do a receipt on any order to test.")
        elif lines and sum(float(l['consumed_quantity']) for l in lines) > 0:
            print("• ✓ Consumption logic is working correctly!")
        
        has_consumption_txns = any(
            t['transaction_type'] == 'SUBCONTRACT_CONSUMPTION' 
            for t in transactions
        ) if transactions else False
        
        if not has_consumption_txns:
            print("• No CONSUMPTION transactions yet - expected if no receipts since restart")
        
        print()
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_consumption_status())
