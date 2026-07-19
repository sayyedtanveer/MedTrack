"""Supplier performance computation service.

Metrics:
 - on_time_delivery_pct   : % of received POs where actual receipt <= expected_delivery
 - quality_acceptance_pct : % of quality inspections marked 'pass' for this supplier's POs
 - avg_lead_time_days     : average calendar days from PO order_date to received date
 - price_trend            : last 3 unit-price data points per material (from supplier_price_history)
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.purchase_order_model import (
    PurchaseOrderModel,
)
from backend.app.infrastructure.persistence.models.quality_model import (
    QualityInspectionModel,
)
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel


class SupplierPerformanceService:
    def __init__(self, session: AsyncSession):
        self._s = session

    # ------------------------------------------------------------------ #
    async def get_performance(
        self, tenant_id: uuid.UUID, supplier_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Return a performance snapshot for a single supplier."""
        supplier = await self._s.get(SupplierModel, supplier_id)
        if not supplier or supplier.tenant_id != tenant_id or supplier.is_deleted:
            return {}

        on_time_pct = await self._on_time_delivery(tenant_id, supplier_id)
        quality_pct = await self._quality_acceptance(tenant_id, supplier_id)
        avg_lead = await self._avg_lead_time(tenant_id, supplier_id)
        price_hist = await self._price_history(tenant_id, supplier_id)

        return {
            "supplier_id": str(supplier_id),
            "supplier_name": supplier.name,
            "supplier_code": supplier.code,
            "on_time_delivery_pct": on_time_pct,
            "quality_acceptance_pct": quality_pct,
            "avg_lead_time_days": avg_lead,
            "performance_rating": float(supplier.performance_rating) if supplier.performance_rating else None,
            "price_history": price_hist,
        }

    # ------------------------------------------------------------------ #
    async def list_all_performance(self, tenant_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Return performance snapshots for all active suppliers."""
        stmt = select(SupplierModel).where(
            SupplierModel.tenant_id == tenant_id,
            SupplierModel.is_deleted.is_(False),
            SupplierModel.is_active.is_(True),
        )
        r = await self._s.execute(stmt)
        suppliers = r.scalars().all()

        results = []
        for s in suppliers:
            perf = await self.get_performance(tenant_id, s.id)
            if perf:
                results.append(perf)
        return results

    # ── private helpers ------------------------------------------------ #

    async def _on_time_delivery(
        self, tenant_id: uuid.UUID, supplier_id: uuid.UUID
    ) -> float | None:
        """% of received POs that were received on or before expected_delivery."""
        result = await self._s.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (WHERE expected_delivery IS NOT NULL)     AS total_with_deadline,
                    COUNT(*) FILTER (
                        WHERE expected_delivery IS NOT NULL
                          AND updated_at::date <= expected_delivery
                    )                                                         AS on_time
                FROM purchase_orders
                WHERE tenant_id = :tid
                  AND supplier_id = :sid
                  AND status = 'received'
                  AND is_deleted = false
            """),
            {"tid": str(tenant_id), "sid": str(supplier_id)},
        )
        row = result.fetchone()
        if not row or not row[0]:
            return None
        total, on_time = row
        if total == 0:
            return None
        return round(on_time / total * 100, 1)

    async def _quality_acceptance(
        self, tenant_id: uuid.UUID, supplier_id: uuid.UUID
    ) -> float | None:
        """% of quality inspections for this supplier's receipts that passed."""
        result = await self._s.execute(
            text("""
                SELECT
                    COUNT(*)                                      AS total,
                    COUNT(*) FILTER (WHERE qi.result = 'pass')   AS passed
                FROM quality_inspections qi
                JOIN purchase_orders po
                    ON po.id = qi.reference_id
                WHERE qi.tenant_id     = :tid
                  AND po.supplier_id   = :sid
                  AND qi.reference_type = 'purchase_receipt'
                  AND po.is_deleted     = false
            """),
            {"tid": str(tenant_id), "sid": str(supplier_id)},
        )
        row = result.fetchone()
        if not row or not row[0]:
            return None
        total, passed = row
        if total == 0:
            return None
        return round(passed / total * 100, 1)

    async def _avg_lead_time(
        self, tenant_id: uuid.UUID, supplier_id: uuid.UUID
    ) -> float | None:
        """Average lead time in calendar days (order_date → received updated_at)."""
        result = await self._s.execute(
            text("""
                SELECT AVG(EXTRACT(EPOCH FROM (updated_at - order_date::timestamp)) / 86400)
                FROM purchase_orders
                WHERE tenant_id  = :tid
                  AND supplier_id = :sid
                  AND status      = 'received'
                  AND is_deleted  = false
            """),
            {"tid": str(tenant_id), "sid": str(supplier_id)},
        )
        row = result.fetchone()
        if not row or row[0] is None:
            return None
        return round(float(row[0]), 1)

    async def _price_history(
        self, tenant_id: uuid.UUID, supplier_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """Last 10 price entries from supplier_price_history."""
        result = await self._s.execute(
            text("""
                SELECT sph.material_id, m.code, m.name, sph.unit_price, sph.effective_from
                FROM supplier_price_history sph
                JOIN materials m ON m.id = sph.material_id
                WHERE sph.tenant_id   = :tid
                  AND sph.supplier_id = :sid
                ORDER BY sph.effective_from DESC
                LIMIT 10
            """),
            {"tid": str(tenant_id), "sid": str(supplier_id)},
        )
        rows = result.fetchall()
        return [
            {
                "material_id": str(r[0]),
                "material_code": r[1],
                "material_name": r[2],
                "unit_price": float(r[3]),
                "effective_from": r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]
