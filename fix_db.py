import asyncio
import os
import asyncpg

async def fix_db():
    database_url = os.environ.get("DATABASE_URL", "postgresql://postgres:123@localhost:5432/medtrack")
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute("ALTER TABLE notifications DROP COLUMN IF EXISTS type;")
        await conn.execute("ALTER TABLE notifications DROP COLUMN IF EXISTS sent_at;")
        await conn.execute("ALTER TABLE notifications DROP COLUMN IF EXISTS email_sent;")
        await conn.execute("ALTER TABLE notifications DROP COLUMN IF EXISTS email_sent_at;")
        print("Columns dropped successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_db())
