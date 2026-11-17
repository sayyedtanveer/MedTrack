"""
Unit tests for PricingService — Option B parent-template fallback.

Policy (approved 2026-11-14):
  Within each price list (client list first, then default list):
    1a  Exact variant price
    1b  Parent template price (variant → template via variant_template_provider)
  Tier 3  variant.selling_price
  Tier 4  ValueError

Tests verify:
  - Variant and parent both priced in same list
  - Variant priced, parent unpriced
  - Parent priced, variant unpriced
  - Neither priced
  - Variant catalog reference fallback (selling_price)
  - Client-specific list exhausted (1a + 1b) before default list consulted
  - Expired/inactive price lists skipped
  - product_type='finished_product' does NOT trigger template fallback
  - Tenant isolation (providers only called with correct tenant)
  - Existing manual override behaviour (unchanged — handled upstream)
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from backend.app.domain.sales.services.pricing_service import PricingService
from backend.app.domain.sales.entities.price_list import PriceList, PriceListLine


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_price_list(
    *,
    is_active: bool = True,
    is_default: bool = False,
    valid_from: date = date(2026, 1, 1),
    valid_to: date | None = None,
    lines: list[tuple[UUID, str, Decimal]] | None = None,
) -> PriceList:
    """Build a PriceList with the given lines list of (product_id, product_type, price)."""
    pl = PriceList(
        id=uuid4(),
        tenant_id=uuid4(),
        name="Test List",
        is_default=is_default,
        is_active=is_active,
        valid_from=valid_from,
        valid_to=valid_to,
    )
    for product_id, product_type, unit_price in (lines or []):
        pl.lines.append(
            PriceListLine(
                id=uuid4(),
                price_list_id=pl.id,
                product_id=product_id,
                product_type=product_type,
                unit_price=unit_price,
            )
        )
    return pl


def _make_service(
    *,
    client_lists: list[PriceList] | None = None,
    default_lists: list[PriceList] | None = None,
    selling_price: Decimal | None = None,
    template_id: UUID | None = None,
) -> PricingService:
    """Build a PricingService with mocked repository and providers."""
    repo = MagicMock()
    repo.find_by_client = AsyncMock(return_value=client_lists or [])
    repo.find_default = AsyncMock(return_value=default_lists or [])

    variant_price_provider = AsyncMock(return_value=selling_price)
    variant_template_provider = AsyncMock(return_value=template_id)

    return PricingService(repo, variant_price_provider, variant_template_provider)


TENANT = uuid4()
CLIENT = uuid4()
VARIANT_ID = uuid4()
TEMPLATE_ID = uuid4()
TODAY = date(2026, 11, 14)


# ── Core Option B scenarios ───────────────────────────────────────────────────

class TestOptionBVariantAndParentBothPriced:
    """When both variant and parent are in the same list, variant price wins."""

    @pytest.mark.asyncio
    async def test_variant_price_returned_when_both_in_default_list(self):
        default_list = _make_price_list(
            is_default=True,
            lines=[
                (VARIANT_ID, "variant", Decimal("900.00")),
                (TEMPLATE_ID, "finished_product", Decimal("1000.00")),
            ],
        )
        svc = _make_service(default_lists=[default_list], template_id=TEMPLATE_ID)

        price = await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            price_date=TODAY,
        )
        assert price == Decimal("900.00")

    @pytest.mark.asyncio
    async def test_variant_price_beats_parent_in_client_list(self):
        client_list = _make_price_list(
            lines=[
                (VARIANT_ID, "variant", Decimal("800.00")),
                (TEMPLATE_ID, "finished_product", Decimal("1000.00")),
            ],
        )
        svc = _make_service(client_lists=[client_list], template_id=TEMPLATE_ID)

        price = await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            client_id=CLIENT,
            price_date=TODAY,
        )
        assert price == Decimal("800.00")


class TestOptionBVariantPricedParentNot:
    """When only variant is priced, return variant price with no parent lookup."""

    @pytest.mark.asyncio
    async def test_variant_only_in_default_list(self):
        default_list = _make_price_list(
            is_default=True,
            lines=[(VARIANT_ID, "variant", Decimal("750.00"))],
        )
        svc = _make_service(default_lists=[default_list], template_id=TEMPLATE_ID)

        price = await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            price_date=TODAY,
        )
        assert price == Decimal("750.00")

    @pytest.mark.asyncio
    async def test_template_provider_not_called_when_variant_found(self):
        """Confirm template_id is not looked up when the exact variant price is found."""
        default_list = _make_price_list(
            is_default=True,
            lines=[(VARIANT_ID, "variant", Decimal("750.00"))],
        )
        svc = _make_service(default_lists=[default_list], template_id=TEMPLATE_ID)

        await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            price_date=TODAY,
        )
        # Provider should NOT have been called (lazy evaluation)
        svc.variant_template_provider.assert_not_called()


class TestOptionBParentPricedVariantNot:
    """When only parent is priced in the list, parent price is used as fallback."""

    @pytest.mark.asyncio
    async def test_parent_price_used_from_default_list(self):
        default_list = _make_price_list(
            is_default=True,
            lines=[(TEMPLATE_ID, "finished_product", Decimal("1000.00"))],
        )
        svc = _make_service(default_lists=[default_list], template_id=TEMPLATE_ID)

        price = await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            price_date=TODAY,
        )
        assert price == Decimal("1000.00")

    @pytest.mark.asyncio
    async def test_parent_price_used_from_client_list(self):
        client_list = _make_price_list(
            lines=[(TEMPLATE_ID, "finished_product", Decimal("950.00"))],
        )
        svc = _make_service(client_lists=[client_list], template_id=TEMPLATE_ID)

        price = await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            client_id=CLIENT,
            price_date=TODAY,
        )
        assert price == Decimal("950.00")

    @pytest.mark.asyncio
    async def test_client_parent_price_beats_default_variant_price(self):
        """
        Option B: client list exhausted (1a + 1b) before default list.
        Client list has parent price (₹950), default list has variant price (₹900).
        Expected: client list parent price (₹950) returned.
        """
        client_list = _make_price_list(
            lines=[(TEMPLATE_ID, "finished_product", Decimal("950.00"))],
        )
        default_list = _make_price_list(
            is_default=True,
            lines=[(VARIANT_ID, "variant", Decimal("900.00"))],
        )
        svc = _make_service(
            client_lists=[client_list],
            default_lists=[default_list],
            template_id=TEMPLATE_ID,
        )

        price = await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            client_id=CLIENT,
            price_date=TODAY,
        )
        assert price == Decimal("950.00")


class TestOptionBNeitherPriced:
    """When no price-list entry exists, tier-3 (selling_price) is consulted."""

    @pytest.mark.asyncio
    async def test_selling_price_fallback_when_no_list_entry(self):
        svc = _make_service(
            default_lists=[],
            selling_price=Decimal("500.00"),
            template_id=TEMPLATE_ID,
        )
        price = await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            price_date=TODAY,
        )
        assert price == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_error_when_no_price_anywhere(self):
        svc = _make_service(
            default_lists=[],
            selling_price=None,
            template_id=TEMPLATE_ID,
        )
        with pytest.raises(ValueError, match="No price found"):
            await svc.get_price(
                tenant_id=TENANT,
                product_id=VARIANT_ID,
                product_type="variant",
                price_date=TODAY,
            )

    @pytest.mark.asyncio
    async def test_error_when_selling_price_is_zero(self):
        """Zero selling_price is treated as not set — no silent zero assignment."""
        svc = _make_service(
            default_lists=[],
            selling_price=Decimal("0"),
            template_id=TEMPLATE_ID,
        )
        with pytest.raises(ValueError, match="No price found"):
            await svc.get_price(
                tenant_id=TENANT,
                product_id=VARIANT_ID,
                product_type="variant",
                price_date=TODAY,
            )


class TestOptionBExpiredAndInactiveLists:
    """Expired or inactive price lists are skipped for both variant and parent lookup."""

    @pytest.mark.asyncio
    async def test_expired_list_skipped(self):
        expired_list = _make_price_list(
            is_default=True,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),   # Expired before TODAY
            lines=[
                (VARIANT_ID, "variant", Decimal("800.00")),
                (TEMPLATE_ID, "finished_product", Decimal("1000.00")),
            ],
        )
        svc = _make_service(
            default_lists=[expired_list],
            selling_price=Decimal("500.00"),
            template_id=TEMPLATE_ID,
        )
        price = await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            price_date=TODAY,
        )
        # Expired list skipped → falls through to selling_price
        assert price == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_inactive_list_not_returned_by_repository(self):
        """Inactive lists are excluded by find_default(include_inactive=False)."""
        # Repository returns empty list (simulates inactive list being filtered)
        svc = _make_service(
            default_lists=[],
            selling_price=Decimal("400.00"),
            template_id=TEMPLATE_ID,
        )
        price = await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            price_date=TODAY,
        )
        assert price == Decimal("400.00")


class TestOptionBFinishedProductTypeNoFallback:
    """
    product_type='finished_product' does NOT trigger the Option B template fallback.
    The template is not a child of itself; fallback is variant → parent only.
    """

    @pytest.mark.asyncio
    async def test_finished_product_uses_exact_match_only(self):
        default_list = _make_price_list(
            is_default=True,
            lines=[(TEMPLATE_ID, "finished_product", Decimal("1200.00"))],
        )
        svc = _make_service(default_lists=[default_list], template_id=None)

        price = await svc.get_price(
            tenant_id=TENANT,
            product_id=TEMPLATE_ID,
            product_type="finished_product",
            price_date=TODAY,
        )
        assert price == Decimal("1200.00")

    @pytest.mark.asyncio
    async def test_finished_product_raises_when_not_priced(self):
        svc = _make_service(default_lists=[], template_id=None, selling_price=None)
        with pytest.raises(ValueError):
            await svc.get_price(
                tenant_id=TENANT,
                product_id=TEMPLATE_ID,
                product_type="finished_product",
                price_date=TODAY,
            )

    @pytest.mark.asyncio
    async def test_template_provider_not_called_for_finished_product(self):
        """variant_template_provider must not be called for finished_product types."""
        default_list = _make_price_list(is_default=True, lines=[])
        svc = _make_service(default_lists=[default_list], template_id=TEMPLATE_ID)

        with pytest.raises(ValueError):
            await svc.get_price(
                tenant_id=TENANT,
                product_id=TEMPLATE_ID,
                product_type="finished_product",
                price_date=TODAY,
            )

        svc.variant_template_provider.assert_not_called()


class TestOptionBBackwardCompatibility:
    """Existing tier ordering and constructor are backward-compatible."""

    @pytest.mark.asyncio
    async def test_works_without_variant_template_provider(self):
        """Service still works when variant_template_provider is None (old callsites)."""
        default_list = _make_price_list(
            is_default=True,
            lines=[(VARIANT_ID, "variant", Decimal("700.00"))],
        )
        # Pass only two args (old constructor signature)
        repo = MagicMock()
        repo.find_by_client = AsyncMock(return_value=[])
        repo.find_default = AsyncMock(return_value=[default_list])
        variant_price_provider = AsyncMock(return_value=None)

        svc = PricingService(repo, variant_price_provider)   # no template provider
        price = await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            price_date=TODAY,
        )
        assert price == Decimal("700.00")

    @pytest.mark.asyncio
    async def test_client_list_always_checked_before_default_list(self):
        """Existing client-before-default ordering preserved."""
        client_list = _make_price_list(
            lines=[(VARIANT_ID, "variant", Decimal("600.00"))],
        )
        default_list = _make_price_list(
            is_default=True,
            lines=[(VARIANT_ID, "variant", Decimal("700.00"))],
        )
        svc = _make_service(
            client_lists=[client_list],
            default_lists=[default_list],
            template_id=TEMPLATE_ID,
        )
        price = await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            client_id=CLIENT,
            price_date=TODAY,
        )
        assert price == Decimal("600.00")

    @pytest.mark.asyncio
    async def test_no_client_list_falls_through_to_default(self):
        default_list = _make_price_list(
            is_default=True,
            lines=[(VARIANT_ID, "variant", Decimal("700.00"))],
        )
        svc = _make_service(default_lists=[default_list])
        # No client_id supplied
        price = await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            price_date=TODAY,
        )
        assert price == Decimal("700.00")

    @pytest.mark.asyncio
    async def test_selling_price_not_used_when_list_has_price(self):
        """Tier-3 selling_price must not override a price found in a list."""
        default_list = _make_price_list(
            is_default=True,
            lines=[(VARIANT_ID, "variant", Decimal("700.00"))],
        )
        svc = _make_service(
            default_lists=[default_list],
            selling_price=Decimal("999.00"),   # Should be ignored
        )
        price = await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            price_date=TODAY,
        )
        assert price == Decimal("700.00")

    @pytest.mark.asyncio
    async def test_tenant_id_passed_to_all_providers(self):
        """Providers must receive the same tenant_id as the get_price call."""
        default_list = _make_price_list(is_default=True, lines=[])
        svc = _make_service(
            default_lists=[default_list],
            selling_price=Decimal("300.00"),
            template_id=TEMPLATE_ID,
        )

        await svc.get_price(
            tenant_id=TENANT,
            product_id=VARIANT_ID,
            product_type="variant",
            price_date=TODAY,
        )

        # Template provider was called with the correct tenant
        svc.variant_template_provider.assert_called_once_with(TENANT, VARIANT_ID)
        # Selling price provider was called with the correct tenant
        svc.variant_price_provider.assert_called_once_with(TENANT, VARIANT_ID)
