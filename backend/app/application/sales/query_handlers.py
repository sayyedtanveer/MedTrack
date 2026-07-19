"""Sales query handlers (read-only operations)."""

from backend.app.domain.sales.repositories import (
    ClientRepository,
    SalesOrderRepository,
    PriceListRepository,
)
from backend.app.domain.sales.services import PricingService, CreditValidationService
from backend.app.application.sales.queries import (
    GetClientByIdQuery,
    GetClientByCodeQuery,
    ListClientsQuery,
    GetSalesOrderByIdQuery,
    GetSalesOrderByNumberQuery,
    ListClientOrdersQuery,
    ListOrdersByDateRangeQuery,
    ListPendingOrdersQuery,
    GetProductPriceQuery,
    CheckClientCreditQuery,
    GetPriceListByIdQuery,
    ListPriceListsQuery,
    GetOrderCountByStatusQuery,
    ListDraftOrdersQuery,
    ListOrdersByDeliveryDateQuery,
)


class GetClientByIdQueryHandler:
    """Handler for fetching client by ID."""

    def __init__(self, client_repo: ClientRepository):
        self.client_repo = client_repo

    async def handle(self, query: GetClientByIdQuery):
        """Get client."""
        client = await self.client_repo.get_by_id(
            id=query.client_id,
            tenant_id=query.tenant_id,
        )
        if not client:
            raise ValueError(f"Client {query.client_id} not found")
        return client.to_dict()


class GetClientByCodeQueryHandler:
    """Handler for fetching client by code."""

    def __init__(self, client_repo: ClientRepository):
        self.client_repo = client_repo

    async def handle(self, query: GetClientByCodeQuery):
        """Get client by code."""
        client = await self.client_repo.get_by_code(
            tenant_id=query.tenant_id,
            code=query.code,
        )
        if not client:
            raise ValueError(f"Client with code '{query.code}' not found")
        return client.to_dict()


class ListClientsQueryHandler:
    """Handler for listing clients."""

    def __init__(self, client_repo: ClientRepository):
        self.client_repo = client_repo

    async def handle(self, query: ListClientsQuery):
        """List clients."""
        clients = await self.client_repo.find_by_status(
            tenant_id=query.tenant_id,
            is_active=query.is_active if query.is_active is not None else True,
            search=query.search,
            limit=query.limit,
            offset=query.offset,
        )
        return [c.to_dict() for c in clients]


class GetSalesOrderByIdQueryHandler:
    """Handler for fetching order by ID."""

    def __init__(self, order_repo: SalesOrderRepository):
        self.order_repo = order_repo

    async def handle(self, query: GetSalesOrderByIdQuery):
        """Get order."""
        order = await self.order_repo.get_by_id(
            id=query.order_id,
            tenant_id=query.tenant_id,
        )
        if not order:
            raise ValueError(f"Order {query.order_id} not found")
        return order.to_dict()


class GetSalesOrderByNumberQueryHandler:
    """Handler for fetching order by order number."""

    def __init__(self, order_repo: SalesOrderRepository):
        self.order_repo = order_repo

    async def handle(self, query: GetSalesOrderByNumberQuery):
        """Get order by number."""
        order = await self.order_repo.get_by_order_number(
            tenant_id=query.tenant_id,
            order_number=str(query.order_number),
        )
        if not order:
            raise ValueError(f"Order {query.order_number} not found")
        return order.to_dict()


class ListClientOrdersQueryHandler:
    """Handler for listing client orders."""

    def __init__(self, order_repo: SalesOrderRepository):
        self.order_repo = order_repo

    async def handle(self, query: ListClientOrdersQuery):
        """List orders for client."""
        orders = await self.order_repo.find_by_client(
            tenant_id=query.tenant_id,
            client_id=query.client_id,
            status=query.status,
            limit=query.limit,
            offset=query.offset,
        )
        return [o.to_dict() for o in orders]


class ListOrdersByDateRangeQueryHandler:
    """Handler for listing orders by date range."""

    def __init__(self, order_repo: SalesOrderRepository):
        self.order_repo = order_repo

    async def handle(self, query: ListOrdersByDateRangeQuery):
        """List orders in date range."""
        orders = await self.order_repo.find_by_date_range(
            tenant_id=query.tenant_id,
            start_date=query.start_date,
            end_date=query.end_date,
            status=query.status,
            limit=query.limit,
            offset=query.offset,
        )
        return [o.to_dict() for o in orders]


