from __future__ import annotations

from backend.app.domain.shared.exceptions.domain_exception import DomainException


class BusinessRuleViolationException(DomainException):
    """
    Raised when a specific business invariant is violated.

    Example:
        raise BusinessRuleViolationException(
            rule="Stock cannot go negative",
            details="Requested 50 units but only 30 available"
        )
    """

    def __init__(self, rule: str, details: str = "") -> None:
        message = rule if not details else f"{rule} — {details}"
        super().__init__(message=message, code="BUSINESS_RULE_VIOLATION")
        self.rule = rule
        self.details = details
