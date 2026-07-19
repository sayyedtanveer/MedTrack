"""Sales order application commands (CQRS pattern)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class CreateSalesOrderCommand:
    """Create a new sales order."""
    
    tenant_id: UUID
    client_id: UUID
    order_date: date
    delivery_date: date
    created_by: str
    notes: str | None = None
    approver_id: UUID | None = None


@dataclass(frozen=True)
class AddLineToSalesOrderCommand:
    """Add a line item to a sales order."""
    
    tenant_id: UUID
    sales_order_id: UUID
    product_id: UUID
    product_type: str  # "variant" or "finished_product"
    uom_id: UUID
    quantity: Decimal
    tax_rate: Decimal = Decimal("0")


@dataclass(frozen=True)
class RemoveLineFromSalesOrderCommand:
    """Remove a line item from a sales order."""
    
    tenant_id: UUID
    sales_order_id: UUID
    line_id: UUID


@dataclass(frozen=True)
class ApplyDiscountToOrderCommand:
    """Apply discount to a sales order."""
    
    tenant_id: UUID
    sales_order_id: UUID
    discount_amount: Decimal


@dataclass(frozen=True)
class SubmitSalesOrderForApprovalCommand:
    """Submit a draft sales order for manager approval."""

    tenant_id: UUID
    sales_order_id: UUID
    submitted_by: str
    approver_id: UUID | None = None
    notes: str | None = None


@dataclass(frozen=True)
class ApproveSalesOrderCommand:
    """Approve a sales order before execution."""

    tenant_id: UUID
    sales_order_id: UUID
    approver_id: UUID
    notes: str | None = None


@dataclass(frozen=True)
class RejectSalesOrderCommand:
    """Reject a submitted sales order."""

    tenant_id: UUID
    sales_order_id: UUID
    approver_id: UUID
    notes: str | None = None


@dataclass(frozen=True)
class ConfirmSalesOrderCommand:
    """Confirm a sales order (transition from DRAFT to CONFIRMED)."""
    
    tenant_id: UUID
    sales_order_id: UUID
    confirmed_by: str


@dataclass(frozen=True)
class CancelSalesOrderCommand:
    """Cancel a sales order."""
    
    tenant_id: UUID
    sales_order_id: UUID
    reason: str | None = None
    cancelled_by: str | None = None


@dataclass(frozen=True)
class TransitionOrderToProductionCommand:
    """Transition order to PRODUCTION status."""
    
    tenant_id: UUID
    sales_order_id: UUID
    transitioned_by: str


@dataclass(frozen=True)
class TransitionOrderToReadyCommand:
    """Transition order to READY status."""
    
    tenant_id: UUID
    sales_order_id: UUID
    transitioned_by: str


@dataclass(frozen=True)
class ShipOrderCommand:
    """Ship a sales order (record shipment details)."""
    
    tenant_id: UUID
    sales_order_id: UUID
    line_shipments: dict[UUID, Decimal]  # {line_id: qty_shipped}
    shipped_by: str


@dataclass(frozen=True)
class DeliverOrderCommand:
    """Deliver a sales order."""
    
    tenant_id: UUID
    sales_order_id: UUID
    delivered_by: str


@dataclass(frozen=True)
class RecordPaymentCommand:
    """Record payment for a sales order."""
    
    tenant_id: UUID
    sales_order_id: UUID
    amount_paid: Decimal
    payment_date: date
    payment_method: str
    reference: str | None = None


@dataclass(frozen=True)
class CreateClientCommand:
    """Create a new client."""
    
    tenant_id: UUID
    code: str
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    gst_number: str | None = None
    credit_limit: Decimal | None = None
    payment_terms_days: int = 0


@dataclass(frozen=True)
class UpdateClientCommand:
    """Update client information."""
    
    tenant_id: UUID
    client_id: UUID
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    gst_number: str | None = None
    credit_limit: Decimal | None = None
    payment_terms_days: int | None = None


@dataclass(frozen=True)
class DeactivateClientCommand:
    """Deactivate a client."""
    
    tenant_id: UUID
    client_id: UUID
    reason: str | None = None


@dataclass(frozen=True)
class CreatePriceListCommand:
    """Create a new price list."""
    
    tenant_id: UUID
    name: str
    is_default: bool = False
    valid_from: date | None = None
    valid_to: date | None = None


@dataclass(frozen=True)
class AddPriceListLineCommand:
    """Add a pricing line to a price list."""
    
    tenant_id: UUID
    price_list_id: UUID
    product_id: UUID
    product_type: str
    unit_price: Decimal


@dataclass(frozen=True)
class UpdatePriceListLineCommand:
    """Update a pricing line in a price list."""
    
    tenant_id: UUID
    price_list_id: UUID
    product_id: UUID
    product_type: str
    new_price: Decimal


@dataclass(frozen=True)
class RemovePriceListLineCommand:
    """Remove a pricing line from a price list."""
    
    tenant_id: UUID
    price_list_id: UUID
    product_id: UUID
    product_type: str
