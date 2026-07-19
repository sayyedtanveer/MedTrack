"""
Property tests for Notification Routing Correctness (Property 13).

# Feature: manufacturing-erp-audit, Property 13: Notification Routing Correctness

**Validates: Requirements 23.1–23.10, 27.1–27.6**

Property 13: For any workflow state transition event:
1. Notification type is correct per the NOTIFICATION_ROUTING mapping
2. Target role matches NOTIFICATION_ROUTING exactly
3. deep_link contains the relevant entity ID and follows the correct URL pattern
4. The mapping is deterministic (same event → same notification every time)
"""
from __future__ import annotations

import uuid

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import (
    uuids,
    sampled_from,
    composite,
    text,
    integers,
)

from backend.app.application.notifications.notification_service import (
    NOTIFICATION_ROUTING,
    ALL_NOTIFICATION_TYPES,
    build_deep_link,
    NOTIFICATION_TYPE_SALES_APPROVED,
    NOTIFICATION_TYPE_MATERIAL_SHORTAGE,
    NOTIFICATION_TYPE_QC_FAILED,
    NOTIFICATION_TYPE_FG_RECEIVED,
    NOTIFICATION_TYPE_DISPATCH_COMPLETED,
    NOTIFICATION_TYPE_PAYMENT_RECEIVED,
    NOTIFICATION_TYPE_WO_RELEASED,
    NOTIFICATION_TYPE_MATERIAL_ISSUED,
    NOTIFICATION_TYPE_QC_APPROVED,
    NOTIFICATION_TYPE_ISSUE_MATERIALS_ACTION,
    NOTIFICATION_TYPE_START_PRODUCTION_ACTION,
    NOTIFICATION_TYPE_RECEIVE_FG_ACTION,
    NOTIFICATION_TYPE_READY_FOR_DISPATCH_ACTION,
    NOTIFICATION_TYPE_INVOICE_CREATION_FAILED,
    NOTIFICATION_TYPE_MACHINE_BREAKDOWN,
    NOTIFICATION_TYPE_PROMISE_DATE_AT_RISK,
    NOTIFICATION_TYPE_QC_ESCALATION,
    NOTIFICATION_TYPE_DELIVERY_CANCELLED,
    NOTIFICATION_TYPE_INCOMING_QC_FAILED,
    NOTIFICATION_TYPE_REQUISITION_REJECTED,
    NOTIFICATION_TYPE_PRODUCTION_SCRAP_FAILED,
)


# ─── Expected Mapping: notification_type → (target_role, entity_type) ────────
# This is the ground-truth mapping derived from Requirements 23.1–23.10, 27.1–27.6
# and the design document's notification routing table.

EXPECTED_ROUTING = {
    NOTIFICATION_TYPE_SALES_APPROVED: ("planner", "sales_order"),
    NOTIFICATION_TYPE_MATERIAL_SHORTAGE: ("procurement", "work_order"),
    NOTIFICATION_TYPE_QC_FAILED: ("production_supervisor", "work_order"),
    NOTIFICATION_TYPE_FG_RECEIVED: ("dispatch", "work_order"),
    NOTIFICATION_TYPE_DISPATCH_COMPLETED: ("finance", "delivery"),
    NOTIFICATION_TYPE_PAYMENT_RECEIVED: ("sales", "sales_order"),
    NOTIFICATION_TYPE_WO_RELEASED: ("storekeeper", "work_order"),
    NOTIFICATION_TYPE_MATERIAL_ISSUED: ("operator", "work_order"),
    NOTIFICATION_TYPE_QC_APPROVED: ("storekeeper", "work_order"),
    NOTIFICATION_TYPE_ISSUE_MATERIALS_ACTION: ("storekeeper", "work_order"),
    NOTIFICATION_TYPE_START_PRODUCTION_ACTION: ("operator", "work_order"),
    NOTIFICATION_TYPE_RECEIVE_FG_ACTION: ("storekeeper", "work_order"),
    NOTIFICATION_TYPE_READY_FOR_DISPATCH_ACTION: ("dispatch", "sales_order"),
    NOTIFICATION_TYPE_INVOICE_CREATION_FAILED: ("finance", "sales_order"),
    NOTIFICATION_TYPE_MACHINE_BREAKDOWN: ("maintenance", "work_order"),
    NOTIFICATION_TYPE_PROMISE_DATE_AT_RISK: ("sales", "sales_order"),
    NOTIFICATION_TYPE_QC_ESCALATION: ("quality_manager", "work_order"),
    NOTIFICATION_TYPE_DELIVERY_CANCELLED: ("sales", "delivery"),
    NOTIFICATION_TYPE_INCOMING_QC_FAILED: ("procurement", "purchase_order"),
    NOTIFICATION_TYPE_REQUISITION_REJECTED: ("planner", "purchase_requisition"),
    NOTIFICATION_TYPE_PRODUCTION_SCRAP_FAILED: ("sales", "work_order"),
}

