"""Unit and regression tests for Price List Phase 1A hardening.

Covers:
- Enriched PriceListLine initialization and to_dict serialization
- Duplicate line detection and DuplicatePriceListLineError
- Coexistence of variant and finished_product sharing the same UUID value
- Exact (product_id, product_type) line deletion
- Ambiguous line deletion rejection when product_type is absent and multiple lines match
- Unambiguous legacy line deletion when exactly one line matches
- ProductNotFoundError on deleting non-existent product
- Repository validate_product_for_pricing behavior (mocked session)
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
import pytest

from backend.app.domain.sales.entities.price_list import PriceList, PriceListLine
from backend.app.domain.sales.exceptions import (
    AmbiguousLineDeletionError,
    DuplicatePriceListLineError,
    InvalidProductTypeError,
    PriceListNotFoundError,
    ProductInactiveError,
    ProductNotFoundError,
)
from backend.app.domain.sales.repositories.price_list_repository import PriceListRepository
from backend.app.infrastructure.persistence.models.item_variant_model import ItemVariantModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel


class TestPriceListLineEnrichment:
    """Tests for enriched PriceListLine entity and serialization."""

    def test_line_init_with_metadata(self):
        line_id = uuid4()
        pl_id = uuid4()
        prod_id = uuid4()
        line = PriceListLine(
            id=line_id,
            price_list_id=pl_id,
            product_id=prod_id,
            product_type="variant",
            unit_price=Decimal("150.50"),
            product_code="VAR-001",
            product_name="Rotameter Tube",
            uom_code="PCS",
            uom_name="Pieces",
            is_orphaned=False,
            is_inactive=False,
        )

        assert line.id == line_id
        assert line.price_list_id == pl_id
        assert line.product_id == prod_id
        assert line.product_type == "variant"
        assert line.unit_price == Decimal("150.50")
        assert line.product_code == "VAR-001"
        assert line.product_name == "Rotameter Tube"
        assert line.uom_code == "PCS"
        assert line.uom_name == "Pieces"
        assert line.is_orphaned is False
        assert line.is_inactive is False

    def test_line_to_dict_includes_all_enriched_fields(self):
        line_id = uuid4()
        pl_id = uuid4()
        prod_id = uuid4()
        line = PriceListLine(
            id=line_id,
            price_list_id=pl_id,
            product_id=prod_id,
            product_type="finished_product",
            unit_price=Decimal("250.00"),
            product_code="FG-100",
            product_name="Complete Meter",
            uom_code="NOS",
            uom_name="Numbers",
            is_orphaned=False,
            is_inactive=False,
        )

        d = line.to_dict()
        assert d["id"] == str(line_id)
        assert d["price_list_id"] == str(pl_id)
        assert d["product_id"] == str(prod_id)
        assert d["product_type"] == "finished_product"
        assert d["unit_price"] == "250.00"
        assert d["product_code"] == "FG-100"
        assert d["product_name"] == "Complete Meter"
        assert d["uom_code"] == "NOS"
        assert d["uom_name"] == "Numbers"
        assert d["is_orphaned"] is False
        assert d["is_inactive"] is False

    def test_legacy_line_without_metadata_defaults_gracefully(self):
        line = PriceListLine(
            id=uuid4(),
            price_list_id=uuid4(),
            product_id=uuid4(),
            product_type="variant",
            unit_price=Decimal("50.00"),
        )
        d = line.to_dict()
        assert d["product_code"] is None
        assert d["product_name"] is None
        assert d["uom_code"] is None
        assert d["is_orphaned"] is False
        assert d["is_inactive"] is False


class TestPriceListDuplicateAndCoexistence:
    """Tests for duplicate prevention and multi-source coexistence."""

    def test_duplicate_line_raises_duplicate_error(self):
        price_list = PriceList(id=uuid4(), tenant_id=uuid4(), name="Test PL")
        prod_id = uuid4()

        line1 = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=prod_id,
            product_type="variant",
            unit_price=Decimal("100.00"),
        )
        price_list.add_line(line1)

        line2 = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=prod_id,
            product_type="variant",
            unit_price=Decimal("120.00"),
        )

        with pytest.raises(DuplicatePriceListLineError) as exc_info:
            price_list.add_line(line2)

        assert exc_info.value.product_id == prod_id
        assert exc_info.value.product_type == "variant"

    def test_coexistence_same_uuid_different_product_types(self):
        """Regression safeguard: Same UUID value used by a variant and a finished material."""
        price_list = PriceList(id=uuid4(), tenant_id=uuid4(), name="Test PL")
        shared_uuid = uuid4()

        variant_line = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=shared_uuid,
            product_type="variant",
            unit_price=Decimal("100.00"),
        )
        finished_line = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=shared_uuid,
            product_type="finished_product",
            unit_price=Decimal("200.00"),
        )

        price_list.add_line(variant_line)
        price_list.add_line(finished_line)

        assert len(price_list.lines) == 2
        assert price_list.get_price(shared_uuid, "variant") == Decimal("100.00")
        assert price_list.get_price(shared_uuid, "finished_product") == Decimal("200.00")


class TestPriceListLineDeletion:
    """Tests for exact, ambiguous, and unambiguous line deletion."""

    def test_delete_exact_when_sharing_same_uuid(self):
        """Deleting with product_type removes only the matching source."""
        price_list = PriceList(id=uuid4(), tenant_id=uuid4(), name="Test PL")
        shared_uuid = uuid4()

        v_line = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=shared_uuid,
            product_type="variant",
            unit_price=Decimal("100.00"),
        )
        f_line = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=shared_uuid,
            product_type="finished_product",
            unit_price=Decimal("200.00"),
        )
        price_list.add_line(v_line)
        price_list.add_line(f_line)

        # Remove only variant
        price_list.remove_line(shared_uuid, product_type="variant")

        assert len(price_list.lines) == 1
        assert price_list.lines[0].product_type == "finished_product"
        assert price_list.lines[0].unit_price == Decimal("200.00")

    def test_delete_ambiguous_fails_when_type_omitted(self):
        """If multiple lines share the same product_id, omitting product_type raises AmbiguousLineDeletionError."""
        price_list = PriceList(id=uuid4(), tenant_id=uuid4(), name="Test PL")
        shared_uuid = uuid4()

        v_line = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=shared_uuid,
            product_type="variant",
            unit_price=Decimal("100.00"),
        )
        f_line = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=shared_uuid,
            product_type="finished_product",
            unit_price=Decimal("200.00"),
        )
        price_list.add_line(v_line)
        price_list.add_line(f_line)

        with pytest.raises(AmbiguousLineDeletionError):
            price_list.remove_line(shared_uuid)

        # Also test with legacy "PRODUCT" placeholder
        with pytest.raises(AmbiguousLineDeletionError):
            price_list.remove_line(shared_uuid, product_type="PRODUCT")

    def test_delete_unambiguous_succeeds_when_single_line_exists(self):
        """Legacy compatibility: If only 1 line matches, omitting product_type removes it safely."""
        price_list = PriceList(id=uuid4(), tenant_id=uuid4(), name="Test PL")
        prod_id = uuid4()

        line = PriceListLine(
            id=uuid4(),
            price_list_id=price_list.id,
            product_id=prod_id,
            product_type="variant",
            unit_price=Decimal("75.00"),
        )
        price_list.add_line(line)

        price_list.remove_line(prod_id)
        assert len(price_list.lines) == 0

    def test_delete_non_existent_product_raises_not_found(self):
        price_list = PriceList(id=uuid4(), tenant_id=uuid4(), name="Test PL")
        with pytest.raises(ProductNotFoundError):
            price_list.remove_line(uuid4(), product_type="variant")


@pytest.mark.asyncio
class TestPriceListRepositoryProductValidation:
    """Tests for repository product existence, tenant isolation, and active status checks."""

    async def test_validate_variant_not_found_raises_generic_404(self):
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        repo = PriceListRepository(session)
        target_uuid = uuid4()

        with pytest.raises(ProductNotFoundError) as exc_info:
            await repo.validate_product_for_pricing(
                tenant_id=uuid4(),
                product_id=target_uuid,
                product_type="variant",
            )

        # Must never leak cross-tenant info
        assert "not found" in str(exc_info.value).lower()
        assert "tenant" not in str(exc_info.value).lower()

    async def test_validate_variant_inactive_raises_inactive_error(self):
        session = AsyncMock()
        variant = ItemVariantModel()
        variant.id = uuid4()
        variant.code = "VAR-INACTIVE"
        variant.is_active = False
        variant.is_deleted = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = variant
        session.execute.return_value = mock_result

        repo = PriceListRepository(session)
        with pytest.raises(ProductInactiveError) as exc_info:
            await repo.validate_product_for_pricing(
                tenant_id=uuid4(),
                product_id=variant.id,
                product_type="variant",
            )
        assert "inactive" in str(exc_info.value).lower()

    async def test_validate_material_raw_type_raises_invalid_type_error(self):
        session = AsyncMock()
        material = MaterialModel()
        material.id = uuid4()
        material.code = "RAW-STEEL"
        material.material_type = "raw"  # Not finished!
        material.is_active = True
        material.is_deleted = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = material
        session.execute.return_value = mock_result

        repo = PriceListRepository(session)
        with pytest.raises(InvalidProductTypeError) as exc_info:
            await repo.validate_product_for_pricing(
                tenant_id=uuid4(),
                product_id=material.id,
                product_type="finished_product",
            )
        assert "not a finished product" in str(exc_info.value).lower()

    async def test_validate_finished_material_success(self):
        session = AsyncMock()
        material = MaterialModel()
        material.id = uuid4()
        material.code = "FG-ROTA"
        material.material_type = "finished"
        material.is_active = True
        material.is_deleted = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = material
        session.execute.return_value = mock_result

        repo = PriceListRepository(session)
        # Should not raise
        await repo.validate_product_for_pricing(
            tenant_id=uuid4(),
            product_id=material.id,
            product_type="finished_product",
        )
