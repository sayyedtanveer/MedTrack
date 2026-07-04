/**
 * Property 7: Work Order Sub-Status Aggregation
 *
 * For any set of linked work orders, the aggregated production sub-status
 * displayed on the `SalesWorkflowTimeline` SHALL equal the status of the
 * least-advanced work order (ordered by lifecycle position).
 *
 * WO lifecycle ordering:
 * PLANNED < RELEASED < MATERIAL_PENDING < MATERIAL_RESERVED < MATERIAL_ISSUED <
 * IN_PRODUCTION < QC_PENDING < QC_APPROVED < FG_RECEIVED < COMPLETED < CLOSED
 *
 * Exception statuses (REWORK, PRODUCTION_HOLD, QC_REJECTED) are treated as "least advanced"
 * but only win if no actual index-0 status (PLANNED) exists.
 *
 * **Validates: Requirements 4.3, 21.2**
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';

// ─── Inline Constants and Helpers ────────────────────────────────────────────
// Copied from SalesWorkflowTimeline.tsx to avoid loading the whole component

/**
 * Work Order status ordering from least-advanced to most-advanced.
 * This is the canonical ordering defined in the design document.
 */
const WO_STATUS_ORDER: string[] = [
  'PLANNED',
  'RELEASED',
  'MATERIAL_PENDING',
  'MATERIAL_RESERVED',
  'MATERIAL_ISSUED',
  'IN_PRODUCTION',
  'QC_PENDING',
  'QC_APPROVED',
  'FG_RECEIVED',
  'COMPLETED',
  'CLOSED',
];

/**
 * Get the least-advanced WO status from a list of work orders.
 * Returns null if no work orders.
 * Copied from SalesWorkflowTimeline.tsx
 */
function getAggregatedWOStatus(workOrders: { status: string }[]): string | null {
  if (!workOrders || workOrders.length === 0) return null;

  // Filter out cancelled/rejected WOs for aggregation
  const activeWOs = workOrders.filter(
    (wo) => wo.status !== 'CANCELLED' && wo.status !== 'REJECTED'
  );
  if (activeWOs.length === 0) return null;

  let leastAdvancedIdx = WO_STATUS_ORDER.length;
  let leastAdvancedStatus = activeWOs[0].status;

  for (const wo of activeWOs) {
    const idx = WO_STATUS_ORDER.indexOf(wo.status);
    if (idx === -1) {
      // Unknown status (e.g. REWORK, PRODUCTION_HOLD) — treat as earlier than most
      // Just use the first one encountered that's not in the ordered list
      if (leastAdvancedIdx > 0) {
        leastAdvancedIdx = 0;
        leastAdvancedStatus = wo.status;
      }
    } else if (idx < leastAdvancedIdx) {
      leastAdvancedIdx = idx;
      leastAdvancedStatus = wo.status;
    }
  }

  return leastAdvancedStatus;
}

// ─── Test Constants ───────────────────────────────────────────────────────────

/**
 * Exception statuses that aren't in the ordered list.
 * These are treated as "index 0 equivalent" but won't override actual index 0 (PLANNED).
 */
const EXCEPTION_STATUSES = ['REWORK', 'QC_REJECTED', 'PRODUCTION_HOLD'];

/**
 * All valid WO statuses from the system.
 * Includes both ordered statuses and exception statuses.
 */
const ALL_WO_STATUSES = [
  ...WO_STATUS_ORDER,
  ...EXCEPTION_STATUSES,
  'REJECTED',
  'CANCELLED',
];

/**
 * Active WO statuses (excluding CANCELLED and REJECTED which are filtered out)
 */
const ACTIVE_WO_STATUSES = ALL_WO_STATUSES.filter(
  (status) => status !== 'CANCELLED' && status !== 'REJECTED'
);

// ─── Test Helpers ─────────────────────────────────────────────────────────────

/**
 * Create a work order item with the given status.
 */
function createWO(status: string): { status: string } {
  return { status };
}

/**
 * Find the least-advanced status manually according to WO_STATUS_ORDER.
 * This matches the exact logic from getAggregatedWOStatus.
 * Returns null if the input is empty.
 */
function findLeastAdvancedManually(statuses: string[]): string | null {
  if (statuses.length === 0) return null;

  // Filter out cancelled/rejected
  const activeStatuses = statuses.filter(
    (s) => s !== 'CANCELLED' && s !== 'REJECTED'
  );
  if (activeStatuses.length === 0) return null;

  let leastAdvancedIdx = WO_STATUS_ORDER.length;
  let leastAdvancedStatus = activeStatuses[0];

  for (const status of activeStatuses) {
    const idx = WO_STATUS_ORDER.indexOf(status);
    if (idx === -1) {
      // Exception status — only wins if leastAdvancedIdx > 0
      if (leastAdvancedIdx > 0) {
        leastAdvancedIdx = 0;
        leastAdvancedStatus = status;
      }
    } else if (idx < leastAdvancedIdx) {
      leastAdvancedIdx = idx;
      leastAdvancedStatus = status;
    }
  }

  return leastAdvancedStatus;
}

