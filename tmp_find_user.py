import asyncio, sys
sys.path.insert(0, '.')

async def main():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    from backend.app.config import get_settings
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url, echo=False)
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT id, email, role, is_active, tenant_id, hashed_password "
            "FROM users WHERE email = 'admin.e2e@medtrack-demo.com'"
        ))
        rows = result.fetchall()
        if not rows:
            print("USER NOT FOUND: admin.e2e@medtrack-demo.com")
        for r in rows:
            print(f"  id={r[0]}")
            print(f"  email={r[1]}")
            print(f"  role={r[2]}")
            print(f"  active={r[3]}")
            print(f"  tenant_id={r[4]}")
            print(f"  hash_prefix={r[5][:20] if r[5] else 'NULL'}")
    await engine.dispose()

asyncio.run(main())
