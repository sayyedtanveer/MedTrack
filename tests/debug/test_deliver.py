import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.config import get_settings
from backend.app.application.delivery.delivery_service import DeliveryService

async def main():
    engine = create_async_engine(get_settings().async_database_url)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        # Get the delivery ID from the user's URL: 6b9f2002-244c-4fee-982e-001921626a7f
        delivery_id = uuid.UUID("6b9f2002-244c-4fee-982e-001921626a7f")
        
        # We need tenant_id. Let's find it.
        from backend.app.infrastructure.persistence.models.delivery_model import DeliveryOrderModel
        from sqlalchemy import select
        
        result = await session.execute(select(DeliveryOrderModel).where(DeliveryOrderModel.id == delivery_id))
        delivery = result.scalar_one_or_none()
        if not delivery:
            print("Delivery not found")
            return
            
        tenant_id = delivery.tenant_id
        
        # Get an admin user
        from backend.app.infrastructure.persistence.models.user_model import UserModel
        result = await session.execute(select(UserModel).where(UserModel.tenant_id == tenant_id, UserModel.role == "admin").limit(1))
        user = result.scalar_one_or_none()
        user_id = user.id if user else uuid.uuid4()
        
        svc = DeliveryService(session)
        try:
            print("Calling deliver()...")
            await svc.deliver(
                tenant_id=tenant_id,
                delivery_id=delivery_id,
                delivered_by=user_id
            )
            print("Success!")
        except Exception as e:
            import traceback
            traceback.print_exc()
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