# deep_link URL pattern expectations per entity_type
EXPECTED_DEEP_LINK_PATTERNS = {
    "sales_order": "/sales/orders/",
    "work_order": "/manufacturing/work-orders/",
    "delivery": "/delivery/deliveries/",
    "invoice": "/finance/invoices/",
    "purchase_requisition": "/procurement/requisitions/",
    "purchase_order": "/procurement/purchase-orders/",
    "material": "/inventory/materials/",
}


# ─── Strategies ──────────────────────────────────────────────────────────────

@composite
def workflow_state_transition_event(draw):
    """
    Generate a random workflow state transition event.

    Each event consists of:
    - notification_type: one of the 21 defined types
    - entity_id: a random UUID representing the entity
    - entity_type: the reference_type for this notification (derived from expected mapping)
    """
    notification_type = draw(sampled_from(ALL_NOTIFICATION_TYPES))
    entity_id = draw(uuids())
    expected_role, expected_entity_type = EXPECTED_ROUTING[notification_type]

    return {
        "notification_type": notification_type,
        "entity_id": entity_id,
        "entity_type": expected_entity_type,
        "expected_role": expected_role,
    }


@composite
def entity_type_and_id(draw):
    """Generate a random entity_type + entity_id pair for deep_link testing."""
    entity_type = draw(sampled_from(list(EXPECTED_DEEP_LINK_PATTERNS.keys())))
    entity_id = draw(uuids())
    return entity_type, entity_id


# ─────────────────────────────────────────────────────────────────────────────
# Property 13: Notification Routing Correctness
#
# For any workflow state transition event:
# (a) notification type is correct per mapping
# (b) target role matches NOTIFICATION_ROUTING exactly
# (c) deep_link contains the relevant entity ID and follows URL pattern
# (d) the mapping is deterministic (same event → same notification every time)
# ─────────────────────────────────────────────────────────────────────────────


class TestNotificationRoutingTargetRole:
    """**Validates: Requirements 23.1–23.10, 27.1–27.6**

    Property 13a/b: For any notification type, the target role resolved from
    NOTIFICATION_ROUTING is exactly the expected role per the requirements.
    """

    @given(event=workflow_state_transition_event())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_target_role_matches_routing_table(self, event: dict):
        """Property 13b: Target role matches NOTIFICATION_ROUTING exactly for all types.

        **Validates: Requirements 23.1–23.10, 27.1–27.6**
        """
        notification_type = event["notification_type"]
        expected_role = event["expected_role"]

        # Look up role from the NOTIFICATION_ROUTING dict
        actual_role = NOTIFICATION_ROUTING.get(notification_type)

        assert actual_role == expected_role, (
            f"Routing mismatch for type '{notification_type}': "
            f"expected role='{expected_role}', got='{actual_role}'"
        )

    @given(event=workflow_state_transition_event())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_all_notification_types_have_routing_entry(self, event: dict):
        """Property 13a: Every notification type has a defined routing entry.

        **Validates: Requirements 23.1–23.10, 27.1–27.6**
        """
        notification_type = event["notification_type"]

        assert notification_type in NOTIFICATION_ROUTING, (
            f"Notification type '{notification_type}' has no entry in NOTIFICATION_ROUTING"
        )
        assert NOTIFICATION_ROUTING[notification_type] is not None, (
            f"Notification type '{notification_type}' has None target_role"
        )


