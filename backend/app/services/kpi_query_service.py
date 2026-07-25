"""KPI Query Service — SQL aggregate queries for dashboards and reports.

Provides aggregation queries for:
- Admin dashboard KPIs (pending SO, running WO, delayed WO, QC pending, low stock, dispatches, invoices, payments)
- Production summary with filters (date range, product, work center)
- Procurement summary (requisitions, pending POs, supplier deliveries, GRN pending, shortages)
- Manufacturing KPIs (OEE, yield, scrap rate, rework rate, inventory turnover)
- Reports: cycle time, QC pass/fail, OEE, inventory turnover

Requirements: 15.1–15.6, 22.1–22.4, 25.1, 30.1–30.5, 32.1–32.10
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select, text, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# --- Data Transfer Objects ---

@dataclass
class AdminKPIResponse:
    """Admin dashboard KPI response."""
    pending_sales_orders: int = 0
    running_work_orders: int = 0
    delayed_work_orders: int = 0
    qc_pending: int = 0
    low_stock_items: int = 0
    todays_dispatches: int = 0
    invoices_pending: int = 0
    payments_pending: int = 0


@dataclass
class DateRange:
    """Date range filter."""
    start_date: date
    end_date: date


@dataclass
class ProductionFilters:
    """Filters for production summary."""
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    product_id: Optional[uuid.UUID] = None
    work_center_id: Optional[uuid.UUID] = None


@dataclass
class ProductionSummary:
    """Production dashboard summary."""
    total_work_orders: int = 0
    running: int = 0
    completed_today: int = 0
    delayed: int = 0
    qc_queue: int = 0
    material_shortages: int = 0
    total_produced: float = 0.0
    total_planned: float = 0.0
    total_scrap: float = 0.0


@dataclass
class ProcurementSummary:
    """Procurement dashboard summary."""
    pending_requisitions: int = 0
    approved_requisitions: int = 0
    pending_purchase_orders: int = 0
    supplier_deliveries_next_7_days: int = 0
    overdue_deliveries: int = 0
    grn_pending: int = 0
    material_shortages: int = 0


@dataclass
class ManufacturingKPIs:
    """Manufacturing KPI metrics."""
    oee: float = 0.0  # Overall Equipment Effectiveness (%)
    yield_rate: float = 0.0  # (produced - scrap) / produced × 100
    scrap_rate: float = 0.0  # scrap / produced × 100
    rework_rate: float = 0.0  # rework_count / total_completed × 100
    inventory_turnover: float = 0.0  # COGS / Average Inventory
    total_produced: float = 0.0
    total_scrap: float = 0.0
    total_completed: int = 0
    total_rework: int = 0


@dataclass
class ReportFilters:
    """Generic report filters."""
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    product_id: Optional[uuid.UUID] = None


@dataclass
class OEEFilters:
    """OEE report filters."""
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    work_center_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None


@dataclass
class CycleTimeEntry:
    """A single product's cycle time data."""
    product_id: uuid.UUID
    product_name: str
    avg_cycle_time_hours: float
    min_cycle_time_hours: float
    max_cycle_time_hours: float
    sample_count: int


@dataclass
class CycleTimeReport:
    """Cycle time report response."""
    entries: List[CycleTimeEntry] = field(default_factory=list)


@dataclass
class QCEntry:
    """QC pass/fail entry per product."""
    product_id: uuid.UUID
    product_name: str
    total_inspections: int
    passed: int
    failed: int
    pass_rate: float


@dataclass
class QCReport:
    """QC pass/fail report response."""
    entries: List[QCEntry] = field(default_factory=list)
    overall_pass_rate: float = 0.0


@dataclass
class OEEEntry:
    """OEE entry per work center or product."""
    identifier: str
    availability: float
    performance: float
    quality: float
    oee: float


@dataclass
class OEEReport:
    """OEE report response."""
    entries: List[OEEEntry] = field(default_factory=list)
    overall_oee: float = 0.0


@dataclass
class TurnoverEntry:
    """Inventory turnover entry per material."""
    material_id: uuid.UUID
    material_name: str
    cogs: float
    average_inventory: float
    turnover_ratio: float


