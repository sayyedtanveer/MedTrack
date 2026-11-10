"""Domain exceptions for Sales module."""

from __future__ import annotations

from uuid import UUID

from backend.app.domain.shared.exceptions.domain_exception import DomainException


class PriceListNotFoundError(DomainException):
    """Raised when a price list is not found for a tenant."""

    def __init__(self, price_list_id: UUID) -> None:
        super().__init__(f"Price list '{price_list_id}' not found.", code="PRICE_LIST_NOT_FOUND")
        self.price_list_id = price_list_id


class ProductNotFoundError(DomainException):
    """Raised when a product or variant is not found for the calling tenant."""

    def __init__(self, product_id: UUID) -> None:
        # Strictly generic message — never disclose cross-tenant existence
        super().__init__(f"Product '{product_id}' not found.", code="PRODUCT_NOT_FOUND")
        self.product_id = product_id


class ProductInactiveError(DomainException):
    """Raised when an inactive product is added to a price list."""

    def __init__(self, code: str) -> None:
        super().__init__(f"Product '{code}' is inactive and cannot be added to a price list.", code="PRODUCT_INACTIVE")
        self.product_code = code


class InvalidProductTypeError(DomainException):
    """Raised when a product type invariant is violated (e.g. raw material as finished product)."""

    def __init__(self, code: str, actual_type: str) -> None:
        super().__init__(
            f"Material '{code}' is a '{actual_type}' material, not a finished product.",
            code="INVALID_PRODUCT_TYPE",
        )
        self.product_code = code
        self.actual_type = actual_type


class DuplicatePriceListLineError(DomainException):
    """Raised when adding a duplicate line to a price list."""

    def __init__(self, product_id: UUID, product_type: str) -> None:
        super().__init__(
            f"Product '{product_id}' ({product_type}) already exists in this price list.",
            code="DUPLICATE_PRICE_LIST_LINE",
        )
        self.product_id = product_id
        self.product_type = product_type


class AmbiguousLineDeletionError(DomainException):
    """Raised when a legacy line deletion request matches multiple lines with different types."""

    def __init__(self, product_id: UUID) -> None:
        super().__init__(
            f"Multiple lines match product '{product_id}'. Please specify 'product_type' to remove unambiguously.",
            code="AMBIGUOUS_LINE_DELETION",
        )
        self.product_id = product_id