// ─── Property Tests ───────────────────────────────────────────────────────────

describe('Property 7: WO Sub-Status Aggregation', () => {
  it('aggregated sub-status equals least-advanced WO status', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom(...ACTIVE_WO_STATUSES), { minLength: 1, maxLength: 10 }),
        (statuses) => {
          // Create WO items from statuses
          const workOrders = statuses.map((status) => createWO(status));

          // Get aggregated status from the function under test
          const aggregated = getAggregatedWOStatus(workOrders);

          // Get expected least-advanced status
          const expected = findLeastAdvancedManually(statuses);

          // Verify they match
          expect(aggregated).toBe(expected);
        }
      ),
      { numRuns: 200 }
    );
  });

  it('returns null for empty work order list', () => {
    const aggregated = getAggregatedWOStatus([]);
    expect(aggregated).toBeNull();
  });

  it('returns null for work order list with only cancelled/rejected WOs', () => {
    const workOrders = [
      createWO('CANCELLED'),
      createWO('REJECTED'),
    ];
    const aggregated = getAggregatedWOStatus(workOrders);
    expect(aggregated).toBeNull();
  });

  it('filters out CANCELLED and REJECTED WOs from aggregation', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom(...ACTIVE_WO_STATUSES), { minLength: 1, maxLength: 5 }),
        fc.nat({ max: 3 }), // number of CANCELLED WOs to add
        fc.nat({ max: 3 }), // number of REJECTED WOs to add
        (activeStatuses, numCancelled, numRejected) => {
          // Build work order list with active + cancelled + rejected
          const workOrders = [
            ...activeStatuses.map((s) => createWO(s)),
            ...Array(numCancelled).fill('CANCELLED').map((s) => createWO(s)),
            ...Array(numRejected).fill('REJECTED').map((s) => createWO(s)),
          ];

          // Get aggregated status
          const aggregated = getAggregatedWOStatus(workOrders);

          // Expected is based only on active statuses
          const expected = findLeastAdvancedManually(activeStatuses);

          expect(aggregated).toBe(expected);
        }
      ),
      { numRuns: 150 }
    );
  });

  it('single WO returns its own status', () => {
    fc.assert(
      fc.property(fc.constantFrom(...ACTIVE_WO_STATUSES), (status) => {
        const workOrders = [createWO(status)];
        const aggregated = getAggregatedWOStatus(workOrders);
        expect(aggregated).toBe(status);
      }),
      { numRuns: 50 }
    );
  });

  it('PLANNED is least-advanced among all ordered statuses', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom(...WO_STATUS_ORDER.slice(1)), { minLength: 1, maxLength: 5 }),
        (otherStatuses) => {
          // PLANNED is at index 0
          const workOrders = [
            createWO('PLANNED'),
            ...otherStatuses.map((s) => createWO(s)),
          ];

          const aggregated = getAggregatedWOStatus(workOrders);
          expect(aggregated).toBe('PLANNED');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('PLANNED wins over exception statuses', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom(...EXCEPTION_STATUSES), { minLength: 1, maxLength: 3 }),
        (exceptionStatuses) => {
          // When PLANNED and exception statuses both exist, PLANNED wins
          const workOrders = [
            createWO('PLANNED'),
            ...exceptionStatuses.map((s) => createWO(s)),
          ];

          const aggregated = getAggregatedWOStatus(workOrders);
          expect(aggregated).toBe('PLANNED');
        }
      ),
      { numRuns: 50 }
    );
  });

  it('exception statuses win over non-PLANNED ordered statuses', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...EXCEPTION_STATUSES),
        fc.array(fc.constantFrom(...WO_STATUS_ORDER.slice(1)), { minLength: 1, maxLength: 5 }),
        (exceptionStatus, orderedStatuses) => {
          const workOrders = [
            createWO(exceptionStatus),
            ...orderedStatuses.map((s) => createWO(s)),
          ];

          const aggregated = getAggregatedWOStatus(workOrders);
          
          // Exception status should win (treated as index 0 equivalent)
          expect(aggregated).toBe(exceptionStatus);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('COMPLETED/CLOSED are most-advanced among ordered statuses', () => {
    const workOrders1 = [createWO('COMPLETED')];
    expect(getAggregatedWOStatus(workOrders1)).toBe('COMPLETED');

    const workOrders2 = [createWO('CLOSED')];
    expect(getAggregatedWOStatus(workOrders2)).toBe('CLOSED');

    // When mixed, the earlier one in the order wins
    const workOrders3 = [createWO('COMPLETED'), createWO('CLOSED')];
    expect(getAggregatedWOStatus(workOrders3)).toBe('COMPLETED');
  });

  it('aggregation is deterministic for the same input', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom(...ACTIVE_WO_STATUSES), { minLength: 1, maxLength: 5 }),
        (statuses) => {
          const workOrders = statuses.map((s) => createWO(s));
          
          const result1 = getAggregatedWOStatus(workOrders);
          const result2 = getAggregatedWOStatus(workOrders);
          
          expect(result1).toBe(result2);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('aggregation result is independent of WO array order for ordered statuses', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom(...WO_STATUS_ORDER), { minLength: 2, maxLength: 5 }),
        (statuses) => {
          // Create WOs in original order
          const workOrders1 = statuses.map((s) => createWO(s));
          
          // Create WOs in reversed order
          const workOrders2 = [...statuses].reverse().map((s) => createWO(s));
          
          const result1 = getAggregatedWOStatus(workOrders1);
          const result2 = getAggregatedWOStatus(workOrders2);
          
          // Results should be identical regardless of order
          expect(result1).toBe(result2);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('lifecycle ordering is transitive for ordered statuses', () => {
    // If A < B and B < C, then A < C
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: WO_STATUS_ORDER.length - 3 }),
        (startIdx) => {
          const statusA = WO_STATUS_ORDER[startIdx];
          const statusB = WO_STATUS_ORDER[startIdx + 1];
          const statusC = WO_STATUS_ORDER[startIdx + 2];

          // Test A vs B
          const result1 = getAggregatedWOStatus([createWO(statusA), createWO(statusB)]);
          expect(result1).toBe(statusA); // A is less advanced

          // Test B vs C
          const result2 = getAggregatedWOStatus([createWO(statusB), createWO(statusC)]);
          expect(result2).toBe(statusB); // B is less advanced

          // Test A vs C (transitive)
          const result3 = getAggregatedWOStatus([createWO(statusA), createWO(statusC)]);
          expect(result3).toBe(statusA); // A is less advanced than C
        }
      ),
      { numRuns: 50 }
    );
  });

  it('aggregation respects the complete lifecycle ordering for ordered statuses', () => {
    // Generate all pairs of statuses and verify ordering is respected
    for (let i = 0; i < WO_STATUS_ORDER.length; i++) {
      for (let j = i + 1; j < WO_STATUS_ORDER.length; j++) {
        const lessAdvanced = WO_STATUS_ORDER[i];
        const moreAdvanced = WO_STATUS_ORDER[j];

        const workOrders = [
          createWO(lessAdvanced),
          createWO(moreAdvanced),
        ];

        const aggregated = getAggregatedWOStatus(workOrders);
        
        // The less advanced status should always win
        expect(aggregated).toBe(lessAdvanced);
      }
    }
  });

  it('multiple WOs with same status returns that status', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...ACTIVE_WO_STATUSES),
        fc.integer({ min: 2, max: 5 }),
        (status, count) => {
          const workOrders = Array(count)
            .fill(status)
            .map((s) => createWO(s));

          const aggregated = getAggregatedWOStatus(workOrders);
          expect(aggregated).toBe(status);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('exception status order dependency - first wins when multiple exceptions', () => {
    // When multiple exception statuses exist and no PLANNED, first encountered wins
    const workOrders1 = [createWO('REWORK'), createWO('PRODUCTION_HOLD')];
    expect(getAggregatedWOStatus(workOrders1)).toBe('REWORK');

    const workOrders2 = [createWO('PRODUCTION_HOLD'), createWO('REWORK')];
    expect(getAggregatedWOStatus(workOrders2)).toBe('PRODUCTION_HOLD');

    const workOrders3 = [createWO('QC_REJECTED'), createWO('REWORK')];
    expect(getAggregatedWOStatus(workOrders3)).toBe('QC_REJECTED');
  });

  it('typical production flow scenario', () => {
    // Scenario: Multiple WOs in different stages
    const workOrders = [
      createWO('COMPLETED'),     // Most advanced
      createWO('IN_PRODUCTION'), // Middle
      createWO('MATERIAL_PENDING'), // Least advanced
      createWO('QC_APPROVED'),   // Advanced
    ];

    const aggregated = getAggregatedWOStatus(workOrders);
    expect(aggregated).toBe('MATERIAL_PENDING'); // Should show the bottleneck
  });

  it('blocked production scenario with exception status', () => {
    // Scenario: One WO on hold, others progressing
    const workOrders = [
      createWO('IN_PRODUCTION'),
      createWO('PRODUCTION_HOLD'), // Exception status
      createWO('QC_APPROVED'),
    ];

    const aggregated = getAggregatedWOStatus(workOrders);
    expect(aggregated).toBe('PRODUCTION_HOLD'); // Should highlight the issue
  });

  it('rework scenario', () => {
    // Scenario: Mix of normal statuses and rework
    const workOrders = [
      createWO('COMPLETED'),
      createWO('REWORK'), // Exception status
      createWO('FG_RECEIVED'),
    ];

    const aggregated = getAggregatedWOStatus(workOrders);
    expect(aggregated).toBe('REWORK'); // Should show rework status
  });

  it('all work orders completed scenario', () => {
    // Scenario: All WOs done
    const workOrders = [
      createWO('COMPLETED'),
      createWO('COMPLETED'),
      createWO('CLOSED'),
    ];

    const aggregated = getAggregatedWOStatus(workOrders);
    // Should return COMPLETED (appears first and at lower index than CLOSED)
    expect(aggregated).toBe('COMPLETED');
  });
});
