"""
Quick script to check if brass2x material exists in database
"""
import asyncio
import sys
from sqlalchemy import select
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.session import async_session_maker

async def check_brass():
    async with async_session_maker() as session:
        # Search for materials with 'brass' in the name
        stmt = select(MaterialModel).where(MaterialModel.name.ilike('%brass%'))
        result = await session.execute(stmt)
        materials = result.scalars().all()
        
        if not materials:
            print("❌ No materials found with 'brass' in the name")
            return
        
        print(f"✅ Found {len(materials)} material(s) with 'brass' in name:\n")
        for mat in materials:
            print(f"  ID: {mat.id}")
            print(f"  Code: {mat.code}")
            print(f"  Name: {mat.name}")
            print(f"  Category: {mat.category}")
            print(f"  Type: {mat.material_type}")
            print(f"  Current Stock: {mat.current_stock}")
            print(f"  Reserved Stock: {mat.reserved_stock}")
            print(f"  Min Stock: {mat.safety_stock}")
            print(f"  Max Stock: {mat.reorder_level}")
            print(f"  Is Active: {mat.is_active}")
            print(f"  Is Deleted: {mat.is_deleted}")
            print()

if __name__ == "__main__":
    asyncio.run(check_brass())
