import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select

from backend.app.infrastructure.persistence.database import async_session_factory
from backend.app.infrastructure.persistence.models.sales_models import SalesOrderModel, SalesOrderLineModel
from backend.app.infrastructure.persistence.models.inventory_transaction_model import InventoryTransactionModel
from backend.app.infrastructure.persistence.models.inventory_reservation_model import InventoryReservationModel

async def main():
    async with async_session_factory() as session:
        # Check if there are any reservation transactions
        stmt = select(InventoryTransactionModel).where(InventoryTransactionModel.transaction_type == "RESERVATION")
        res = await session.execute(stmt)
        txs = res.scalars().all()
        print(f"Total RESERVATION transactions in DB: {len(txs)}")
        for tx in txs:
            print(f"- tx.id: {tx.id}, ref_type: {tx.reference_type}, ref_id: {tx.reference_id}")
            
        stmt = select(InventoryReservationModel)
        res = await session.execute(stmt)
        reservations = res.scalars().all()
        print(f"\nTotal InventoryReservationModel records: {len(reservations)}")
        for r in reservations:
            print(f"- r.id: {r.id}, ref_type: {r.reference_type}, ref_id: {r.reference_id}, status: {r.status}")

        print("\nLet's find any delivery lines that are causing the issue...")

if __name__ == "__main__":
    asyncio.run(main())
