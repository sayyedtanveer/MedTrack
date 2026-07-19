"""Accountant Service - operational flow for accountant dashboard."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.invoice_model import InvoiceModel
from backend.app.infrastructure.persistence.models.delivery_model import DeliveryOrderModel


class AccountantService:
    """Service for accountant operational dashboard and actions.

    Responsibilities:
    - Get pending invoices
    - Get overdue invoices
    - Get paid invoices
    - View revenue metrics
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_pending_invoices(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get pending invoices for accountant dashboard."""
        stmt = (
            select(InvoiceModel)
            .where(
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.status == "PENDING",
                InvoiceModel.is_deleted.is_(False),
            )
            .order_by(InvoiceModel.due_date)
        )
        result = await self._session.execute(stmt)
        invoices = result.scalars().all()

        pending_invoices = []
        for inv in invoices:
            pending_invoices.append({
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "customer_id": inv.customer_id,
                "amount": inv.total_amount,
                "due_date": inv.due_date,
                "status": inv.status,
            })

        return pending_invoices

    async def get_overdue_invoices(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get overdue invoices for accountant dashboard."""
        from datetime import datetime, timezone

        stmt = (
            select(InvoiceModel)
            .where(
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.due_date < datetime.now(timezone.utc),
                InvoiceModel.status.in_(["PENDING", "PARTIALLY_PAID"]),
                InvoiceModel.is_deleted.is_(False),
            )
            .order_by(InvoiceModel.due_date)
        )
        result = await self._session.execute(stmt)
        invoices = result.scalars().all()

        overdue_invoices = []
        for inv in invoices:
            overdue_invoices.append({
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "customer_id": inv.customer_id,
                "amount": inv.total_amount,
                "due_date": inv.due_date,
                "status": inv.status,
            })

        return overdue_invoices

    async def get_paid_invoices(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get paid invoices for accountant dashboard."""
        stmt = (
            select(InvoiceModel)
            .where(
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.status == "PAID",
                InvoiceModel.is_deleted.is_(False),
            )
            .order_by(InvoiceModel.paid_at.desc())
        )
        result = await self._session.execute(stmt)
        invoices = result.scalars().all()

        paid_invoices = []
        for inv in invoices:
            paid_invoices.append({
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "customer_id": inv.customer_id,
                "amount": inv.total_amount,
                "paid_date": inv.paid_at,
                "status": inv.status,
            })

        return paid_invoices

    async def get_revenue_metrics(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Get revenue metrics for accountant dashboard."""
        from datetime import datetime, timezone, timedelta

        # Get invoices paid in the last 30 days
        future_date = datetime.now(timezone.utc)
        past_date = future_date - timedelta(days=30)
        
        stmt = (
            select(InvoiceModel)
            .where(
                InvoiceModel.tenant_id == tenant_id,
                InvoiceModel.status == "PAID",
                InvoiceModel.is_deleted.is_(False),
                InvoiceModel.paid_at >= past_date,
            )
        )
        result = await self._session.execute(stmt)
        invoices = result.scalars().all()

        total_revenue = sum(inv.total_amount for inv in invoices)
        
        return {
            "paid_invoice_count": len(invoices),
            "total_revenue": total_revenue,
            "average_invoice_value": total_revenue / len(invoices) if invoices else 0,
        }
