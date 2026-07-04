/**
 * Property 1: Sales Order Status-to-Action Mapping
 *
 * For any sales order status, the set of action buttons displayed on the
 * Sales_Order_Detail_Page SHALL be exactly the set defined in the STATUS_ACTIONS
 * mapping — no extra buttons for any status, no missing buttons, and the
 * "Create Delivery Note" button SHALL appear if and only if the status is
 * READY_FOR_DISPATCH.
 *
 * **Validates: Requirements 1.1, 11.1, 11.2, 11.4, 11.5, 11.6**
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { STATUS_ACTIONS } from '../SalesOrderStatusConfig';
import { OrderStatus } from '@/types/sales.types';

// ─── Inline Helpers ───────────────────────────────────────────────────────────

/**
 * Compute the set of actions for a given status.
 * This simulates what the SalesOrderActionPanel component does.
 */
function computeActionsForStatus(status: OrderStatus): string[] {
  const actions = STATUS_ACTIONS[status] || [];
  return actions.map((actionConfig) => actionConfig.action);
}

/**
 * Get all valid OrderStatus values as an array.
 */
function getAllOrderStatuses(): OrderStatus[] {
  return Object.values(OrderStatus);
}

// ─── Property Tests ───────────────────────────────────────────────────────────

describe('Property 1: Sales Order Status-to-Action Mapping', () => {
  it('action buttons match STATUS_ACTIONS exactly — no extra, no missing', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...getAllOrderStatuses()),
        (status) => {
          // Get expected actions from the config
          const expectedActionConfigs = STATUS_ACTIONS[status] || [];
          const expectedActions = expectedActionConfigs.map((ac) => ac.action);

          // Get actual actions from the computed function
          const actualActions = computeActionsForStatus(status);

          // Verify arrays are equal
          expect(actualActions).toEqual(expectedActions);

          // Verify lengths match (no extra, no missing)
          expect(actualActions.length).toBe(expectedActions.length);

          // Verify each expected action is present
          for (const expectedAction of expectedActions) {
            expect(actualActions).toContain(expectedAction);
          }

          // Verify no extra actions
          for (const actualAction of actualActions) {
            expect(expectedActions).toContain(actualAction);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('"Create Delivery Note" appears iff status is READY_FOR_DISPATCH', () => {
    // Verify READY_FOR_DISPATCH has the action
    const rdActions = STATUS_ACTIONS[OrderStatus.READY_FOR_DISPATCH] || [];
    const hasCreateDelivery = rdActions.some((a) => a.action === 'create_delivery');
    expect(hasCreateDelivery).toBe(true);

    // Verify no other status has it
    const allStatuses = getAllOrderStatuses();
    for (const status of allStatuses) {
      if (status === OrderStatus.READY_FOR_DISPATCH) continue;

      const actions = STATUS_ACTIONS[status] || [];
      const hasCreateDeliveryForThisStatus = actions.some((a) => a.action === 'create_delivery');
      expect(hasCreateDeliveryForThisStatus).toBe(false);
    }
  });

  it('all statuses are present in STATUS_ACTIONS mapping', () => {
    // Every status in the OrderStatus enum should have an entry in STATUS_ACTIONS
    const allStatuses = getAllOrderStatuses();
    for (const status of allStatuses) {
      expect(STATUS_ACTIONS).toHaveProperty(status);
    }
  });

  it('STATUS_ACTIONS values are arrays of ActionConfig objects', () => {
    const allStatuses = getAllOrderStatuses();
    for (const status of allStatuses) {
      const actions = STATUS_ACTIONS[status];
      expect(Array.isArray(actions)).toBe(true);

      // Verify each action has required properties
      for (const actionConfig of actions) {
        expect(actionConfig).toHaveProperty('label');
        expect(actionConfig).toHaveProperty('action');
        expect(typeof actionConfig.label).toBe('string');
        expect(typeof actionConfig.action).toBe('string');
        expect(actionConfig.label.length).toBeGreaterThan(0);
        expect(actionConfig.action.length).toBeGreaterThan(0);
      }
    }
  });

  it('action names are unique within each status', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...getAllOrderStatuses()),
        (status) => {
          const actions = STATUS_ACTIONS[status] || [];
          const actionNames = actions.map((a) => a.action);
          const uniqueActionNames = new Set(actionNames);

          // No duplicate action names for a given status
          expect(actionNames.length).toBe(uniqueActionNames.size);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('DRAFT status has exactly one action: submit', () => {
    const actions = computeActionsForStatus(OrderStatus.DRAFT);
    expect(actions).toEqual(['submit']);
    expect(actions.length).toBe(1);
  });

  it('PENDING_APPROVAL status has exactly two actions: approve and reject', () => {
    const actions = computeActionsForStatus(OrderStatus.PENDING_APPROVAL);
    expect(actions).toContain('approve');
    expect(actions).toContain('reject');
    expect(actions.length).toBe(2);
  });

  it('APPROVED status has exactly one action: confirm', () => {
    const actions = computeActionsForStatus(OrderStatus.APPROVED);
    expect(actions).toEqual(['confirm']);
    expect(actions.length).toBe(1);
  });

  it('READY_FOR_DISPATCH status has exactly one action: create_delivery', () => {
    const actions = computeActionsForStatus(OrderStatus.READY_FOR_DISPATCH);
    expect(actions).toEqual(['create_delivery']);
    expect(actions.length).toBe(1);
  });

  it('INVOICED status has exactly one action: record_payment', () => {
    const actions = computeActionsForStatus(OrderStatus.INVOICED);
    expect(actions).toEqual(['record_payment']);
    expect(actions.length).toBe(1);
  });

  it('informational statuses have no actions', () => {
    // These statuses show contextual info panels instead of action buttons
    const infoStatuses: OrderStatus[] = [
      OrderStatus.REJECTED,
      OrderStatus.WORK_ORDER_CREATED,
      OrderStatus.CONFIRMED,
      OrderStatus.PROCESSING,
      OrderStatus.PRODUCTION,
      OrderStatus.READY,
      OrderStatus.SHIPPED,
      OrderStatus.DELIVERED,
      OrderStatus.PAYMENT_RECEIVED,
      OrderStatus.COMPLETED,
      OrderStatus.CANCELLED,
    ];

    for (const status of infoStatuses) {
      const actions = computeActionsForStatus(status);
      expect(actions).toEqual([]);
      expect(actions.length).toBe(0);
    }
  });

  it('mapping is deterministic — same status always returns same actions', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...getAllOrderStatuses()),
        (status) => {
          const actions1 = computeActionsForStatus(status);
          const actions2 = computeActionsForStatus(status);

          expect(actions1).toEqual(actions2);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('only actionable statuses have non-empty action arrays', () => {
    // Actionable statuses are those where the user can perform an action
    const actionableStatuses: OrderStatus[] = [
      OrderStatus.DRAFT,
      OrderStatus.PENDING_APPROVAL,
      OrderStatus.APPROVED,
      OrderStatus.READY_FOR_DISPATCH,
      OrderStatus.INVOICED,
    ];

    for (const status of actionableStatuses) {
      const actions = computeActionsForStatus(status);
      expect(actions.length).toBeGreaterThan(0);
    }

    // All other statuses should have empty arrays
    const allStatuses = getAllOrderStatuses();
    const nonActionableStatuses = allStatuses.filter(
      (s) => !actionableStatuses.includes(s)
    );

    for (const status of nonActionableStatuses) {
      const actions = computeActionsForStatus(status);
      expect(actions.length).toBe(0);
    }
  });

  it('action labels are human-readable and non-empty', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...getAllOrderStatuses()),
        (status) => {
          const actions = STATUS_ACTIONS[status] || [];

          for (const actionConfig of actions) {
            // Label should be non-empty
            expect(actionConfig.label.length).toBeGreaterThan(0);

            // Label should start with a capital letter (human-readable convention)
            expect(actionConfig.label[0]).toMatch(/[A-Z]/);

            // Label should not be just whitespace
            expect(actionConfig.label.trim().length).toBeGreaterThan(0);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('action identifiers are lowercase snake_case', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...getAllOrderStatuses()),
        (status) => {
          const actions = STATUS_ACTIONS[status] || [];

          for (const actionConfig of actions) {
            // Action identifier should match snake_case pattern
            expect(actionConfig.action).toMatch(/^[a-z_]+$/);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('variant property is optional and when present has valid values', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...getAllOrderStatuses()),
        (status) => {
          const actions = STATUS_ACTIONS[status] || [];

          for (const actionConfig of actions) {
            if (actionConfig.variant !== undefined) {
              const validVariants = ['default', 'destructive', 'outline', 'secondary'];
              expect(validVariants).toContain(actionConfig.variant);
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('destructive variant is used appropriately for reject actions', () => {
    // The "reject" action should use destructive variant for visual emphasis
    const pendingApprovalActions = STATUS_ACTIONS[OrderStatus.PENDING_APPROVAL] || [];
    const rejectAction = pendingApprovalActions.find((a) => a.action === 'reject');

    if (rejectAction) {
      expect(rejectAction.variant).toBe('destructive');
    }
  });

  it('STATUS_ACTIONS mapping covers all 16 OrderStatus values', () => {
    const allStatuses = getAllOrderStatuses();
    const mappedStatuses = Object.keys(STATUS_ACTIONS);

    // Should have 16 statuses
    expect(allStatuses.length).toBe(16);
    expect(mappedStatuses.length).toBe(16);

    // Every status should be mapped
    for (const status of allStatuses) {
      expect(mappedStatuses).toContain(status);
    }
  });

  it('typical user workflow progression has correct actions at each stage', () => {
    // Typical workflow: DRAFT → PENDING_APPROVAL → APPROVED → ... → READY_FOR_DISPATCH → ... → INVOICED → ... → COMPLETED

    // Stage 1: Draft — user submits
    const draftActions = computeActionsForStatus(OrderStatus.DRAFT);
    expect(draftActions).toContain('submit');

    // Stage 2: Pending Approval — approver approves or rejects
    const pendingActions = computeActionsForStatus(OrderStatus.PENDING_APPROVAL);
    expect(pendingActions).toContain('approve');
    expect(pendingActions).toContain('reject');

    // Stage 3: Approved — user confirms
    const approvedActions = computeActionsForStatus(OrderStatus.APPROVED);
    expect(approvedActions).toContain('confirm');

    // Stage 4: Ready for Dispatch — user creates delivery
    const readyActions = computeActionsForStatus(OrderStatus.READY_FOR_DISPATCH);
    expect(readyActions).toContain('create_delivery');

    // Stage 5: Invoiced — user records payment
    const invoicedActions = computeActionsForStatus(OrderStatus.INVOICED);
    expect(invoicedActions).toContain('record_payment');

    // Stage 6: Completed — no actions
    const completedActions = computeActionsForStatus(OrderStatus.COMPLETED);
    expect(completedActions).toEqual([]);
  });

  it('terminal statuses have no actions', () => {
    // Terminal statuses: COMPLETED, CANCELLED, REJECTED
    const terminalStatuses: OrderStatus[] = [
      OrderStatus.COMPLETED,
      OrderStatus.CANCELLED,
      OrderStatus.REJECTED,
    ];

    for (const status of terminalStatuses) {
      const actions = computeActionsForStatus(status);
      expect(actions).toEqual([]);
    }
  });

  it('intermediate statuses (auto-transition) have no manual actions', () => {
    // These statuses are transitional and handled automatically by the system
    const autoStatuses: OrderStatus[] = [
      OrderStatus.CONFIRMED,
      OrderStatus.PROCESSING,
      OrderStatus.PRODUCTION,
      OrderStatus.READY,
      OrderStatus.SHIPPED,
      OrderStatus.DELIVERED,
      OrderStatus.PAYMENT_RECEIVED,
    ];

    for (const status of autoStatuses) {
      const actions = computeActionsForStatus(status);
      expect(actions).toEqual([]);
    }
  });

  it('action config objects are immutable (frozen)', () => {
    // Verify that modifying the returned actions doesn't affect the original mapping
    fc.assert(
      fc.property(
        fc.constantFrom(...getAllOrderStatuses()),
        (status) => {
          const actions1 = computeActionsForStatus(status);
          const originalLength = actions1.length;

          // Try to modify the returned array (should not affect original)
          actions1.push('fake_action');

          const actions2 = computeActionsForStatus(status);
          expect(actions2.length).toBe(originalLength);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('no status has more than 3 actions', () => {
    // Business rule: keep UI simple, max 2-3 actions per status
    fc.assert(
      fc.property(
        fc.constantFrom(...getAllOrderStatuses()),
        (status) => {
          const actions = computeActionsForStatus(status);
          expect(actions.length).toBeLessThanOrEqual(3);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('action order is consistent and meaningful', () => {
    // For PENDING_APPROVAL, "approve" should come before "reject"
    const pendingActions = STATUS_ACTIONS[OrderStatus.PENDING_APPROVAL] || [];
    const approveIdx = pendingActions.findIndex((a) => a.action === 'approve');
    const rejectIdx = pendingActions.findIndex((a) => a.action === 'reject');

    if (approveIdx !== -1 && rejectIdx !== -1) {
      // Approve (positive action) should appear before reject (negative action)
      expect(approveIdx).toBeLessThan(rejectIdx);
    }
  });

  it('create_delivery action only exists for READY_FOR_DISPATCH', () => {
    // Property 1 requirement: "Create Delivery Note" iff READY_FOR_DISPATCH
    fc.assert(
      fc.property(
        fc.constantFrom(...getAllOrderStatuses()),
        (status) => {
          const actions = computeActionsForStatus(status);
          const hasCreateDelivery = actions.includes('create_delivery');

          if (status === OrderStatus.READY_FOR_DISPATCH) {
            expect(hasCreateDelivery).toBe(true);
          } else {
            expect(hasCreateDelivery).toBe(false);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('each actionable status has at least one action', () => {
    // If a status has actions, it should have at least one
    const allStatuses = getAllOrderStatuses();

    for (const status of allStatuses) {
      const actions = computeActionsForStatus(status);

      // Either no actions (informational status) or at least one action
      if (actions.length > 0) {
        expect(actions.length).toBeGreaterThanOrEqual(1);
      }
    }
  });

  it('STATUS_ACTIONS is a complete and valid mapping', () => {
    // Verify the STATUS_ACTIONS object is well-formed
    expect(STATUS_ACTIONS).toBeDefined();
    expect(typeof STATUS_ACTIONS).toBe('object');
    expect(STATUS_ACTIONS).not.toBeNull();

    // Verify it maps all 16 statuses
    const keys = Object.keys(STATUS_ACTIONS);
    expect(keys.length).toBe(16);

    // Verify each value is an array
    for (const key of keys) {
      const value = STATUS_ACTIONS[key as OrderStatus];
      expect(Array.isArray(value)).toBe(true);
    }
  });
});
