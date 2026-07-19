"""
Quotation state machine tests validating supplier quotation lifecycle.

Tests the quotation flow:
1. Create quotation (DRAFT)
2. Supplier submits (DRAFT → SUBMITTED)
3. Admin approves (SUBMITTED → APPROVED)
4. Or admin rejects from any state
"""
from __future__ import annotations

import pytest
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.persistence.models.quality_model import (
    SupplierQuotationModel,
)

from backend.app.domain.procurement.entities import (
    SupplierQuotation,
    SupplierQuotationStatus,
    InvalidQuotationTransitionError,
)
from backend.app.application.procurement.handlers.supplier_quotation_handler import (
    SupplierQuotationHandler,
)


@pytest.mark.asyncio
async def test_quotation_lifecycle_state_machine_transitions(test_session: AsyncSession):
    """Test Quotation state machine properly enforces transitions."""
    # Arrange
    quotation_entity = SupplierQuotation(
        tenant_id=uuid.uuid4(),
        supplier_id=uuid.uuid4(),
        material_id=uuid.uuid4(),
        purchase_order_id=None,
        quoted_price=Decimal("100.00"),
        quantity=Decimal("50"),
        delivery_days=7,
        created_by=uuid.uuid4(),
    )

    # Act & Assert
    assert quotation_entity.status == SupplierQuotationStatus.DRAFT

    # DRAFT → SUBMITTED
    quotation_entity.submit()
    assert quotation_entity.status == SupplierQuotationStatus.SUBMITTED

    # SUBMITTED → APPROVED
    quotation_entity.approve()
    assert quotation_entity.status == SupplierQuotationStatus.APPROVED

    # APPROVED is terminal - should not allow further transitions
    with pytest.raises(InvalidQuotationTransitionError):
        quotation_entity.submit()


@pytest.mark.asyncio
async def test_quotation_invalid_transition_rejected(test_session: AsyncSession):
    """Test invalid quotation transitions are rejected."""
    quotation_entity = SupplierQuotation(
        tenant_id=uuid.uuid4(),
        supplier_id=uuid.uuid4(),
        material_id=uuid.uuid4(),
        purchase_order_id=None,
        quoted_price=Decimal("100.00"),
        quantity=Decimal("50"),
        delivery_days=7,
        created_by=uuid.uuid4(),
    )

    # Try to jump from DRAFT to APPROVED (skipping SUBMITTED)
    with pytest.raises(InvalidQuotationTransitionError):
        quotation_entity.approve()


@pytest.mark.asyncio
async def test_quotation_reject_from_any_state(test_session: AsyncSession):
    """Test quotation can be rejected from any state."""
    # Reject from DRAFT
    quotation_entity = SupplierQuotation(
        tenant_id=uuid.uuid4(),
        supplier_id=uuid.uuid4(),
        material_id=uuid.uuid4(),
        purchase_order_id=None,
        quoted_price=Decimal("100.00"),
        quantity=Decimal("50"),
        delivery_days=7,
        created_by=uuid.uuid4(),
    )
    quotation_entity.reject()
    assert quotation_entity.status == SupplierQuotationStatus.REJECTED

    # Reject from SUBMITTED
    quotation_entity2 = SupplierQuotation(
        tenant_id=uuid.uuid4(),
        supplier_id=uuid.uuid4(),
        material_id=uuid.uuid4(),
        purchase_order_id=None,
        quoted_price=Decimal("150.00"),
        quantity=Decimal("75"),
        delivery_days=10,
        created_by=uuid.uuid4(),
    )
    quotation_entity2.submit()
    quotation_entity2.reject()
    assert quotation_entity2.status == SupplierQuotationStatus.REJECTED


@pytest.mark.asyncio
async def test_quotation_handler_submit(test_session: AsyncSession):
    """Test SupplierQuotationHandler.submit_quotation() enforces domain rules."""
    # Arrange - create a real quotation in database
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    user_id = uuid.uuid4()

    quotation_model = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        material_id=material_id,
        purchase_order_id=None,
        quantity=Decimal("100"),
        unit_price=Decimal("50.00"),
        valid_until=date.today() + timedelta(days=30),
        status="draft",
        created_by=user_id,
    )
    test_session.add(quotation_model)
    await test_session.flush()

    # Act
    handler = SupplierQuotationHandler(test_session)
    result = await handler.submit_quotation(quotation_model.id, tenant_id)

    # Assert
    assert result["status"] == "ok"
    await test_session.refresh(quotation_model)
    assert quotation_model.status == "submitted"


