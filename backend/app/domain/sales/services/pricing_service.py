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
    3. item_variant.selling_price fallback (variant_price_provider, variants only)
    4. Raise ValueError if no price found

    Requirements: REQ-SP-004 AC1, AC3; REQ-SP-005 AC4
    """

    def __init__(self, price_list_repository, variant_price_provider=None):
        """Initialize pricing service.

        Args:
            price_list_repository: Repository for loading price lists.
            variant_price_provider: Optional async callable(tenant_id, variant_id) -> Decimal | None.
                Used as the tier-3 fallback when no price list covers the product.
                Only consulted for product_type == "variant".
        """
        self.price_list_repo = price_list_repository
        self.variant_price_provider = variant_price_provider

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
        1. Client-specific price list (if client_id provided and list is valid on price_date)
        2. Tenant default price list (if valid on price_date)
        3. item_variant.selling_price via variant_price_provider (variants only, price > 0)
        4. ValueError if none of the above yields a price

        Args:
            tenant_id: Tenant ID
            product_id: Product ID
            product_type: Product type ("variant" or "finished_product")
            client_id: Client ID (optional, for client-specific pricing)
            price_date: Date to check validity (defaults to today)

        Returns:
            Unit price as Decimal

        Raises:
            ValueError: If no price found via any tier
        """
        if price_date is None:
            price_date = date.today()

        # Tier 1: client-specific price list
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

        # Tier 2: tenant default price list
        default_lists = await self.price_list_repo.find_default(
            tenant_id=tenant_id,
            include_inactive=False,
        )
        for plist in default_lists:
            if plist.is_valid_on(price_date):
                price = plist.get_price(product_id, product_type)
                if price is not None:
                    return price

        # Tier 3: item_variant.selling_price (catalog price, variants only)
        if self.variant_price_provider and product_type == "variant":
            catalog_price = await self.variant_price_provider(tenant_id, product_id)
            if catalog_price is not None and catalog_price > 0:
                return catalog_price

        raise ValueError(
            f"No price found for product {product_id} ({product_type}) "
            f"at {price_date} for client {client_id or 'default'}"
        )
