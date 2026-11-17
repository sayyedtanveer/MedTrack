"""
Domain exceptions for procurement pricing.

These exceptions represent business rule violations and are raised by domain entities.
They should be caught in the application layer and converted to HTTP responses.
"""

import uuid

from backend.app.domain.shared.exceptions import (
    DomainException,
    InvalidStateTransitionError,
)


class SupplierPriceAgreementNotFoundError(DomainException):
    """Raised when supplier price agreement does not exist."""

    def __init__(self, agreement_id: uuid.UUID):
        self.agreement_id = agreement_id
        super().__init__(f"Supplier price agreement {agreement_id} not found")


class InvalidAgreementStateTransitionError(InvalidStateTransitionError):
    """Raised when agreement status transition is invalid."""

    def __init__(self, current_status: str, requested_status: str):
        self.current_status = current_status
        self.requested_status = requested_status
        super().__init__(
            f"Cannot transition agreement from {current_status} to {requested_status}"
        )


class AgreementAlreadyActiveError(DomainException):
    """Raised when trying to activate agreement while another is active."""

    def __init__(self, supplier_id: uuid.UUID, material_id: uuid.UUID):
        self.supplier_id = supplier_id
        self.material_id = material_id
        super().__init__(
            f"Active agreement already exists for supplier {supplier_id}, material {material_id}"
        )


class OverlappingSupplierPriceAgreementError(DomainException):
    """Raised when a supplier/material agreement overlaps another agreement."""

    def __init__(self, supplier_id: uuid.UUID, material_id: uuid.UUID):
        self.supplier_id = supplier_id
        self.material_id = material_id
        super().__init__(
            f"Supplier price agreement overlaps an existing agreement for supplier {supplier_id}, material {material_id}"
        )


class CostRevisionNotFoundError(DomainException):
    """Raised when cost revision does not exist."""

    def __init__(self, revision_id: uuid.UUID):
        self.revision_id = revision_id
        super().__init__(f"Cost revision {revision_id} not found")


class CostRevisionAlreadyReviewedError(DomainException):
    """Raised when trying to review already approved/rejected revision."""

    def __init__(self, revision_id: uuid.UUID, current_status: str):
        self.revision_id = revision_id
        self.current_status = current_status
        super().__init__(
            f"Cannot review revision {revision_id}: already {current_status}"
        )


class StaleCostRevisionError(DomainException):
    """Raised when material cost changed after a revision was requested."""

    def __init__(self, revision_id: uuid.UUID):
        self.revision_id = revision_id
        super().__init__(
            f"Cost revision {revision_id} is stale; create a revision against the current cost"
        )


class RequesterCannotApproveOwnRevisionError(DomainException):
    """Raised when requester tries to approve their own cost revision (segregation of duties)."""

    def __init__(self, revision_id: uuid.UUID):
        self.revision_id = revision_id
        super().__init__(
            f"Requester cannot approve their own cost revision (segregation of duties)"
        )


class PriceOverrideRecordNotFoundError(DomainException):
    """Raised when price override record does not exist."""

    def __init__(self, record_id: uuid.UUID):
        self.record_id = record_id
        super().__init__(f"Price override record {record_id} not found")
