"""Shared domain exceptions."""

from backend.app.domain.shared.exceptions.domain_exception import DomainException
from backend.app.domain.shared.exceptions.invalid_state_transition_error import (
    InvalidStateTransitionError,
)

__all__ = [
    "DomainException",
    "InvalidStateTransitionError",
]
