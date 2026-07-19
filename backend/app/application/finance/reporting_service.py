"""Reporting service for cross-module analytics and financial statements."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.finance.finance_service import FinanceService


ROLE_REPORT_ACCESS = {
    "ADMIN": ["inventory", "production", "sales", "procurement", "quality", "finance", "mrp"],
    "MANAGER": ["inventory", "production", "sales", "procurement", "quality", "finance", "mrp"],
    "ACCOUNTANT": ["finance", "sales"],
    "SALES": ["sales"],
    "QC": ["quality"],
    "OPERATOR": ["production", "inventory"],
    "VIEWER": ["sales", "inventory"],
    "CLIENT": [],
    "SUPPLIER": [],
}


class ReportingService:
    """Role-aware reporting facade. Financial reports delegate to FinanceService."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.finance = FinanceService(session)

    def _check_access(self, role: str, report_type: str) -> None:
        allowed = ROLE_REPORT_ACCESS.get(role, [])
        if report_type not in allowed:
            raise PermissionError(f"Role '{role}' cannot access '{report_type}' reports")

    async def inventory_summary(self, tenant_id: uuid.UUID, role: str) -> List[Dict]:
        self._check_access(role, "inventory")
        result = await self.session.execute(
            text(
                """
                SELECT
                    m.id,
                    m.name,
                    m.code,
                    mc.name as category,
                    sl.quantity_on_hand,
                    sl.quantity_reserved,
                    sl.quantity_on_hand - sl.quantity_reserved as available,
                    m.reorder_level,
                    CASE WHEN sl.quantity_on_hand <= m.reorder_level THEN true ELSE false END as is_low_stock
                FROM materials m
                LEFT JOIN stock_levels sl ON sl.material_id = m.id AND sl.tenant_id = m.tenant_id
                LEFT JOIN material_categories mc ON mc.id = m.category_id
                WHERE m.tenant_id = :tenant_id AND m.is_deleted = false
                ORDER BY m.name
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [dict(row._mapping) for row in result]

    async def inventory_turnover(self, tenant_id: uuid.UUID, role: str) -> List[Dict]:
        self._check_access(role, "inventory")
        try:
            result = await self.session.execute(
                text(
                    """
                    SELECT
                        mvit.material_id,
                        m.name,
                        m.code,
                        mvit.total_consumed,
                        mvit.months_count,
                        CASE WHEN mvit.months_count > 0
                            THEN ROUND(mvit.total_consumed::numeric / mvit.months_count, 2)
                            ELSE 0
                        END as avg_monthly_consumption
                    FROM mv_inventory_turnover mvit
                    LEFT JOIN materials m ON m.id = mvit.material_id
                    WHERE mvit.tenant_id = :tenant_id
                    ORDER BY mvit.total_consumed DESC
                    """
                ),
                {"tenant_id": tenant_id},
            )
            return [dict(row._mapping) for row in result]
        except Exception:
            return []

    async def work_order_summary(self, tenant_id: uuid.UUID, role: str) -> Dict:
        self._check_access(role, "production")
        result = await self.session.execute(
            text(
                """
                SELECT
                    status,
                    COUNT(*) as count,
                    SUM(produced_quantity) as total_produced,
                    SUM(scrap_quantity) as total_scrap
                FROM work_orders
                WHERE tenant_id = :tenant_id
                GROUP BY status
                ORDER BY status
                """
            ),
            {"tenant_id": tenant_id},
        )
        return {"by_status": [dict(row._mapping) for row in result]}

    async def work_order_efficiency(self, tenant_id: uuid.UUID, role: str) -> List[Dict]:
        self._check_access(role, "production")
        try:
            result = await self.session.execute(
                text(
                    """
                    SELECT month, total_produced, total_scrap, scrap_percentage
                    FROM mv_work_order_efficiency
                    WHERE tenant_id = :tenant_id
                    ORDER BY month DESC
                    LIMIT 12
                    """
                ),
                {"tenant_id": tenant_id},
            )
            return [dict(row._mapping) for row in result]
        except Exception:
            return []

    async def sales_summary(self, tenant_id: uuid.UUID, role: str) -> Dict:
        self._check_access(role, "sales")
        result = await self.session.execute(
            text(
                """
                SELECT
                    status,
                    COUNT(*) as count,
                    SUM(grand_total) as total_value
                FROM sales_orders
                WHERE tenant_id = :tenant_id AND is_deleted = false
                GROUP BY status
                ORDER BY status
                """
            ),
            {"tenant_id": tenant_id},
        )
        monthly_result = await self.session.execute(
            text(
                """
                SELECT
                    date_trunc('month', created_at)::date as month,
                    COUNT(*) as orders,
                    SUM(grand_total) as revenue
                FROM sales_orders
                WHERE tenant_id = :tenant_id AND is_deleted = false
                    AND created_at >= NOW() - INTERVAL '6 months'
                GROUP BY date_trunc('month', created_at)
                ORDER BY month
                """
            ),
            {"tenant_id": tenant_id},
        )
        return {
            "by_status": [dict(row._mapping) for row in result],
            "monthly": [dict(row._mapping) for row in monthly_result],
        }

    async def top_clients(self, tenant_id: uuid.UUID, role: str, limit: int = 10) -> List[Dict]:
        self._check_access(role, "sales")
        result = await self.session.execute(
            text(
                """
                SELECT
                    sc.id,
                    sc.name,
                    sc.code,
                    COUNT(so.id) as order_count,
                    SUM(so.grand_total) as total_revenue
                FROM sales_clients sc
                LEFT JOIN sales_orders so ON so.client_id = sc.id AND so.is_deleted = false
                WHERE sc.tenant_id = :tenant_id AND sc.is_deleted = false
                GROUP BY sc.id, sc.name, sc.code
                ORDER BY total_revenue DESC NULLS LAST
                LIMIT :limit
                """
            ),
            {"tenant_id": tenant_id, "limit": limit},
        )
        return [dict(row._mapping) for row in result]

    async def procurement_summary(self, tenant_id: uuid.UUID, role: str) -> Dict:
        self._check_access(role, "procurement")
        result = await self.session.execute(
            text(
                """
                SELECT
                    status,
                    COUNT(*) as count,
                    SUM(total_amount) as total_value
                FROM purchase_orders
                WHERE tenant_id = :tenant_id AND is_deleted = false
                GROUP BY status
                ORDER BY status
                """
            ),
            {"tenant_id": tenant_id},
        )
        return {"by_status": [dict(row._mapping) for row in result]}

    async def quality_summary(self, tenant_id: uuid.UUID, role: str) -> Dict:
        self._check_access(role, "quality")
        result = await self.session.execute(
            text(
                """
                SELECT
                    result,
                    COUNT(*) as count
                FROM quality_inspections
                WHERE tenant_id = :tenant_id
                GROUP BY result
                ORDER BY result
                """
            ),
            {"tenant_id": tenant_id},
        )
        return {"by_result": [dict(row._mapping) for row in result]}

    async def finance_summary(self, tenant_id: uuid.UUID, role: str) -> Dict:
        self._check_access(role, "finance")
        ar = await self.finance.get_ar_summary(tenant_id)
        ap = await self.finance.get_ap_summary(tenant_id)
        pnl = await self.finance.get_profit_and_loss(tenant_id)
        cash_flow = await self.finance.get_cash_flow_statement(tenant_id, months=6)
        return {
            "ar": ar,
            "ap": ap,
            "profit_and_loss": pnl["totals"],
            "cash_flow": cash_flow["totals"],
        }

    async def ar_aging(self, tenant_id: uuid.UUID, role: str) -> List[Dict]:
        self._check_access(role, "finance")
        return await self.finance.get_ar_aging(tenant_id)

    async def ap_aging(self, tenant_id: uuid.UUID, role: str) -> List[Dict]:
        self._check_access(role, "finance")
        return await self.finance.get_ap_aging(tenant_id)

    async def trial_balance(self, tenant_id: uuid.UUID, role: str, as_of: Optional[date] = None) -> Dict:
        self._check_access(role, "finance")
        return await self.finance.get_trial_balance(tenant_id, as_of=as_of)

    async def profit_and_loss(
        self,
        tenant_id: uuid.UUID,
        role: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Dict:
        self._check_access(role, "finance")
        return await self.finance.get_profit_and_loss(tenant_id, from_date=from_date, to_date=to_date)

    async def balance_sheet(self, tenant_id: uuid.UUID, role: str, as_of: Optional[date] = None) -> Dict:
        self._check_access(role, "finance")
        return await self.finance.get_balance_sheet(tenant_id, as_of=as_of)

    async def cash_flow(self, tenant_id: uuid.UUID, role: str, months: int = 6) -> Dict:
        self._check_access(role, "finance")
        return await self.finance.get_cash_flow_statement(tenant_id, months=months)

    async def refresh_views(self, view_name: Optional[str] = None) -> List[str]:
        views = [
            "mv_inventory_turnover",
            "mv_work_order_efficiency",
            "mv_sales_revenue",
            "mv_ar_aging",
        ]
        if view_name:
            views = [v for v in views if v == view_name]

        refreshed = []
        for view in views:
            try:
                await self.session.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"))
                refreshed.append(view)
            except Exception:
                try:
                    await self.session.execute(text(f"REFRESH MATERIALIZED VIEW {view}"))
                    refreshed.append(view)
                except Exception:
                    pass
        await self.session.commit()
        return refreshed
