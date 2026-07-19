"""Sales domain entities."""

from backend.app.domain.sales.entities.client import Client
from backend.app.domain.sales.entities.sales_order import SalesOrder
from backend.app.domain.sales.entities.sales_order_line import SalesOrderLine
from backend.app.domain.sales.entities.price_list import PriceList, PriceListLine

__all__ = [
    "Client",
    "SalesOrder",
    "SalesOrderLine",
    "PriceList",
    "PriceListLine",
]


