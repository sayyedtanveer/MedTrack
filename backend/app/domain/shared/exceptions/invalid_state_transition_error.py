"""
Invalid state transition exception (DDD).

Raised when an entity cannot transition to the requested state.
"""

from backend.app.domain.shared.exceptions.domain_exception import DomainException


class InvalidStateTransitionError(DomainException):
    """Raised when an entity state transition is invalid."""

    def __init__(self, current_state: str, requested_state: str):
        self.current_state = current_state
        self.requested_state = requested_state
        super().__init__(
            f"Cannot transition from {current_state} to {requested_state}",
            code="INVALID_STATE_TRANSITION",
        )
