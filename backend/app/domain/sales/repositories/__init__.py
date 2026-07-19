"""Sales domain repositories."""

from backend.app.domain.sales.repositories.client_repository import ClientRepository
from backend.app.domain.sales.repositories.sales_order_repository import SalesOrderRepository
from backend.app.domain.sales.repositories.price_list_repository import PriceListRepository

__all__ = [
    "ClientRepository",
    "SalesOrderRepository",
    "PriceListRepository",
]

