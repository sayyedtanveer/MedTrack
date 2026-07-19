"""Subcontract order number generator."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SubcontractNumberService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def generate(self, tenant_id: uuid.UUID) -> str:
        await self._session.execute(
            text("""
                INSERT INTO subcontract_number_sequences (tenant_id, current_value)
                VALUES (:tid, 0)
                ON CONFLICT (tenant_id) DO NOTHING
            """),
            {"tid": str(tenant_id)},
        )
        result = await self._session.execute(
            text("""
                UPDATE subcontract_number_sequences
                SET current_value = current_value + 1
                WHERE tenant_id = :tid
                RETURNING current_value
            """),
            {"tid": str(tenant_id)},
        )
        row = result.fetchone()
        seq = row[0]
        today = date.today().strftime("%Y%m%d")
        return f"SCO-{today}-{seq:04d}"
