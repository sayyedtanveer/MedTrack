from enum import Enum
class ProductStatus(str, Enum):
    """
    Lifecycle states for product templates.
    
    - DRAFT: Initial state, not yet ready for use
    - ACTIVE: Ready for use in BOMs, procurement, sales
    - INACTIVE: No longer in use but history maintained
    - ARCHIVED: Historic records, rarely accessed
    """
    
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"

    @staticmethod
    def can_transition(from_status: "ProductStatus", to_status: "ProductStatus") -> bool:
        """Check if a transition is allowed."""
        if from_status == to_status:
            return True  # No-op transitions are allowed
        return to_status in PRODUCT_STATUS_TRANSITIONS.get(from_status, set())

    @staticmethod
    def validate_transition(from_status: "ProductStatus", to_status: "ProductStatus") -> None:
        """Raise ValueError if transition is not allowed."""
        if not ProductStatus.can_transition(from_status, to_status):
            raise ValueError(
                f"Cannot transition from {from_status.value} to {to_status.value}. "
                f"Valid transitions from {from_status.value}: {', '.join(s.value for s in PRODUCT_STATUS_TRANSITIONS[from_status])}"
            )

    @property
    def is_active_state(self) -> bool:
        """Returns True if product is in ACTIVE state."""
        return self == ProductStatus.ACTIVE

    @property
    def is_usable(self) -> bool:
        """Returns True if product can be used in operations (ACTIVE or DRAFT)."""
        return self in {ProductStatus.ACTIVE, ProductStatus.DRAFT}


# State transition rules live outside the Enum class so Python does not turn the
# mapping itself into an enum member.
PRODUCT_STATUS_TRANSITIONS = {
    ProductStatus.DRAFT: {ProductStatus.ACTIVE, ProductStatus.ARCHIVED},
    ProductStatus.ACTIVE: {ProductStatus.INACTIVE, ProductStatus.ARCHIVED},
    ProductStatus.INACTIVE: {ProductStatus.ACTIVE, ProductStatus.ARCHIVED},
    ProductStatus.ARCHIVED: set(),
}
