"""Debug script to check subcontract issue inventory impact and prove stock was deducted"""
import asyncio
import sys
import uuid
from decimal import Decimal
sys.path.insert(0, 'backend')

from sqlalchemy import select
from app.infrastructure.persistence.database import get_session_factory
from app.infrastructure.persistence.models.material_model import MaterialModel
from app.infrastructure.persistence.models.stock_level_model import StockLevelModel
from app.infrastructure.persistence.models.location_model import LocationModel
from app.infrastructure.persistence.models.subcontract_model import SubcontractMaterialIssueModel

async def check_subcontract_issue(order_id_str: str = None, material_code: str = None):
async def check_subcontract_issue(order_id_str: str = None, material_code: str = None):
    """Check inventory before and after subcontract issue"""
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        
        # If material code provided, show its stock breakdown
        if material_code:
            print(f"\n{'='*90}")
            print(f"STOCK BREAKDOWN FOR MATERIAL: {material_code}")
            print(f"{'='*90}\n")
            
            # Get material
            mat_stmt = select(MaterialModel).where(MaterialModel.code == material_code)
            mat_result = await session.execute(mat_stmt)
            material = mat_result.scalar_one_or_none()
            
            if not material:
                print(f"Material {material_code} not found!")
                return
            
            print(f"Material: {material.code} - {material.name}")
            print(f"Total Stock (all locations): {material.current_stock}")
            print(f"Reserved Stock: {material.reserved_stock}")
            print(f"Available Stock: {material.current_stock - material.reserved_stock}")
            
            # Get stock levels by location
            stock_stmt = (
                select(StockLevelModel, LocationModel)
                .join(LocationModel, LocationModel.id == StockLevelModel.location_id)
                .where(
                    StockLevelModel.material_id == material.id,
                    StockLevelModel.is_deleted == False,
                    StockLevelModel.quantity > 0
                )
                .order_by(LocationModel.type, LocationModel.name)
            )
            stock_result = await session.execute(stock_stmt)
            stock_rows = stock_result.all()
            
            print(f"\n{'='*90}")
            print(f"STOCK BY LOCATION (This proves stock was deducted from warehouse!):")
            print(f"{'='*90}")
            print(f"{'Location':<40} {'Type':<20} {'Status':<15} {'Quantity':>12}")
            print(f"{'-'*90}")
            
            warehouse_total = 0
            subcontractor_total = 0
            
            for stock, location in stock_rows:
                print(f"{location.name:<40} {location.type:<20} {stock.stock_status:<15} {stock.quantity:>12.3f}")
                
                if location.type in ['warehouse', 'zone', 'rack', 'bin']:
                    warehouse_total += stock.quantity
                elif location.type == 'subcontractor':
                    subcontractor_total += stock.quantity
            
            print(f"{'-'*90}")
            print(f"{'Warehouse Total':<75} {warehouse_total:>12.3f}")
            print(f"{'Subcontractor Total':<75} {subcontractor_total:>12.3f}")
            print(f"{'='*90}")
            print(f"{'GRAND TOTAL (matches material.current_stock)':<75} {material.current_stock:>12.3f}")
            print(f"{'='*90}\n")
            
            if subcontractor_total > 0:
                print("✅ PROOF: Stock HAS been deducted from warehouse and moved to subcontractor!")
                print(f"   - Warehouse stock: {warehouse_total}")
                print(f"   - At subcontractor: {subcontractor_total}")
                print(f"   - The UI shows total ({material.current_stock}) but warehouse actually has less!\n")
            
            return
        
        # Original order-based check
        if not order_id_str:
            print("ERROR: Provide either order_id or material_code")
            return
            
        try:
            order_id = uuid.UUID(order_id_str)
        except ValueError:
            print(f"Invalid order ID: {order_id_str}")
            return
        
        # Get all issues for this order
        stmt = select(SubcontractMaterialIssueModel).where(
            SubcontractMaterialIssueModel.subcontract_order_id == order_id
        )
        result = await session.execute(stmt)
        issues = result.scalars().all()
        
        if not issues:
            print(f"No material issues found for order {order_id_str}")
            return
        
        print(f"\n{'='*90}")
        print(f"Subcontract Order: {order_id_str}")
        print(f"{'='*90}\n")
        
        for issue in issues:
            print(f"\nIssue ID: {issue.id}")
            print(f"Material ID: {issue.material_id}")
            print(f"Quantity Issued: {issue.quantity}")
            print(f"From Location: {issue.from_location_id}")
            print(f"Batch: {issue.batch_number or 'None'}")
            
            # Get material details
            mat_stmt = select(MaterialModel).where(MaterialModel.id == issue.material_id)
            mat_result = await session.execute(mat_stmt)
            material = mat_result.scalar_one_or_none()
            
            if material:
                print(f"\nMaterial: {material.code} - {material.name}")
                print(f"Total Stock (all locations): {material.current_stock}")
                print(f"Reserved Stock: {material.reserved_stock}")
                print(f"Available Stock: {material.current_stock - material.reserved_stock}")
            
            # Get stock levels by location
            stock_stmt = (
                select(StockLevelModel, LocationModel)
                .join(LocationModel, LocationModel.id == StockLevelModel.location_id)
                .where(
                    StockLevelModel.material_id == issue.material_id,
                    StockLevelModel.is_deleted == False,
                    StockLevelModel.quantity > 0
                )
            )
            stock_result = await session.execute(stock_stmt)
            stock_rows = stock_result.all()
            
            print(f"\nStock Levels by Location:")
            print(f"{'Location':<40} {'Type':<20} {'Status':<15} {'Quantity':>12}")
            print(f"{'-'*90}")
            
            for stock, location in stock_rows:
                print(f"{location.name:<40} {location.type:<20} {stock.stock_status:<15} {stock.quantity:>12.3f}")
            
            print(f"\n{'-'*90}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  By Order ID:     python debug_subcontract_issue.py <order_id>")
        print("  By Material:     python debug_subcontract_issue.py --material <material_code>")
        print()
        print("Examples:")
        print("  python debug_subcontract_issue.py 4412fe8e-b123-4b2f-a766-b2d15db2c89e")
        print("  python debug_subcontract_issue.py --material RM-MT-0004")
        sys.exit(1)
    
    if sys.argv[1] == '--material' and len(sys.argv) >= 3:
        asyncio.run(check_subcontract_issue(material_code=sys.argv[2]))
    else:
        asyncio.run(check_subcontract_issue(order_id_str=sys.argv[1]))
