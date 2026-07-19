import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from backend.app.config import get_settings

settings = get_settings()

async def check_column():
    engine = create_async_engine(settings.database_url)
    
    async with engine.begin() as conn:
        result = await conn.execute(text('''
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='item_templates' AND column_name='status'
        '''))
        exists = result.scalar()
        if exists:
            print('✓ Status column exists')
        else:
            print('✗ Status column missing - adding now...')
            await conn.execute(text("ALTER TABLE item_templates ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'"))
            print('✓ Status column added')
    
    await engine.dispose()

asyncio.run(check_column())