@dataclass
class TurnoverReport:
    """Inventory turnover report response."""
    entries: List[TurnoverEntry] = field(default_factory=list)
    overall_turnover: float = 0.0


# --- Service Implementation ---

class KPIQueryService:
    """Aggregation queries for dashboards and reports.

    All methods execute SQL aggregate queries — avoids materialized views,
    single-query responses keep it simple and the data volumes are manageable.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_admin_kpis(self, tenant_id: uuid.UUID) -> AdminKPIResponse:
        """Return admin dashboard KPI aggregates.

        Counts: pending SO, running WO, delayed WO, QC pending,
        low stock items, today's dispatches, invoices pending, payments pending.
        """
        today = date.today()

        # Pending sales orders (PENDING_APPROVAL status)
        pending_so = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM sales_orders
                WHERE tenant_id = :tid AND status = 'PENDING_APPROVAL'
                  AND is_deleted = false
            """),
            {"tid": tenant_id},
        )
        pending_so_count = pending_so.scalar() or 0

        # Running work orders (IN_PRODUCTION status)
        running_wo = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM work_orders
                WHERE tenant_id = :tid AND status = 'IN_PRODUCTION'
                  AND is_deleted = false
            """),
            {"tid": tenant_id},
        )
        running_wo_count = running_wo.scalar() or 0

        # Delayed work orders (past due_date and not completed/closed/cancelled)
        delayed_wo = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM work_orders
                WHERE tenant_id = :tid
                  AND due_date < :today
                  AND status NOT IN ('COMPLETED', 'CLOSED', 'CANCELLED', 'REJECTED')
                  AND is_deleted = false
            """),
            {"tid": tenant_id, "today": today},
        )
        delayed_wo_count = delayed_wo.scalar() or 0

        # QC pending work orders
        qc_pending = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM work_orders
                WHERE tenant_id = :tid AND status = 'QC_PENDING'
                  AND is_deleted = false
            """),
            {"tid": tenant_id},
        )
        qc_pending_count = qc_pending.scalar() or 0

        # Low stock items (current_stock <= reorder_level, reorder_level IS NOT NULL)
        low_stock = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM materials
                WHERE tenant_id = :tid
                  AND reorder_level IS NOT NULL
                  AND current_stock <= reorder_level
                  AND is_deleted = false
            """),
            {"tid": tenant_id},
        )
        low_stock_count = low_stock.scalar() or 0

        # Today's dispatches (deliveries shipped today)
        todays_dispatches = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM delivery_orders
                WHERE tenant_id = :tid
                  AND shipped_at::date = :today
                  AND is_deleted = false
            """),
            {"tid": tenant_id, "today": today},
        )
        todays_dispatches_count = todays_dispatches.scalar() or 0

        # Invoices pending (DRAFT status)
        invoices_pending = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM invoices
                WHERE tenant_id = :tid AND status = 'DRAFT'
                  AND is_deleted = false
            """),
            {"tid": tenant_id},
        )
        invoices_pending_count = invoices_pending.scalar() or 0

        # Payments pending (invoices with balance_due > 0, status not PAID)
        payments_pending = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM invoices
                WHERE tenant_id = :tid
                  AND grand_total > paid_amount
                  AND status NOT IN ('PAID', 'CANCELLED')
                  AND is_deleted = false
            """),
            {"tid": tenant_id},
        )
        payments_pending_count = payments_pending.scalar() or 0

        return AdminKPIResponse(
            pending_sales_orders=pending_so_count,
            running_work_orders=running_wo_count,
            delayed_work_orders=delayed_wo_count,
            qc_pending=qc_pending_count,
            low_stock_items=low_stock_count,
            todays_dispatches=todays_dispatches_count,
            invoices_pending=invoices_pending_count,
            payments_pending=payments_pending_count,
        )

    async def get_production_summary(
        self, tenant_id: uuid.UUID, filters: ProductionFilters
    ) -> ProductionSummary:
        """Return production dashboard metrics with optional filters.

        Filters: date range, product, work center.
        """
        today = date.today()
        params: Dict[str, Any] = {"tid": tenant_id, "today": today}

        # Build optional WHERE clauses
        date_filter = ""
        if filters.date_from:
            date_filter += " AND wo.start_date >= :date_from"
            params["date_from"] = filters.date_from
        if filters.date_to:
            date_filter += " AND wo.start_date <= :date_to"
            params["date_to"] = filters.date_to

        product_filter = ""
        if filters.product_id:
            product_filter = " AND wo.product_id = :product_id"
            params["product_id"] = filters.product_id

        # Work center filter (via job_cards -> operations -> work_center_id)
        wc_join = ""
        wc_filter = ""
        if filters.work_center_id:
            wc_join = """
                INNER JOIN job_cards jc ON jc.work_order_id = wo.id
                INNER JOIN operations op ON op.id = jc.operation_id
            """
            wc_filter = " AND op.work_center_id = :work_center_id"
            params["work_center_id"] = filters.work_center_id

        base_where = f"""
            WHERE wo.tenant_id = :tid AND wo.is_deleted = false
            {date_filter}{product_filter}{wc_filter}
        """

        # Total work orders count
        result = await self._session.execute(
            text(f"""
                SELECT COUNT(DISTINCT wo.id) FROM work_orders wo
                {wc_join}
                {base_where}
            """),
            params,
        )
        total_work_orders = result.scalar() or 0

        # Running (IN_PROGRESS)
        result = await self._session.execute(
            text(f"""
                SELECT COUNT(DISTINCT wo.id) FROM work_orders wo
                {wc_join}
                {base_where} AND wo.status = 'IN_PROGRESS'
            """),
            params,
        )
        running = result.scalar() or 0

        # Completed today
        result = await self._session.execute(
            text(f"""
                SELECT COUNT(DISTINCT wo.id) FROM work_orders wo
                {wc_join}
                {base_where}
                AND wo.status IN ('COMPLETED', 'CLOSED')
                AND wo.updated_at::date = :today
            """),
            params,
        )
        completed_today = result.scalar() or 0

        # Delayed (past due_date, not completed)
        result = await self._session.execute(
            text(f"""
                SELECT COUNT(DISTINCT wo.id) FROM work_orders wo
                {wc_join}
                {base_where}
                AND wo.due_date < :today
                AND wo.status NOT IN ('COMPLETED', 'CLOSED', 'CANCELLED', 'REJECTED')
            """),
            params,
        )
        delayed = result.scalar() or 0

        # QC queue
        result = await self._session.execute(
            text(f"""
                SELECT COUNT(DISTINCT wo.id) FROM work_orders wo
                {wc_join}
                {base_where} AND wo.status = 'QC_PENDING'
            """),
            params,
        )
        qc_queue = result.scalar() or 0

        # Material shortages (MATERIAL_PENDING)
        result = await self._session.execute(
            text(f"""
                SELECT COUNT(DISTINCT wo.id) FROM work_orders wo
                {wc_join}
                {base_where} AND wo.status = 'MATERIAL_PENDING'
            """),
            params,
        )
        material_shortages = result.scalar() or 0

        # Production quantities
        result = await self._session.execute(
            text(f"""
                SELECT
                    COALESCE(SUM(wo.produced_quantity), 0) as total_produced,
                    COALESCE(SUM(wo.planned_quantity), 0) as total_planned,
                    COALESCE(SUM(wo.scrap_quantity), 0) as total_scrap
                FROM work_orders wo
                {wc_join}
                {base_where}
            """),
            params,
        )
        row = result.mappings().first()
        total_produced = float(row["total_produced"]) if row else 0.0
        total_planned = float(row["total_planned"]) if row else 0.0
        total_scrap = float(row["total_scrap"]) if row else 0.0

        return ProductionSummary(
            total_work_orders=total_work_orders,
            running=running,
            completed_today=completed_today,
            delayed=delayed,
            qc_queue=qc_queue,
            material_shortages=material_shortages,
            total_produced=total_produced,
            total_planned=total_planned,
            total_scrap=total_scrap,
        )

    async def get_procurement_summary(self, tenant_id: uuid.UUID) -> ProcurementSummary:
        """Return procurement dashboard summary.

        Requisition counts, pending POs, supplier deliveries, GRN pending, shortages.
        """
        today = date.today()
        seven_days_later = date.fromordinal(today.toordinal() + 7)

        # Pending requisitions
        result = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM purchase_requisitions
                WHERE tenant_id = :tid AND status = 'PENDING_APPROVAL'
                  AND is_deleted = false
            """),
            {"tid": tenant_id},
        )
        pending_requisitions = result.scalar() or 0

        # Approved requisitions
        result = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM purchase_requisitions
                WHERE tenant_id = :tid AND status = 'APPROVED'
                  AND is_deleted = false
            """),
            {"tid": tenant_id},
        )
        approved_requisitions = result.scalar() or 0

        # Pending purchase orders (draft or pending approval)
        result = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM purchase_orders
                WHERE tenant_id = :tid
                  AND status IN ('draft', 'pending_approval')
                  AND is_deleted = false
            """),
            {"tid": tenant_id},
        )
        pending_pos = result.scalar() or 0

        # Supplier deliveries due in next 7 days
        result = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM purchase_orders
                WHERE tenant_id = :tid
                  AND expected_delivery IS NOT NULL
                  AND expected_delivery <= :seven_days
                  AND expected_delivery >= :today
                  AND status NOT IN ('received', 'cancelled')
                  AND is_deleted = false
            """),
            {"tid": tenant_id, "today": today, "seven_days": seven_days_later},
        )
        supplier_deliveries = result.scalar() or 0

        # Overdue deliveries
        result = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM purchase_orders
                WHERE tenant_id = :tid
                  AND expected_delivery IS NOT NULL
                  AND expected_delivery < :today
                  AND status NOT IN ('received', 'cancelled')
                  AND is_deleted = false
            """),
            {"tid": tenant_id, "today": today},
        )
        overdue_deliveries = result.scalar() or 0

        # GRN pending (POs received but with outstanding lines)
        result = await self._session.execute(
            text("""
                SELECT COUNT(DISTINCT po.id) FROM purchase_orders po
                INNER JOIN purchase_order_lines pol ON pol.purchase_order_id = po.id
                WHERE po.tenant_id = :tid
                  AND po.status IN ('confirmed', 'partial')
                  AND pol.received_quantity < pol.quantity
                  AND po.is_deleted = false
                  AND pol.is_deleted = false
            """),
            {"tid": tenant_id},
        )
        grn_pending = result.scalar() or 0

        # Material shortages (WOs in MATERIAL_PENDING)
        result = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM work_orders
                WHERE tenant_id = :tid AND status = 'MATERIAL_PENDING'
                  AND is_deleted = false
            """),
            {"tid": tenant_id},
        )
        material_shortages = result.scalar() or 0

        return ProcurementSummary(
            pending_requisitions=pending_requisitions,
            approved_requisitions=approved_requisitions,
            pending_purchase_orders=pending_pos,
            supplier_deliveries_next_7_days=supplier_deliveries,
            overdue_deliveries=overdue_deliveries,
            grn_pending=grn_pending,
            material_shortages=material_shortages,
        )

    async def get_manufacturing_kpis(
        self, tenant_id: uuid.UUID, date_range: DateRange
    ) -> ManufacturingKPIs:
        """Return manufacturing KPI metrics for the given date range.

        Formulas:
        - Yield = (produced - scrap) / produced × 100
        - Scrap Rate = scrap / produced × 100
        - Rework Rate = rework_count / total_completed × 100
        - OEE = Availability × Performance × Quality
        - Inventory Turnover = COGS / Average Inventory
        """
        params = {
            "tid": tenant_id,
            "date_from": date_range.start_date,
            "date_to": date_range.end_date,
        }

        # Aggregate production quantities in the date range
        result = await self._session.execute(
            text("""
                SELECT
                    COALESCE(SUM(produced_quantity), 0) as total_produced,
                    COALESCE(SUM(scrap_quantity), 0) as total_scrap,
                    COUNT(*) FILTER (WHERE status IN ('COMPLETED', 'CLOSED')) as total_completed,
                    COUNT(*) FILTER (WHERE status = 'REWORK') as total_rework
                FROM work_orders
                WHERE tenant_id = :tid
                  AND start_date >= :date_from
                  AND start_date <= :date_to
                  AND is_deleted = false
            """),
            params,
        )
        row = result.mappings().first()

        total_produced = float(row["total_produced"]) if row else 0.0
        total_scrap = float(row["total_scrap"]) if row else 0.0
        total_completed = int(row["total_completed"]) if row else 0
        total_rework = int(row["total_rework"]) if row else 0

        # Also count rework from audit log (WOs that transitioned to REWORK)
        rework_from_audit = await self._session.execute(
            text("""
                SELECT COUNT(*) FROM audit_logs
                WHERE tenant_id = :tid
                  AND action = 'qc_rework'
                  AND entity_type = 'work_order'
                  AND occurred_at >= :date_from
                  AND occurred_at <= :date_to
            """),
            params,
        )
        rework_count = rework_from_audit.scalar() or total_rework

        # Calculate KPIs
        yield_rate = 0.0
        scrap_rate = 0.0
        if total_produced > 0:
            yield_rate = ((total_produced - total_scrap) / total_produced) * 100
            scrap_rate = (total_scrap / total_produced) * 100

        rework_rate = 0.0
        if total_completed > 0:
            rework_rate = (rework_count / total_completed) * 100

        # OEE = Availability × Performance × Quality
        # Availability: actual run time / planned production time (from job cards)
        # Performance: actual output / theoretical max output
        # Quality: good units / total produced
        oee = await self._calculate_oee(tenant_id, date_range)

        # Inventory Turnover = COGS / Average Inventory
        inventory_turnover = await self._calculate_inventory_turnover(
            tenant_id, date_range
        )

        return ManufacturingKPIs(
            oee=oee,
            yield_rate=round(yield_rate, 2),
            scrap_rate=round(scrap_rate, 2),
            rework_rate=round(rework_rate, 2),
            inventory_turnover=round(inventory_turnover, 2),
            total_produced=total_produced,
            total_scrap=total_scrap,
            total_completed=total_completed,
            total_rework=rework_count,
        )

    async def get_cycle_time_report(
        self, tenant_id: uuid.UUID, filters: ReportFilters
    ) -> CycleTimeReport:
        """Return cycle time per product.

        Cycle time = time from IN_PRODUCTION start to COMPLETED,
        calculated from work order timestamps.
        """
        params: Dict[str, Any] = {"tid": tenant_id}
        date_filter = ""
        product_filter = ""

        if filters.date_from:
            date_filter += " AND wo.start_date >= :date_from"
            params["date_from"] = filters.date_from
        if filters.date_to:
            date_filter += " AND wo.start_date <= :date_to"
            params["date_to"] = filters.date_to
        if filters.product_id:
            product_filter = " AND wo.product_id = :product_id"
            params["product_id"] = filters.product_id

        result = await self._session.execute(
            text(f"""
                SELECT
                    wo.product_id,
                    iv.name as product_name,
                    AVG(EXTRACT(EPOCH FROM (wo.updated_at - wo.created_at)) / 3600)
                        as avg_cycle_hours,
                    MIN(EXTRACT(EPOCH FROM (wo.updated_at - wo.created_at)) / 3600)
                        as min_cycle_hours,
                    MAX(EXTRACT(EPOCH FROM (wo.updated_at - wo.created_at)) / 3600)
                        as max_cycle_hours,
                    COUNT(*) as sample_count
                FROM work_orders wo
                LEFT JOIN item_variants iv ON iv.id = wo.product_id
                WHERE wo.tenant_id = :tid
                  AND wo.status IN ('COMPLETED', 'CLOSED')
                  AND wo.is_deleted = false
                  {date_filter}{product_filter}
                GROUP BY wo.product_id, iv.name
                ORDER BY avg_cycle_hours DESC
            """),
            params,
        )

        entries = []
        for row in result.mappings():
            entries.append(CycleTimeEntry(
                product_id=row["product_id"],
                product_name=row["product_name"] or "Unknown",
                avg_cycle_time_hours=round(float(row["avg_cycle_hours"] or 0), 2),
                min_cycle_time_hours=round(float(row["min_cycle_hours"] or 0), 2),
                max_cycle_time_hours=round(float(row["max_cycle_hours"] or 0), 2),
                sample_count=int(row["sample_count"]),
            ))

        return CycleTimeReport(entries=entries)

    async def get_qc_pass_fail_report(
        self, tenant_id: uuid.UUID, filters: ReportFilters
    ) -> QCReport:
        """Return QC pass/fail rates grouped by product."""
        params: Dict[str, Any] = {"tid": tenant_id}
        date_filter = ""
        product_filter = ""

        if filters.date_from:
            date_filter += " AND qi.inspection_date >= :date_from"
            params["date_from"] = filters.date_from
        if filters.date_to:
            date_filter += " AND qi.inspection_date <= :date_to"
            params["date_to"] = filters.date_to
        if filters.product_id:
            product_filter = " AND wo.product_id = :product_id"
            params["product_id"] = filters.product_id

        result = await self._session.execute(
            text(f"""
                SELECT
                    wo.product_id,
                    iv.name as product_name,
                    COUNT(*) as total_inspections,
                    COUNT(*) FILTER (WHERE qi.result = 'PASS') as passed,
                    COUNT(*) FILTER (WHERE qi.result = 'FAIL') as failed
                FROM quality_inspections qi
                INNER JOIN work_orders wo
                    ON wo.id = qi.reference_id AND qi.reference_type = 'work_order'
                LEFT JOIN item_variants iv ON iv.id = wo.product_id
                WHERE qi.tenant_id = :tid
                  {date_filter}{product_filter}
                GROUP BY wo.product_id, iv.name
                ORDER BY total_inspections DESC
            """),
            params,
        )

        entries = []
        total_all = 0
        passed_all = 0
        for row in result.mappings():
            total = int(row["total_inspections"])
            passed = int(row["passed"])
            failed = int(row["failed"])
            pass_rate = (passed / total * 100) if total > 0 else 0.0
            total_all += total
            passed_all += passed
            entries.append(QCEntry(
                product_id=row["product_id"],
                product_name=row["product_name"] or "Unknown",
                total_inspections=total,
                passed=passed,
                failed=failed,
                pass_rate=round(pass_rate, 2),
            ))

        overall_pass_rate = (passed_all / total_all * 100) if total_all > 0 else 0.0

        return QCReport(entries=entries, overall_pass_rate=round(overall_pass_rate, 2))

    async def get_oee_report(
        self, tenant_id: uuid.UUID, filters: OEEFilters
    ) -> OEEReport:
        """Return OEE report per product or work center.

        OEE = Availability × Performance × Quality
        - Availability = (total_run_time - downtime) / total_run_time
        - Performance = actual_output / (run_time × ideal_cycle_rate)
        - Quality = good_units / total_produced
        """
        params: Dict[str, Any] = {"tid": tenant_id}
        date_filter = ""
        product_filter = ""
        wc_filter = ""

        if filters.date_from:
            date_filter += " AND wo.start_date >= :date_from"
            params["date_from"] = filters.date_from
        if filters.date_to:
            date_filter += " AND wo.start_date <= :date_to"
            params["date_to"] = filters.date_to
        if filters.product_id:
            product_filter = " AND wo.product_id = :product_id"
            params["product_id"] = filters.product_id
        if filters.work_center_id:
            wc_filter = " AND op.work_center_id = :work_center_id"
            params["work_center_id"] = filters.work_center_id

        # OEE per product using job card data
        result = await self._session.execute(
            text(f"""
                SELECT
                    wo.product_id,
                    iv.name as product_name,
                    COALESCE(SUM(
                        EXTRACT(EPOCH FROM (
                            COALESCE(jc.completed_at, NOW()) - jc.started_at
                        ))
                    ), 0) as total_run_seconds,
                    COALESCE(SUM(jc.total_downtime_seconds), 0) as total_downtime,
                    COALESCE(SUM(jc.produced_quantity), 0) as actual_output,
                    COALESCE(SUM(wo.planned_quantity), 0) as planned_output,
                    COALESCE(SUM(jc.produced_quantity - jc.scrap_quantity - jc.rejected_quantity), 0) as good_units,
                    COALESCE(SUM(jc.produced_quantity), 0) as total_produced_jc
                FROM job_cards jc
                INNER JOIN work_orders wo ON wo.id = jc.work_order_id
                INNER JOIN operations op ON op.id = jc.operation_id
                LEFT JOIN item_variants iv ON iv.id = wo.product_id
                WHERE wo.tenant_id = :tid
                  AND wo.is_deleted = false
                  AND jc.started_at IS NOT NULL
                  {date_filter}{product_filter}{wc_filter}
                GROUP BY wo.product_id, iv.name
            """),
            params,
        )

        entries = []
        total_oee_sum = 0.0
        count = 0

        for row in result.mappings():
            total_run = float(row["total_run_seconds"])
            downtime = float(row["total_downtime"])
            actual_output = float(row["actual_output"])
            planned_output = float(row["planned_output"])
            good_units = float(row["good_units"])
            total_produced_jc = float(row["total_produced_jc"])

            # Availability
            availability = 0.0
            if total_run > 0:
                availability = (total_run - downtime) / total_run

            # Performance (actual / planned as proxy)
            performance = 0.0
            if planned_output > 0:
                performance = min(actual_output / planned_output, 1.0)

            # Quality
            quality = 0.0
            if total_produced_jc > 0:
                quality = good_units / total_produced_jc

            oee_value = availability * performance * quality * 100

            entries.append(OEEEntry(
                identifier=row["product_name"] or str(row["product_id"]),
                availability=round(availability * 100, 2),
                performance=round(performance * 100, 2),
                quality=round(quality * 100, 2),
                oee=round(oee_value, 2),
            ))
            total_oee_sum += oee_value
            count += 1

        overall_oee = (total_oee_sum / count) if count > 0 else 0.0
        return OEEReport(entries=entries, overall_oee=round(overall_oee, 2))

    async def get_inventory_turnover(
        self, tenant_id: uuid.UUID, filters: ReportFilters
    ) -> TurnoverReport:
        """Return inventory turnover report.

        Inventory Turnover = COGS / Average Inventory
        COGS proxy: sum of material consumption (outbound transactions) × cost
        Average Inventory: (opening + closing) / 2 or average current_stock × cost
        """
        params: Dict[str, Any] = {"tid": tenant_id}
        date_filter = ""

        if filters.date_from:
            date_filter += " AND it.created_at >= :date_from"
            params["date_from"] = filters.date_from
        if filters.date_to:
            date_filter += " AND it.created_at <= :date_to"
            params["date_to"] = filters.date_to

        product_filter = ""
        if filters.product_id:
            product_filter = " AND it.material_id = :product_id"
            params["product_id"] = filters.product_id

        # COGS = sum of outbound quantities × material cost
        result = await self._session.execute(
            text(f"""
                SELECT
                    m.id as material_id,
                    m.name as material_name,
                    COALESCE(SUM(ABS(it.quantity) * m.current_cost), 0) as cogs,
                    m.current_stock * m.current_cost as current_inventory_value
                FROM inventory_transactions it
                INNER JOIN materials m ON m.id = it.material_id
                WHERE it.tenant_id = :tid
                  AND it.quantity < 0
                  AND it.is_deleted = false
                  AND m.is_deleted = false
                  {date_filter}{product_filter}
                GROUP BY m.id, m.name, m.current_stock, m.current_cost
                HAVING SUM(ABS(it.quantity) * m.current_cost) > 0
                ORDER BY cogs DESC
            """),
            params,
        )

        entries = []
        total_cogs = 0.0
        total_avg_inv = 0.0

        for row in result.mappings():
            cogs = float(row["cogs"])
            inv_value = float(row["current_inventory_value"] or 0)
            # Use current inventory as proxy for average (simplified)
            avg_inventory = max(inv_value, 0.01)  # Avoid division by zero
            turnover_ratio = cogs / avg_inventory if avg_inventory > 0 else 0.0

            entries.append(TurnoverEntry(
                material_id=row["material_id"],
                material_name=row["material_name"],
                cogs=round(cogs, 2),
                average_inventory=round(inv_value, 2),
                turnover_ratio=round(turnover_ratio, 2),
            ))
            total_cogs += cogs
            total_avg_inv += inv_value

        overall_turnover = (
            total_cogs / total_avg_inv if total_avg_inv > 0 else 0.0
        )

        return TurnoverReport(
            entries=entries,
            overall_turnover=round(overall_turnover, 2),
        )

    # --- Private helper methods ---

    async def _calculate_oee(
        self, tenant_id: uuid.UUID, date_range: DateRange
    ) -> float:
        """Calculate overall OEE for the date range.

        OEE = Availability × Performance × Quality
        """
        params = {
            "tid": tenant_id,
            "date_from": date_range.start_date,
            "date_to": date_range.end_date,
        }

        result = await self._session.execute(
            text("""
                SELECT
                    COALESCE(SUM(
                        EXTRACT(EPOCH FROM (
                            COALESCE(jc.completed_at, NOW()) - jc.started_at
                        ))
                    ), 0) as total_run_seconds,
                    COALESCE(SUM(jc.total_downtime_seconds), 0) as total_downtime,
                    COALESCE(SUM(jc.produced_quantity), 0) as actual_output,
                    COALESCE(SUM(wo.planned_quantity), 0) as planned_output,
                    COALESCE(SUM(jc.produced_quantity - jc.scrap_quantity - jc.rejected_quantity), 0) as good_units,
                    COALESCE(SUM(jc.produced_quantity), 0) as total_produced
                FROM job_cards jc
                INNER JOIN work_orders wo ON wo.id = jc.work_order_id
                WHERE wo.tenant_id = :tid
                  AND wo.start_date >= :date_from
                  AND wo.start_date <= :date_to
                  AND wo.is_deleted = false
                  AND jc.started_at IS NOT NULL
            """),
            params,
        )
        row = result.mappings().first()
        if not row:
            return 0.0

        total_run = float(row["total_run_seconds"])
        downtime = float(row["total_downtime"])
        actual_output = float(row["actual_output"])
        planned_output = float(row["planned_output"])
        good_units = float(row["good_units"])
        total_produced = float(row["total_produced"])

        # Availability = (run_time - downtime) / run_time
        availability = 0.0
        if total_run > 0:
            availability = (total_run - downtime) / total_run

        # Performance = actual / planned (capped at 1.0)
        performance = 0.0
        if planned_output > 0:
            performance = min(actual_output / planned_output, 1.0)

        # Quality = good / total
        quality = 0.0
        if total_produced > 0:
            quality = good_units / total_produced

        oee = availability * performance * quality * 100
        return round(oee, 2)

    async def _calculate_inventory_turnover(
        self, tenant_id: uuid.UUID, date_range: DateRange
    ) -> float:
        """Calculate overall inventory turnover ratio.

        Inventory Turnover = COGS / Average Inventory
        """
        params = {
            "tid": tenant_id,
            "date_from": date_range.start_date,
            "date_to": date_range.end_date,
        }

        # COGS = total value of outbound material transactions in period
        result = await self._session.execute(
            text("""
                SELECT
                    COALESCE(SUM(ABS(it.quantity) * m.current_cost), 0) as total_cogs
                FROM inventory_transactions it
                INNER JOIN materials m ON m.id = it.material_id
                WHERE it.tenant_id = :tid
                  AND it.quantity < 0
                  AND it.created_at >= :date_from
                  AND it.created_at <= :date_to
                  AND it.is_deleted = false
                  AND m.is_deleted = false
            """),
            params,
        )
        total_cogs = float(result.scalar() or 0)

        # Average inventory = sum of current_stock × current_cost for all materials
        result = await self._session.execute(
            text("""
                SELECT COALESCE(SUM(current_stock * current_cost), 0) as total_inv
                FROM materials
                WHERE tenant_id = :tid AND is_deleted = false
            """),
            {"tid": tenant_id},
        )
        total_inventory = float(result.scalar() or 0)

        if total_inventory <= 0:
            return 0.0
        return total_cogs / total_inventory
