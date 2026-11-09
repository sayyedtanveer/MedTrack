import asyncio
import uuid
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine
from backend.app.config import get_settings
from backend.app.infrastructure.persistence.database import create_session_factory
from backend.app.application.quality.handlers.qc_handler import QCHandler
from backend.app.application.quality.commands.qc_commands import ApproveInspectionCommand
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel

async def test_qc_approve():
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url)
    session_factory = create_session_factory(engine)
    
    async with session_factory() as session:
        # Find a work order that is QC_PENDING
        stmt = select(WorkOrderModel).where(WorkOrderModel.status == "QC_PENDING").limit(1)
        result = await session.execute(stmt)
        wo = result.scalar_one_or_none()
        
        if not wo:
            print("No QC_PENDING work order found.")
            return

        print(f"Found QC_PENDING WO: {wo.wo_number} (ID: {wo.id})")
        
        try:
            handler = QCHandler(session)
            # Find an admin user to act as inspector
            res = await session.execute(text("SELECT id, tenant_id FROM users WHERE role='admin' LIMIT 1"))
            user_row = res.fetchone()
            if not user_row:
                print("No admin user found")
                return
            
            user_id = user_row[0]
            tenant_id = user_row[1]
            
            print("Executing QC approval...")
            cmd = ApproveInspectionCommand(
                tenant_id=tenant_id,
                work_order_id=wo.id,
                inspector_id=user_id,
                remarks="Automated test script approval",
                details=[]
            )
            await handler.approve_inspection(cmd)
            
            await session.commit()
            print("Successfully approved QC and committed transaction!")
            
        except Exception as e:
            await session.rollback()
            print(f"QC Approval failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_qc_approve())
