import asyncio
import uuid
from sqlalchemy import select
from backend.app.infrastructure.container import Container
from backend.app.config import settings
from backend.app.infrastructure.persistence.models.work_order_model import WorkOrderModel
from backend.app.infrastructure.persistence.models.bom_model import BOMModel, BOMLineModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel

async def main():
    container = Container.create(settings)
    
    async with container.session_factory() as session:
        wo_id = uuid.UUID("5faa5b8c-025c-4637-84e7-0c6a07d57c7f")
        wo = await session.get(WorkOrderModel, wo_id)
        
        if wo:
            print(f"Work Order: {wo.wo_number}, Product ID: {wo.product_id}, Planned Qty: {wo.planned_quantity}")
            
            bom_stmt = select(BOMModel).where(BOMModel.product_id == wo.product_id).limit(1)
            bom = (await session.execute(bom_stmt)).scalar_one_or_none()
            
            if bom:
                print(f"Found BOM: {bom.bom_number}, Base Qty: {bom.base_quantity}")
                
                lines_stmt = select(BOMLineModel, MaterialModel).join(
                    MaterialModel, BOMLineModel.material_id == MaterialModel.id
                ).where(BOMLineModel.bom_id == bom.id)
                lines = (await session.execute(lines_stmt)).all()
                
                for bom_line, material in lines:
                    print(f"  - Material: {material.code} ({material.name}) | BOM Line Qty: {bom_line.quantity}")
            else:
                print("No BOM found for this product.")
        else:
            print("Work Order not found.")

if __name__ == "__main__":
    asyncio.run(main())
