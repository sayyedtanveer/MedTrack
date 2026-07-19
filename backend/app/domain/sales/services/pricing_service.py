"""Pricing domain service."""

from datetime import date
from decimal import Decimal
from uuid import UUID


class PricingService:
    """
    Pricing service for determining product unit prices.
    
    Priority logic:
    1. Client-specific price list (if exists and valid)
    2. Default price list
    3. Raise error if no price found
    """

    def __init__(self, price_list_repository):
        """Initialize pricing service."""
        self.price_list_repo = price_list_repository

    async def get_price(
        self,
        tenant_id: UUID,
        product_id: UUID,
        product_type: str,
        client_id: UUID | None = None,
        price_date: date | None = None,
    ) -> Decimal:
        """
        Get unit price for a product.
        
        Pricing priority:
        1. Client-specific price list (if client_id provided)
        2. Default price list
        
        Args:
            tenant_id: Tenant ID
            product_id: Product ID
            product_type: Product type ("variant" or "finished_product")
            client_id: Client ID (optional, for client-specific pricing)
            price_date: Date to check validity (defaults to today)
            
        Returns:
            Unit price as Decimal
            
        Raises:
            ValueError: If no price found
        """
        if price_date is None:
            price_date = date.today()
        
        # Try client-specific price list first
        if client_id:
            price_lists = await self.price_list_repo.find_by_client(
                tenant_id=tenant_id,
                client_id=client_id,
                include_inactive=False,
            )
            for plist in price_lists:
                if plist.is_valid_on(price_date):
                    price = plist.get_price(product_id, product_type)
                    if price is not None:
                        return price
        
        # Fall back to default price list
        default_lists = await self.price_list_repo.find_default(
            tenant_id=tenant_id,
            include_inactive=False,
        )
        
        for plist in default_lists:
            if plist.is_valid_on(price_date):
                price = plist.get_price(product_id, product_type)
                if price is not None:
                    return price
        
        raise ValueError(
            f"No price found for product {product_id} ({product_type}) "
            f"at {price_date} for client {client_id or 'default'}"
        )