@pytest.mark.asyncio
async def test_quotation_handler_submit_wrong_status_fails(test_session: AsyncSession):
    """Test SupplierQuotationHandler.submit_quotation() rejects non-draft quotations."""
    # Arrange
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    user_id = uuid.uuid4()

    quotation_model = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        material_id=material_id,
        purchase_order_id=None,
        quantity=Decimal("100"),
        unit_price=Decimal("50.00"),
        valid_until=date.today() + timedelta(days=30),
        status="submitted",  # Already submitted
        created_by=user_id,
    )
    test_session.add(quotation_model)
    await test_session.flush()

    # Act & Assert
    handler = SupplierQuotationHandler(test_session)
    with pytest.raises(ValueError, match="Cannot transition"):
        await handler.submit_quotation(quotation_model.id, tenant_id)


@pytest.mark.asyncio
async def test_quotation_handler_approve(test_session: AsyncSession):
    """Test SupplierQuotationHandler.approve_quotation() transitions correctly."""
    # Arrange
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    user_id = uuid.uuid4()

    quotation_model = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        material_id=material_id,
        purchase_order_id=None,
        quantity=Decimal("100"),
        unit_price=Decimal("50.00"),
        valid_until=date.today() + timedelta(days=30),
        status="submitted",
        created_by=user_id,
    )
    test_session.add(quotation_model)
    await test_session.flush()

    # Act
    handler = SupplierQuotationHandler(test_session)
    result = await handler.approve_quotation(quotation_model.id, tenant_id)

    # Assert
    assert result["status"] == "ok"
    await test_session.refresh(quotation_model)
    assert quotation_model.status == "approved"


@pytest.mark.asyncio
async def test_quotation_handler_reject(test_session: AsyncSession):
    """Test SupplierQuotationHandler.reject_quotation() works from any state."""
    # Arrange
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    user_id = uuid.uuid4()

    quotation_model = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        material_id=material_id,
        purchase_order_id=None,
        quantity=Decimal("100"),
        unit_price=Decimal("50.00"),
        valid_until=date.today() + timedelta(days=30),
        status="submitted",
        created_by=user_id,
    )
    test_session.add(quotation_model)
    await test_session.flush()

    # Act
    handler = SupplierQuotationHandler(test_session)
    result = await handler.reject_quotation(quotation_model.id, tenant_id)

    # Assert
    assert result["status"] == "rejected"
    await test_session.refresh(quotation_model)
    assert quotation_model.status == "rejected"


@pytest.mark.asyncio
async def test_quotation_handler_tenant_validation(test_session: AsyncSession):
    """Test SupplierQuotationHandler validates tenant ownership."""
    # Arrange
    tenant_id_1 = uuid.uuid4()
    tenant_id_2 = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    user_id = uuid.uuid4()

    quotation_model = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id_1,
        supplier_id=supplier_id,
        material_id=material_id,
        purchase_order_id=None,
        quantity=Decimal("100"),
        unit_price=Decimal("50.00"),
        valid_until=date.today() + timedelta(days=30),
        status="draft",
        created_by=user_id,
    )
    test_session.add(quotation_model)
    await test_session.flush()

    # Act & Assert - try to operate on quotation from wrong tenant
    handler = SupplierQuotationHandler(test_session)
    with pytest.raises(ValueError, match="Quotation.*not found"):
        await handler.submit_quotation(quotation_model.id, tenant_id_2)


@pytest.mark.asyncio
async def test_quotation_cannot_approve_if_draft(test_session: AsyncSession):
    """Test quotation in DRAFT cannot be approved (must submit first)."""
    # Arrange
    tenant_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    material_id = uuid.uuid4()
    user_id = uuid.uuid4()

    quotation_model = SupplierQuotationModel(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        supplier_id=supplier_id,
        material_id=material_id,
        purchase_order_id=None,
        quantity=Decimal("100"),
        unit_price=Decimal("50.00"),
        valid_until=date.today() + timedelta(days=30),
        status="draft",
        created_by=user_id,
    )
    test_session.add(quotation_model)
    await test_session.flush()

    # Act & Assert
    handler = SupplierQuotationHandler(test_session)
    with pytest.raises(ValueError, match="Cannot transition"):
        await handler.approve_quotation(quotation_model.id, tenant_id)


@pytest.mark.asyncio
async def test_quotation_cannot_transition_after_reject(test_session: AsyncSession):
    """Test rejected quotation cannot transition further."""
    quotation_entity = SupplierQuotation(
        tenant_id=uuid.uuid4(),
        supplier_id=uuid.uuid4(),
        material_id=uuid.uuid4(),
        purchase_order_id=None,
        quoted_price=Decimal("100.00"),
        quantity=Decimal("50"),
        delivery_days=7,
        created_by=uuid.uuid4(),
    )

    # Reject from DRAFT
    quotation_entity.reject()
    assert quotation_entity.status == SupplierQuotationStatus.REJECTED

    # Try to submit a rejected quotation
    with pytest.raises(Exception):  # QuotationRejectedError
        quotation_entity.submit()


# Summary of test coverage:
# - State machine transitions validated
# - Invalid transitions rejected
# - Reject from any state works
# - Handler enforces domain rules
# - Tenant validation works
# - Cannot skip intermediate states
# - Terminal states prevent further transitions
