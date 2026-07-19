"""Apply Operation Master schema changes via Python/SQLAlchemy."""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.infrastructure.persistence.database import create_engine
from backend.app.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession


async def apply_schema_changes():
    """Apply the SQL schema changes for Operation Master."""
    
    print("\n" + "=" * 70)
    print("  OPERATION MASTER SCHEMA UPDATE")
    print("=" * 70 + "\n")
    
    try:
        # Read SQL script
        sql_file = Path("db_scripts/add_operation_master_schema.sql")
        if not sql_file.exists():
            print(f"❌ SQL file not found: {sql_file}")
            return False
        
        sql_content = sql_file.read_text()
        print(f"📄 SQL script: {sql_file}")
        print(f"   Size: {len(sql_content)} bytes\n")
        
        # Create engine and execute SQL
        engine = create_engine()
        
        print("🔄 Applying schema changes...")
        print()
        
        async with engine.begin() as connection:
            # Split by semicolons and execute each statement
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]
            
            for i, statement in enumerate(statements, 1):
                try:
                    if not statement:
                        continue
                    
                    # Show progress
                    preview = statement[:60].replace('\n', ' ')
                    if len(statement) > 60:
                        preview += "..."
                    
                    await connection.exec_driver_sql(statement)
                    print(f"  ✅ [{i}/{len(statements)}] {preview}")
                    
                except Exception as e:
                    print(f"  ⚠️  [{i}/{len(statements)}] {preview}")
                    print(f"     Error: {str(e)[:80]}")
                    # Continue with next statement - many are conditional
        
        await engine.dispose()
        
        print("\n" + "=" * 70)
        print("✅ SCHEMA UPDATE COMPLETE")
        print("=" * 70 + "\n")
        print("📋 Next Steps:")
        print("   1. Run: python backend/db_scripts/seed_operations.py")
        print("   2. Verify operations in database")
        print("   3. Test Operation Master API endpoints\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = asyncio.run(apply_schema_changes())
    sys.exit(0 if success else 1)
