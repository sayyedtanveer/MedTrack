import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from backend.app.config import get_settings
from backend.app.infrastructure.persistence.models.item_template_model import ItemTemplateModel

settings = get_settings()

async def test_query():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            print("Testing item_templates query...")
            stmt = select(ItemTemplateModel).limit(1)
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()
            
            if template:
                print(f"\n[OK] Query successful!")
                print(f"  ID: {template.id}")
                print(f"  Code: {template.code}")
                print(f"  Name: {template.name}")
                print(f"  Status: {template.status}")
                print(f"  Is Active: {template.is_active}")
            else:
                print("[OK] Query successful (no templates exist)")
            
            # Now test count query (like the original error)
            count_result = await session.execute(select(ItemTemplateModel))
            templates = count_result.scalars().all()
            print(f"\n[OK] Count query successful: {len(templates)} templates found")
            
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()

asyncio.run(test_query())
