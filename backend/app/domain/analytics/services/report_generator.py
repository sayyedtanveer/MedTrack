"""Analytics service for generating reports and calculating metrics."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
from decimal import Decimal
from enum import Enum


class MetricType(str, Enum):
    """Supported metric types."""
    REVENUE = "revenue"
    ORDERS = "orders"
    PRODUCTION_QTY = "production_qty"
    SCRAP_QTY = "scrap_qty"
    INVENTORY_VALUE = "inventory_value"
    AVERAGE_COST = "average_cost"


class ReportGenerator:
    """Service for generating reports from domain data."""

    def __init__(self, repository):
        """Initialize with repository for data access."""
        self.repository = repository

    async def generate_sales_report(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
        grouping: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate sales report with revenue, orders, and trends."""
        filters = filters or {}
        
        # Get sales data
        sales_data = await self.repository.get_sales_data(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            filters=filters,
        )

        # Aggregate by grouping (client, product, date, etc.)
        aggregated = self._aggregate_data(sales_data, grouping or {"by": "date"})

        return {
            "report_type": "sales",
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "data": aggregated,
            "summary": {
                "total_revenue": sum(d.get("revenue", 0) for d in aggregated),
                "total_orders": sum(d.get("order_count", 0) for d in aggregated),
                "average_order_value": self._safe_divide(
                    sum(d.get("revenue", 0) for d in aggregated),
                    sum(d.get("order_count", 0) for d in aggregated),
                ),
            },
        }

    async def generate_production_report(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
        grouping: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate production report with WO status and metrics."""
        filters = filters or {}
        
        work_orders = await self.repository.get_work_orders(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            filters=filters,
        )

        total_planned = sum(wo.get("planned_qty", 0) for wo in work_orders)
        total_produced = sum(wo.get("produced_qty", 0) for wo in work_orders)
        total_scrap = sum(wo.get("scrap_qty", 0) for wo in work_orders)

        aggregated = self._aggregate_data(work_orders, grouping or {"by": "status"})

        return {
            "report_type": "production",
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "data": aggregated,
            "summary": {
                "total_planned": total_planned,
                "total_produced": total_produced,
                "total_scrap": total_scrap,
                "completion_rate": self._safe_divide(total_produced, total_planned),
                "scrap_rate": self._safe_divide(total_scrap, total_planned),
                "efficiency": self._safe_divide(
                    total_produced, total_planned + total_scrap
                ),
            },
        }

    async def generate_inventory_report(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
        grouping: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate inventory report with stock levels and movements."""
        filters = filters or {}
        
        inventory_data = await self.repository.get_inventory_data(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            filters=filters,
        )

        aggregated = self._aggregate_data(inventory_data, grouping or {"by": "category"})

        return {
            "report_type": "inventory",
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "data": aggregated,
            "summary": {
                "total_items": len(aggregated),
                "total_value": sum(d.get("value", 0) for d in aggregated),
                "average_stock_level": self._safe_divide(
                    sum(d.get("quantity", 0) for d in aggregated),
                    len(aggregated),
                ),
                "fast_moving": len([d for d in aggregated if d.get("turnover", 0) > 10]),
                "slow_moving": len([d for d in aggregated if d.get("turnover", 0) < 2]),
                "stockouts": len([d for d in aggregated if d.get("quantity", 0) == 0]),
            },
        }

    async def generate_finance_report(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
        grouping: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate finance report with AR/AP and cash flow."""
        filters = filters or {}
        
        finance_data = await self.repository.get_finance_data(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            filters=filters,
        )

        aggregated = self._aggregate_data(finance_data, grouping or {"by": "status"})

        ar_total = sum(d.get("ar_amount", 0) for d in aggregated if d.get("type") == "ar")
        ap_total = sum(d.get("ap_amount", 0) for d in aggregated if d.get("type") == "ap")
        collected = sum(d.get("collected", 0) for d in aggregated if d.get("type") == "ar")
        paid = sum(d.get("paid", 0) for d in aggregated if d.get("type") == "ap")

        return {
            "report_type": "finance",
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "data": aggregated,
            "summary": {
                "ar_total": ar_total,
                "ap_total": ap_total,
                "ar_collected": collected,
                "ap_paid": paid,
                "ar_outstanding": ar_total - collected,
                "ap_outstanding": ap_total - paid,
                "dso": self._calculate_dso(aggregated),
                "dpo": self._calculate_dpo(aggregated),
                "cash_conversion_cycle": self._calculate_ccc(aggregated),
            },
        }

    def _aggregate_data(
        self, data: List[Dict[str, Any]], grouping: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Aggregate data by grouping criteria."""
        if not data:
            return []

        group_by = grouping.get("by", "date")
        aggregated = {}

        for item in data:
            key = item.get(group_by, "unknown")
            if key not in aggregated:
                aggregated[key] = {
                    "group": key,
                    "count": 0,
                    "entries": [],
                }
            aggregated[key]["count"] += 1
            aggregated[key]["entries"].append(item)

        return list(aggregated.values())

    @staticmethod
    def _safe_divide(numerator: float, denominator: float) -> float:
        """Safe division with zero handling."""
        if denominator == 0:
            return 0.0
        return round(float(numerator) / float(denominator), 4)

    @staticmethod
    def _calculate_dso(data: List[Dict[str, Any]]) -> float:
        """Calculate Days Sales Outstanding (DSO)."""
        # DSO = (AR / Total Revenue) * Number of Days
        return 30.0  # Placeholder

    @staticmethod
    def _calculate_dpo(data: List[Dict[str, Any]]) -> float:
        """Calculate Days Payable Outstanding (DPO)."""
        # DPO = (AP / COGS) * Number of Days
        return 35.0  # Placeholder

    @staticmethod
    def _calculate_ccc(data: List[Dict[str, Any]]) -> float:
        """Calculate Cash Conversion Cycle (CCC)."""
        # CCC = DIO + DSO - DPO
        return 60.0  # Placeholder


class MetricsCalculator:
    """Service for calculating dashboard metrics."""

    def __init__(self, repository):
        """Initialize with repository."""
        self.repository = repository

    async def calculate_metric(
        self,
        tenant_id: UUID,
        metric_key: str,
        start_date: datetime,
        end_date: datetime,
    ) -> float:
        """Calculate a specific metric."""
        if metric_key.startswith("sales_"):
            return await self._calculate_sales_metric(
                tenant_id, metric_key, start_date, end_date
            )
        elif metric_key.startswith("production_"):
            return await self._calculate_production_metric(
                tenant_id, metric_key, start_date, end_date
            )
        elif metric_key.startswith("inventory_"):
            return await self._calculate_inventory_metric(
                tenant_id, metric_key, start_date, end_date
            )
        elif metric_key.startswith("finance_"):
            return await self._calculate_finance_metric(
                tenant_id, metric_key, start_date, end_date
            )
        else:
            raise ValueError(f"Unknown metric: {metric_key}")

    async def _calculate_sales_metric(
        self, tenant_id: UUID, metric_key: str, start_date: datetime, end_date: datetime
    ) -> float:
        """Calculate sales metrics."""
        data = await self.repository.get_sales_data(tenant_id, start_date, end_date)
        
        if metric_key == "sales_revenue_total":
            return sum(d.get("revenue", 0) for d in data)
        elif metric_key == "sales_orders_count":
            return len(data)
        elif metric_key == "sales_average_order_value":
            return sum(d.get("revenue", 0) for d in data) / len(data) if data else 0
        else:
            raise ValueError(f"Unknown sales metric: {metric_key}")

    async def _calculate_production_metric(
        self, tenant_id: UUID, metric_key: str, start_date: datetime, end_date: datetime
    ) -> float:
        """Calculate production metrics."""
        data = await self.repository.get_work_orders(tenant_id, start_date, end_date)
        
        if metric_key == "production_total_qty":
            return sum(d.get("produced_qty", 0) for d in data)
        elif metric_key == "production_scrap_rate":
            total_qty = sum(d.get("produced_qty", 0) for d in data)
            total_scrap = sum(d.get("scrap_qty", 0) for d in data)
            return total_scrap / total_qty if total_qty > 0 else 0
        elif metric_key == "production_completion_rate":
            total_planned = sum(d.get("planned_qty", 0) for d in data)
            total_produced = sum(d.get("produced_qty", 0) for d in data)
            return total_produced / total_planned if total_planned > 0 else 0
        else:
            raise ValueError(f"Unknown production metric: {metric_key}")

    async def _calculate_inventory_metric(
        self, tenant_id: UUID, metric_key: str, start_date: datetime, end_date: datetime
    ) -> float:
        """Calculate inventory metrics."""
        data = await self.repository.get_inventory_data(tenant_id, start_date, end_date)
        
        if metric_key == "inventory_value_total":
            return sum(d.get("value", 0) for d in data)
        elif metric_key == "inventory_item_count":
            return len([d for d in data if d.get("quantity", 0) > 0])
        elif metric_key == "inventory_stockouts":
            return len([d for d in data if d.get("quantity", 0) == 0])
        else:
            raise ValueError(f"Unknown inventory metric: {metric_key}")

    async def _calculate_finance_metric(
        self, tenant_id: UUID, metric_key: str, start_date: datetime, end_date: datetime
    ) -> float:
        """Calculate finance metrics."""
        data = await self.repository.get_finance_data(tenant_id, start_date, end_date)
        
        if metric_key == "finance_ar_total":
            return sum(d.get("ar_amount", 0) for d in data if d.get("type") == "ar")
        elif metric_key == "finance_ap_total":
            return sum(d.get("ap_amount", 0) for d in data if d.get("type") == "ap")
        elif metric_key == "finance_cash_position":
            ar = sum(d.get("ar_amount", 0) for d in data if d.get("type") == "ar")
            ap = sum(d.get("ap_amount", 0) for d in data if d.get("type") == "ap")
            return ar - ap
        else:
            raise ValueError(f"Unknown finance metric: {metric_key}")
