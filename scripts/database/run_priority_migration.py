"""
Quick script to add priority column to sales_orders table
Run this once on local/production database
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Parse DATABASE_SYNC_URL from .env
sync_url = os.getenv("DATABASE_SYNC_URL", "postgresql://postgres:123@localhost:5432/medtrack")

# Extract connection params
# Format: postgresql://user:password@host:port/database
parts = sync_url.replace("postgresql://", "").split("@")
user_pass = parts[0].split(":")
host_port_db = parts[1].split("/")
host_port = host_port_db[0].split(":")

conn_params = {
    "user": user_pass[0],
    "password": user_pass[1],
    "host": host_port[0],
    "port": host_port[1],
    "database": host_port_db[1]
}

print(f"🔌 Connecting to database: {conn_params['host']}:{conn_params['port']}/{conn_params['database']}")

try:
    conn = psycopg2.connect(**conn_params)
    conn.autocommit = True
    cur = conn.cursor()
    
    print("✅ Connected successfully")
    print()
    
    # Check if priority column exists
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'sales_orders' AND column_name = 'priority'
    """)
    
    if cur.fetchone():
        print("⏭️  Priority column already exists!")
        print("✅ Nothing to do - database is already up to date")
    else:
        print("➕ Adding priority column...")
        
        # Add priority column
        cur.execute("""
            ALTER TABLE sales_orders 
            ADD COLUMN priority VARCHAR(20) NOT NULL DEFAULT 'NORMAL'
        """)
        print("✅ Added priority column")
        
        # Add check constraint
        cur.execute("""
            ALTER TABLE sales_orders 
            ADD CONSTRAINT ck_sales_order_priority 
            CHECK (priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT'))
        """)
        print("✅ Added priority check constraint")
        
        # Add index
        cur.execute("""
            CREATE INDEX ix_sales_orders_priority 
            ON sales_orders(tenant_id, priority)
        """)
        print("✅ Added priority index")
        
        print()
        print("🎉 Sales Order Priority Enhancement Complete!")
        print()
        print("Priority levels available:")
        print("  🔴 URGENT  - Rush orders, critical deadlines")
        print("  🟠 HIGH    - Important customers, time-sensitive")
        print("  🟢 NORMAL  - Standard orders (default)")
        print("  ⚪ LOW     - Flexible deadlines, buffer stock")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    raise