class TestNotificationDeepLinkCorrectness:
    """**Validates: Requirements 23.10, 27.1–27.4**

    Property 13c: deep_link contains the entity ID and follows the correct URL pattern.
    """

    @given(data=entity_type_and_id())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_deep_link_contains_entity_id(self, data: tuple):
        """Property 13c: deep_link URL contains the relevant entity ID.

        **Validates: Requirements 23.10, 27.1–27.4**
        """
        entity_type, entity_id = data
        entity_id_str = str(entity_id)

        deep_link = build_deep_link(entity_type, entity_id_str)

        assert entity_id_str in deep_link, (
            f"deep_link does not contain entity_id: "
            f"entity_type='{entity_type}', entity_id='{entity_id_str}', "
            f"deep_link='{deep_link}'"
        )

    @given(data=entity_type_and_id())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_deep_link_follows_correct_url_pattern(self, data: tuple):
        """Property 13c: deep_link follows the correct URL pattern for entity_type.

        **Validates: Requirements 23.10, 27.1–27.4**
        """
        entity_type, entity_id = data
        entity_id_str = str(entity_id)

        deep_link = build_deep_link(entity_type, entity_id_str)
        expected_prefix = EXPECTED_DEEP_LINK_PATTERNS[entity_type]

        assert deep_link.startswith(expected_prefix), (
            f"deep_link URL pattern mismatch: "
            f"entity_type='{entity_type}', expected prefix='{expected_prefix}', "
            f"got='{deep_link}'"
        )

    @given(data=entity_type_and_id())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_deep_link_is_exact_route(self, data: tuple):
        """Property 13c: deep_link is exactly prefix + entity_id (no extraneous content).

        **Validates: Requirements 23.10**
        """
        entity_type, entity_id = data
        entity_id_str = str(entity_id)

        deep_link = build_deep_link(entity_type, entity_id_str)
        expected_prefix = EXPECTED_DEEP_LINK_PATTERNS[entity_type]
        expected_link = f"{expected_prefix}{entity_id_str}"

        assert deep_link == expected_link, (
            f"deep_link not exact: entity_type='{entity_type}', "
            f"expected='{expected_link}', got='{deep_link}'"
        )


class TestNotificationRoutingDeterminism:
    """**Validates: Requirements 23.1–23.10, 27.1–27.6**

    Property 13d: The mapping is deterministic — same event always produces
    the same notification type, target role, and deep_link.
    """

    @given(event=workflow_state_transition_event())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_routing_is_deterministic(self, event: dict):
        """Property 13d: Same notification_type always resolves to the same target_role.

        **Validates: Requirements 23.1–23.10, 27.1–27.6**
        """
        notification_type = event["notification_type"]

        # Call routing resolution multiple times
        role_1 = NOTIFICATION_ROUTING[notification_type]
        role_2 = NOTIFICATION_ROUTING[notification_type]
        role_3 = NOTIFICATION_ROUTING[notification_type]

        assert role_1 == role_2 == role_3, (
            f"Non-deterministic routing for '{notification_type}': "
            f"got {role_1}, {role_2}, {role_3}"
        )

    @given(event=workflow_state_transition_event())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_deep_link_generation_is_deterministic(self, event: dict):
        """Property 13d: Same entity_type + entity_id always produces the same deep_link.

        **Validates: Requirements 23.10, 27.1–27.4**
        """
        entity_type = event["entity_type"]
        entity_id_str = str(event["entity_id"])

        # Generate deep_link multiple times
        link_1 = build_deep_link(entity_type, entity_id_str)
        link_2 = build_deep_link(entity_type, entity_id_str)
        link_3 = build_deep_link(entity_type, entity_id_str)

        assert link_1 == link_2 == link_3, (
            f"Non-deterministic deep_link for entity_type='{entity_type}', "
            f"entity_id='{entity_id_str}': got '{link_1}', '{link_2}', '{link_3}'"
        )

    @given(event=workflow_state_transition_event())
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_full_routing_tuple_is_deterministic(self, event: dict):
        """Property 13d: The full routing tuple (type, role, deep_link) is deterministic.

        **Validates: Requirements 23.1–23.10, 27.1–27.6**
        """
        notification_type = event["notification_type"]
        entity_type = event["entity_type"]
        entity_id_str = str(event["entity_id"])

        # Resolve full tuple twice
        tuple_1 = (
            notification_type,
            NOTIFICATION_ROUTING[notification_type],
            build_deep_link(entity_type, entity_id_str),
        )
        tuple_2 = (
            notification_type,
            NOTIFICATION_ROUTING[notification_type],
            build_deep_link(entity_type, entity_id_str),
        )

        assert tuple_1 == tuple_2, (
            f"Non-deterministic full routing: first={tuple_1}, second={tuple_2}"
        )