class ListDraftOrdersQueryHandler:
    """Handler for listing draft orders."""

    def __init__(self, order_repo: SalesOrderRepository):
        self.order_repo = order_repo

    async def handle(self, query: ListDraftOrdersQuery):
        """List draft orders."""
        orders = await self.order_repo.find_pending_confirmation(
            tenant_id=query.tenant_id,
            limit=query.limit,
        )
        return [o.to_dict() for o in orders]


class ListOrdersByDeliveryDateQueryHandler:
    """Handler for listing orders by delivery date."""

    def __init__(self, order_repo: SalesOrderRepository):
        self.order_repo = order_repo

    async def handle(self, query: ListOrdersByDeliveryDateQuery):
        """List orders by delivery date."""
        orders = await self.order_repo.find_by_delivery_date_range(
            tenant_id=query.tenant_id,
            start_date=query.start_date,
            end_date=query.end_date,
        )
        return [o.to_dict() for o in orders]


class GetProductPriceQueryHandler:
    """Handler for fetching product price."""

    def __init__(self, pricing_service: PricingService):
        self.pricing_service = pricing_service

    async def handle(self, query: GetProductPriceQuery):
        """Get product price."""
        price = await self.pricing_service.get_price(
            tenant_id=query.tenant_id,
            product_id=query.product_id,
            product_type=query.product_type,
            client_id=query.client_id,
            price_date=query.price_date,
        )
        return {"product_id": str(query.product_id), "unit_price": str(price)}


class CheckClientCreditQueryHandler:
    """Handler for checking client credit."""

    def __init__(self, client_repo: ClientRepository):
        self.client_repo = client_repo

    async def handle(self, query: CheckClientCreditQuery):
        """Check client credit."""
        client = await self.client_repo.get_by_id(
            id=query.client_id,
            tenant_id=query.tenant_id,
        )
        if not client:
            raise ValueError(f"Client {query.client_id} not found")

        credit_limit = client.credit_limit
        credit_used = client.credit_used
        order_total = query.order_total or 0

        if not credit_limit:
            return {
                "client_id": str(client.id),
                "credit_limit": None,
                "credit_used": str(credit_used),
                "available_credit": None,
                "is_valid_for_amount": True,
                "message": "Client has unlimited credit",
            }

        available_credit = credit_limit - credit_used
        is_valid = order_total <= available_credit
        return {
            "client_id": str(client.id),
            "credit_limit": str(credit_limit),
            "credit_used": str(credit_used),
            "available_credit": str(available_credit),
            "is_valid_for_amount": is_valid,
            "message": "Credit available" if is_valid else "Insufficient credit",
        }


class GetPriceListByIdQueryHandler:
    """Handler for fetching price list."""

    def __init__(self, price_list_repo: PriceListRepository):
        self.price_list_repo = price_list_repo

    async def handle(self, query: GetPriceListByIdQuery):
        """Get price list."""
        price_list = await self.price_list_repo.get_by_id(
            id=query.price_list_id,
            tenant_id=query.tenant_id,
        )
        if not price_list:
            raise ValueError(f"Price list {query.price_list_id} not found")
        return price_list.to_dict()


class ListPriceListsQueryHandler:
    """Handler for listing price lists."""

    def __init__(self, price_list_repo: PriceListRepository):
        self.price_list_repo = price_list_repo

    async def handle(self, query: ListPriceListsQuery):
        """List price lists."""
        price_lists = await self.price_list_repo.find_default(
            tenant_id=query.tenant_id,
            include_inactive=not query.is_active,
        )
        return [pl.to_dict() for pl in price_lists]


class GetOrderCountByStatusQueryHandler:
    """Handler for getting order counts by status."""

    def __init__(self, order_repo: SalesOrderRepository):
        self.order_repo = order_repo

    async def handle(self, query: GetOrderCountByStatusQuery):
        """Get order counts by status."""
        counts = await self.order_repo.count_by_status(
            tenant_id=query.tenant_id,
        )
        return counts

