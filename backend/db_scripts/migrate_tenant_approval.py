import os
import sys
from sqlalchemy import text, create_engine
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.tenant_audit_log_model import TenantAuditLogModel

def migrate():
    load_dotenv()
    
    # Use sync engine for migration
    engine = create_engine(settings.sync_database_url)
    
    with engine.begin() as conn:
        print("Adding 'status' column to 'tenants' table...")
        try:
            conn.execute(text("ALTER TABLE tenants ADD COLUMN status VARCHAR(20) DEFAULT 'pending' NOT NULL;"))
            print("Successfully added 'status'.")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("'status' column already exists.")
            else:
                print(f"Error adding 'status': {e}")
                
        print("Adding 'is_system_tenant' column to 'tenants' table...")
        try:
            conn.execute(text("ALTER TABLE tenants ADD COLUMN is_system_tenant BOOLEAN DEFAULT FALSE NOT NULL;"))
            print("Successfully added 'is_system_tenant'.")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("'is_system_tenant' column already exists.")
            else:
                print(f"Error adding 'is_system_tenant': {e}")
                
        print("Updating existing tenants to 'active' status...")
        conn.execute(text("UPDATE tenants SET status = 'active' WHERE status = 'pending' OR status IS NULL;"))
        
        print("Creating tenant_audit_logs table if it doesn't exist...")
        Base.metadata.create_all(engine, tables=[TenantAuditLogModel.__table__])
        print("tenant_audit_logs table verified/created.")

    print("Migration complete!")

if __name__ == "__main__":
    migrate()
