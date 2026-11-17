"""Pricing domain service."""

from datetime import date
from decimal import Decimal
from uuid import UUID
from typing import Optional


class PricingService:
    """
    Pricing service for determining product unit prices.

    Priority logic (Option B — approved 2026-11-14):

    For each price list in the existing priority order (client list first,
    then default list), the lookup is performed within the same list:

      1a. Exact variant price  (product_id=variant_id, product_type='variant')
      1b. Parent template price (product_id=template_id, product_type='finished_product')
            — only when product_type=='variant' AND variant_template_provider is set
            — template_id is resolved once via variant_template_provider

    The two list tiers are still applied in order:
      Tier 1  client-specific price list  → 1a then 1b within the list
      Tier 2  tenant default price list   → 1a then 1b within the list
      Tier 3  item_variant.selling_price fallback (variants only, via variant_price_provider)
      Tier 4  raise ValueError

    Key invariants preserved:
    - Client list always evaluated before default list.
    - Exact variant price always beats parent price within the same list.
    - Parent price in client list beats exact variant price in default list
      (because the client list is exhausted — both 1a and 1b — before the
      default list is consulted).
    - variant.selling_price is only used when NO price-list entry (variant or parent)
      was found in any list.
    - Manual override on the Sales Order line bypasses this service entirely
      (handled upstream in AddLineToSalesOrderCommandHandler).
    - Zero is never silently assigned; ValueError is raised when no price found.
    - product_type=='finished_product' lines do NOT trigger the template fallback
      (a template cannot fall back to itself; fallback is variant → parent only).

    Requirements: REQ-SP-004 AC1, AC3; REQ-SP-005 AC4; Phase 1 Option B
    """

    def __init__(
        self,
        price_list_repository,
        variant_price_provider=None,
        variant_template_provider=None,
    ):
        """Initialize pricing service.

        Args:
            price_list_repository: Repository for loading price lists.
            variant_price_provider: Optional async callable(tenant_id, variant_id) -> Decimal | None.
                Used as the tier-3 fallback when no price list covers the product.
                Only consulted for product_type == "variant".
            variant_template_provider: Optional async callable(tenant_id, variant_id) -> UUID | None.
                Returns the parent template_id for a variant.
                Used for within-list parent-template fallback (Option B).
                Only consulted for product_type == "variant".
        """
        self.price_list_repo = price_list_repository
        self.variant_price_provider = variant_price_provider
        self.variant_template_provider = variant_template_provider

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

        See class docstring for the full priority chain.

        Args:
            tenant_id: Tenant ID
            product_id: Product ID (variant or template)
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

        # Resolve the parent template_id once (only for variant products).
        # This is a single async lookup done lazily — only when we know we
        # need to attempt a within-list parent fallback.
        parent_template_id: Optional[UUID] = None
        is_variant = product_type == "variant"

        async def _get_parent_id() -> Optional[UUID]:
            """Lazily resolve and cache the parent template_id."""
            nonlocal parent_template_id
            if parent_template_id is None and is_variant and self.variant_template_provider:
                parent_template_id = await self.variant_template_provider(
                    tenant_id, product_id
                )
            return parent_template_id

        def _lookup_in_list(plist) -> Optional[Decimal]:
            """Look up exact variant price in this list."""
            return plist.get_price(product_id, product_type)

        def _lookup_parent_in_list(plist, tmpl_id: UUID) -> Optional[Decimal]:
            """Look up parent template price in this list (Option B fallback)."""
            return plist.get_price(tmpl_id, "finished_product")

        # ── Tier 1: client-specific price list ──────────────────────────────
        if client_id:
            price_lists = await self.price_list_repo.find_by_client(
                tenant_id=tenant_id,
                client_id=client_id,
                include_inactive=False,
            )
            for plist in price_lists:
                if not plist.is_valid_on(price_date):
                    continue

                # 1a. Exact variant (or finished_product) price
                price = _lookup_in_list(plist)
                if price is not None:
                    return price

                # 1b. Parent template fallback (Option B — variant only)
                tmpl_id = await _get_parent_id()
                if tmpl_id is not None:
                    price = _lookup_parent_in_list(plist, tmpl_id)
                    if price is not None:
                        return price

        # ── Tier 2: tenant default price list ───────────────────────────────
        default_lists = await self.price_list_repo.find_default(
            tenant_id=tenant_id,
            include_inactive=False,
        )
        for plist in default_lists:
            if not plist.is_valid_on(price_date):
                continue

            # 2a. Exact variant (or finished_product) price
            price = _lookup_in_list(plist)
            if price is not None:
                return price

            # 2b. Parent template fallback (Option B — variant only)
            tmpl_id = await _get_parent_id()
            if tmpl_id is not None:
                price = _lookup_parent_in_list(plist, tmpl_id)
                if price is not None:
                    return price

        # ── Tier 3: item_variant.selling_price (catalog price, variants only) ──
        if self.variant_price_provider and is_variant:
            catalog_price = await self.variant_price_provider(tenant_id, product_id)
            if catalog_price is not None and catalog_price > 0:
                return catalog_price

        raise ValueError(
            f"No price found for product {product_id} ({product_type}) "
            f"at {price_date} for client {client_id or 'default'}"
        )
