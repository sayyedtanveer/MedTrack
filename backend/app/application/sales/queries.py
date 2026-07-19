"""Sales order application queries (CQRS pattern)."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class GetClientByIdQuery:
    """Get client details by ID."""
    
    tenant_id: UUID
    client_id: UUID


@dataclass(frozen=True)
class GetClientByCodeQuery:
    """Get client details by code."""
    
    tenant_id: UUID
    code: str


@dataclass(frozen=True)
class ListClientsQuery:
    """List clients with pagination and filtering."""
    
    tenant_id: UUID
    is_active: bool | None = True
    search: str | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetSalesOrderByIdQuery:
    """Get sales order details by ID."""
    
    tenant_id: UUID
    order_id: UUID


@dataclass(frozen=True)
class GetSalesOrderByNumberQuery:
    """Get sales order by order number."""
    
    tenant_id: UUID
    order_number: str


@dataclass(frozen=True)
class ListClientOrdersQuery:
    """List orders for a specific client."""
    
    tenant_id: UUID
    client_id: UUID
    status: str | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class ListOrdersByDateRangeQuery:
    """List orders within a date range."""
    
    tenant_id: UUID
    start_date: date
    end_date: date
    status: str | None = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class ListPendingOrdersQuery:
    """List orders pending confirmation or fulfillment."""
    
    tenant_id: UUID
    limit: int = 50


@dataclass(frozen=True)
class GetAvailableInventoryQuery:
    """Get available inventory for a product."""
    
    tenant_id: UUID
    product_id: UUID
    product_type: str


@dataclass(frozen=True)
class GetProductPriceQuery:
    """Get product price from pricing rules."""
    
    tenant_id: UUID
    product_id: UUID
    product_type: str
    client_id: UUID | None = None
    price_date: date | None = None


@dataclass(frozen=True)
class CheckClientCreditQuery:
    """Check client credit availability."""
    
    tenant_id: UUID
    client_id: UUID
    order_total: float | None = None


@dataclass(frozen=True)
class GetPriceListByIdQuery:
    """Get price list details."""
    
    tenant_id: UUID
    price_list_id: UUID


@dataclass(frozen=True)
class ListPriceListsQuery:
    """List price lists."""
    
    tenant_id: UUID
    is_default: bool | None = None
    is_active: bool = True
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetOrderSummaryQuery:
    """Get key metrics and summary for an order."""
    
    tenant_id: UUID
    order_id: UUID


@dataclass(frozen=True)
class GetClientCreditSummaryQuery:
    """Get credit usage summary for a client."""
    
    tenant_id: UUID
    client_id: UUID


@dataclass(frozen=True)
class ListHighCreditUsageClientsQuery:
    """Find clients using most of their credit limit."""
    
    tenant_id: UUID
    threshold_percent: float = 80.0
    limit: int = 50


@dataclass(frozen=True)
class GetOrderCountByStatusQuery:
    """Get count of orders by status."""
    
    tenant_id: UUID


@dataclass(frozen=True)
class ListDraftOrdersQuery:
    """List all draft orders waiting for confirmation."""
    
    tenant_id: UUID
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class ListOrdersByDeliveryDateQuery:
    """List orders due for delivery in a date range."""
    
    tenant_id: UUID
    start_date: date
    end_date: date
    limit: int = 100
    offset: int = 0