class TestNotificationRoutingCompleteness:
    """**Validates: Requirements 23.1–23.10, 27.1–27.6**

    Verify the routing table is complete and consistent with requirements.
    """

    def test_all_21_notification_types_in_routing(self):
        """Property 13: All 21 defined notification types are in the routing table.

        **Validates: Requirements 23.1–23.10, 27.1–27.6**
        """
        assert len(NOTIFICATION_ROUTING) == 21, (
            f"Expected 21 notification types in routing, got {len(NOTIFICATION_ROUTING)}"
        )

    def test_all_notification_types_list_matches_routing_keys(self):
        """Property 13: ALL_NOTIFICATION_TYPES matches NOTIFICATION_ROUTING keys exactly.

        **Validates: Requirements 23.1–23.10, 27.1–27.6**
        """
        routing_keys = set(NOTIFICATION_ROUTING.keys())
        all_types_set = set(ALL_NOTIFICATION_TYPES)

        assert routing_keys == all_types_set, (
            f"Mismatch between ALL_NOTIFICATION_TYPES and NOTIFICATION_ROUTING keys. "
            f"In routing but not list: {routing_keys - all_types_set}. "
            f"In list but not routing: {all_types_set - routing_keys}."
        )

    def test_expected_routing_matches_implementation(self):
        """Property 13: Expected routing (from requirements) matches actual implementation.

        **Validates: Requirements 23.1–23.10, 27.1–27.6**
        """
        for notification_type, (expected_role, _) in EXPECTED_ROUTING.items():
            actual_role = NOTIFICATION_ROUTING.get(notification_type)
            assert actual_role == expected_role, (
                f"Routing mismatch for '{notification_type}': "
                f"requirements say role='{expected_role}', "
                f"implementation has role='{actual_role}'"
            )

    def test_no_duplicate_routing_entries(self):
        """Property 13: No notification type is mapped to multiple different roles.

        **Validates: Requirements 23.1–23.10**
        """
        # Since NOTIFICATION_ROUTING is a dict, keys are unique by nature,
        # but verify no None values slipped in
        for ntype, role in NOTIFICATION_ROUTING.items():
            assert role is not None, f"Notification type '{ntype}' has None role"
            assert isinstance(role, str), f"Notification type '{ntype}' has non-string role: {role}"
            assert len(role) > 0, f"Notification type '{ntype}' has empty role string"

    @given(notification_type=sampled_from(ALL_NOTIFICATION_TYPES))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_routing_role_is_valid_known_role(self, notification_type: str):
        """Property 13: Every routed role is one of the known operational roles.

        **Validates: Requirements 23.1–23.10, 27.1–27.6**
        """
        known_roles = {
            "planner",
            "procurement",
            "production_supervisor",
            "dispatch",
            "finance",
            "sales",
            "storekeeper",
            "operator",
            "maintenance",
            "quality_manager",
        }

        role = NOTIFICATION_ROUTING[notification_type]
        assert role in known_roles, (
            f"Notification type '{notification_type}' routes to unknown role '{role}'. "
            f"Known roles: {known_roles}"
        )


class TestDeepLinkEdgeCases:
    """Edge cases for deep_link generation.

    **Validates: Requirements 23.10**
    """

    def test_unknown_entity_type_uses_fallback_pattern(self):
        """Property 13c edge case: Unknown entity_type uses fallback /{type}/{id} pattern.

        **Validates: Requirements 23.10**
        """
        entity_id = str(uuid.uuid4())
        deep_link = build_deep_link("unknown_entity", entity_id)

        assert deep_link == f"/unknown_entity/{entity_id}", (
            f"Expected fallback pattern for unknown entity_type, got '{deep_link}'"
        )

    @given(entity_id=uuids())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_deep_link_starts_with_slash(self, entity_id: uuid.UUID):
        """Property 13c: All deep_links start with a forward slash (valid route).

        **Validates: Requirements 23.10**
        """
        for entity_type in EXPECTED_DEEP_LINK_PATTERNS:
            deep_link = build_deep_link(entity_type, str(entity_id))
            assert deep_link.startswith("/"), (
                f"deep_link doesn't start with '/': entity_type='{entity_type}', "
                f"deep_link='{deep_link}'"
            )
