/**
 * Property 22: Rework Count Derivation
 *
 * For any work order, the displayed rework count SHALL equal the number
 * of audit_log entries with action_type "qc_rework" (or equivalent) for
 * that work_order_id, capped at a display maximum of 99.
 *
 * **Validates: Requirements 12.4, 12.6**
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';

// ─── Types ────────────────────────────────────────────────────────────────────

interface AuditLogEntry {
  id: string;
  action_type: string;
  entity_type: string;
  entity_id: string;
  timestamp: string;
}

// ─── Business Logic Functions ─────────────────────────────────────────────────

/**
 * Count the number of rework actions from audit logs.
 * Returns the count of entries with action_type "qc_rework", capped at 99.
 */
function countReworkFromAuditLogs(
  workOrderId: string,
  auditLogs: AuditLogEntry[]
): number {
  // Filter audit logs for this work order with qc_rework action
  const reworkEntries = auditLogs.filter(
    (log) =>
      log.entity_type === 'work_order' &&
      log.entity_id === workOrderId &&
      log.action_type === 'qc_rework'
  );

  // Cap at 99 for display
  const count = reworkEntries.length;
  return Math.min(count, 99);
}

/**
 * Determine if rework warning should be shown (10+ reworks).
 */
function shouldShowReworkWarning(reworkCount: number): boolean {
  return reworkCount >= 10;
}

// ─── Test Helpers ─────────────────────────────────────────────────────────────

/**
 * Create a mock audit log entry.
 */
function createAuditLog(
  actionType: string,
  entityType: string,
  entityId: string,
  timestamp?: string
): AuditLogEntry {
  return {
    id: `log-${Math.random().toString(36).substring(7)}`,
    action_type: actionType,
    entity_type: entityType,
    entity_id: entityId,
    timestamp: timestamp || new Date().toISOString(),
  };
}

/**
 * Create N rework audit log entries for a work order.
 */
function createReworkLogs(workOrderId: string, count: number): AuditLogEntry[] {
  return Array.from({ length: count }, (_, i) =>
    createAuditLog('qc_rework', 'work_order', workOrderId, new Date(Date.now() + i * 1000).toISOString())
  );
}

// ─── Property Tests ───────────────────────────────────────────────────────────

describe('Property 22: Rework Count Derivation', () => {
  it('rework count equals number of qc_rework audit entries', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 50 }), // rework count within reasonable range
        (reworkCount) => {
          const workOrderId = 'wo-123';
          const auditLogs = createReworkLogs(workOrderId, reworkCount);

          const count = countReworkFromAuditLogs(workOrderId, auditLogs);

          expect(count).toBe(reworkCount);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('rework count is capped at 99 for display', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 100, max: 500 }), // excessive rework counts
        (reworkCount) => {
          const workOrderId = 'wo-456';
          const auditLogs = createReworkLogs(workOrderId, reworkCount);

          const count = countReworkFromAuditLogs(workOrderId, auditLogs);

          // Should be capped at 99
          expect(count).toBe(99);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('boundary case - exactly 99 reworks', () => {
    const workOrderId = 'wo-boundary';
    const auditLogs = createReworkLogs(workOrderId, 99);

    const count = countReworkFromAuditLogs(workOrderId, auditLogs);

    expect(count).toBe(99);
  });

  it('boundary case - exactly 100 reworks capped to 99', () => {
    const workOrderId = 'wo-boundary-100';
    const auditLogs = createReworkLogs(workOrderId, 100);

    const count = countReworkFromAuditLogs(workOrderId, auditLogs);

    expect(count).toBe(99);
  });

  it('zero rework entries returns zero count', () => {
    const workOrderId = 'wo-zero';
    const auditLogs: AuditLogEntry[] = [];

    const count = countReworkFromAuditLogs(workOrderId, auditLogs);

    expect(count).toBe(0);
  });

  it('filters out non-rework audit entries', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 20 }),
        fc.integer({ min: 1, max: 20 }),
        (reworkCount, otherCount) => {
          const workOrderId = 'wo-filter';

          // Create rework logs
          const reworkLogs = createReworkLogs(workOrderId, reworkCount);

          // Create other action type logs
          const otherLogs = Array.from({ length: otherCount }, () =>
            createAuditLog('qc_approve', 'work_order', workOrderId)
          );

          const allLogs = [...reworkLogs, ...otherLogs];

          const count = countReworkFromAuditLogs(workOrderId, allLogs);

          // Should only count rework entries
          expect(count).toBe(Math.min(reworkCount, 99));
        }
      ),
      { numRuns: 100 }
    );
  });

  it('filters by work order ID - ignores other work orders', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 20 }),
        fc.integer({ min: 1, max: 20 }),
        (targetCount, otherCount) => {
          const targetWorkOrderId = 'wo-target';
          const otherWorkOrderId = 'wo-other';

          // Create rework logs for target WO
          const targetLogs = createReworkLogs(targetWorkOrderId, targetCount);

          // Create rework logs for other WO
          const otherLogs = createReworkLogs(otherWorkOrderId, otherCount);

          const allLogs = [...targetLogs, ...otherLogs];

          const count = countReworkFromAuditLogs(targetWorkOrderId, allLogs);

          // Should only count target WO entries
          expect(count).toBe(Math.min(targetCount, 99));
        }
      ),
      { numRuns: 100 }
    );
  });

  it('filters by entity type - ignores non-work-order entities', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 20 }),
        fc.integer({ min: 1, max: 20 }),
        (woReworkCount, soReworkCount) => {
          const entityId = 'entity-123';

          // Create rework logs for work_order
          const woLogs = Array.from({ length: woReworkCount }, () =>
            createAuditLog('qc_rework', 'work_order', entityId)
          );

          // Create rework logs for sales_order (should be ignored)
          const soLogs = Array.from({ length: soReworkCount }, () =>
            createAuditLog('qc_rework', 'sales_order', entityId)
          );

          const allLogs = [...woLogs, ...soLogs];

          const count = countReworkFromAuditLogs(entityId, allLogs);

          // Should only count work_order entries
          expect(count).toBe(Math.min(woReworkCount, 99));
        }
      ),
      { numRuns: 100 }
    );
  });

  it('warning shown when rework count >= 10', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 10, max: 50 }),
        (reworkCount) => {
          const shouldWarn = shouldShowReworkWarning(reworkCount);
          expect(shouldWarn).toBe(true);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('no warning when rework count < 10', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 9 }),
        (reworkCount) => {
          const shouldWarn = shouldShowReworkWarning(reworkCount);
          expect(shouldWarn).toBe(false);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('count is deterministic for same input', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 100 }),
        (reworkCount) => {
          const workOrderId = 'wo-deterministic';
          const auditLogs = createReworkLogs(workOrderId, reworkCount);

          const count1 = countReworkFromAuditLogs(workOrderId, auditLogs);
          const count2 = countReworkFromAuditLogs(workOrderId, auditLogs);

          expect(count1).toBe(count2);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('count is independent of audit log order', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 5, max: 30 }),
        (reworkCount) => {
          const workOrderId = 'wo-order';
          const auditLogs = createReworkLogs(workOrderId, reworkCount);

          const count1 = countReworkFromAuditLogs(workOrderId, auditLogs);

          // Reverse the order
          const reversedLogs = [...auditLogs].reverse();
          const count2 = countReworkFromAuditLogs(workOrderId, reversedLogs);

          // Shuffle the order
          const shuffledLogs = [...auditLogs].sort(() => Math.random() - 0.5);
          const count3 = countReworkFromAuditLogs(workOrderId, shuffledLogs);

          // All should give same count
          expect(count1).toBe(count2);
          expect(count1).toBe(count3);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('realistic scenario - 3 rework cycles', () => {
    const workOrderId = 'wo-realistic';
    const auditLogs = createReworkLogs(workOrderId, 3);

    const count = countReworkFromAuditLogs(workOrderId, auditLogs);

    expect(count).toBe(3);
    expect(shouldShowReworkWarning(count)).toBe(false);
  });

  it('concerning scenario - 15 rework cycles with warning', () => {
    const workOrderId = 'wo-concerning';
    const auditLogs = createReworkLogs(workOrderId, 15);

    const count = countReworkFromAuditLogs(workOrderId, auditLogs);

    expect(count).toBe(15);
    expect(shouldShowReworkWarning(count)).toBe(true);
  });

  it('extreme scenario - 200 rework cycles capped at 99', () => {
    const workOrderId = 'wo-extreme';
    const auditLogs = createReworkLogs(workOrderId, 200);

    const count = countReworkFromAuditLogs(workOrderId, auditLogs);

    expect(count).toBe(99);
    expect(shouldShowReworkWarning(count)).toBe(true);
  });

  it('mixed scenario - multiple work orders and action types', () => {
    const wo1 = 'wo-001';
    const wo2 = 'wo-002';

    const auditLogs: AuditLogEntry[] = [
      ...createReworkLogs(wo1, 5),
      ...createReworkLogs(wo2, 8),
      createAuditLog('qc_approve', 'work_order', wo1),
      createAuditLog('qc_reject', 'work_order', wo1),
      createAuditLog('release_wo', 'work_order', wo1),
      createAuditLog('qc_rework', 'sales_order', wo1), // Different entity type
    ];

    const count1 = countReworkFromAuditLogs(wo1, auditLogs);
    const count2 = countReworkFromAuditLogs(wo2, auditLogs);

    expect(count1).toBe(5);
    expect(count2).toBe(8);
  });

  it('count increases monotonically with additional rework entries', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 40 }),
        fc.integer({ min: 1, max: 10 }),
        (initialCount, additionalCount) => {
          const workOrderId = 'wo-monotonic';
          const initialLogs = createReworkLogs(workOrderId, initialCount);
          const additionalLogs = createReworkLogs(workOrderId, additionalCount);

          const count1 = countReworkFromAuditLogs(workOrderId, initialLogs);
          const count2 = countReworkFromAuditLogs(workOrderId, [...initialLogs, ...additionalLogs]);

          // Count should increase (or stay at 99 if capped)
          if (initialCount < 99) {
            expect(count2).toBeGreaterThanOrEqual(count1);
          }
          expect(count2).toBeLessThanOrEqual(99);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('empty audit log array always returns zero', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 20 }),
        (workOrderId) => {
          const count = countReworkFromAuditLogs(workOrderId, []);
          expect(count).toBe(0);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('action type matching is exact (case sensitive)', () => {
    const workOrderId = 'wo-case';

    const auditLogs: AuditLogEntry[] = [
      createAuditLog('qc_rework', 'work_order', workOrderId),
      createAuditLog('QC_REWORK', 'work_order', workOrderId), // Different case
      createAuditLog('qc_Rework', 'work_order', workOrderId), // Different case
      createAuditLog('qc_rework', 'work_order', workOrderId),
    ];

    const count = countReworkFromAuditLogs(workOrderId, auditLogs);

    // Should only count exact matches (lowercase 'qc_rework')
    expect(count).toBe(2);
  });

  it('count respects cap even with duplicate timestamps', () => {
    const workOrderId = 'wo-duplicates';
    const timestamp = new Date().toISOString();

    // Create 120 rework logs with same timestamp
    const auditLogs = Array.from({ length: 120 }, () =>
      createAuditLog('qc_rework', 'work_order', workOrderId, timestamp)
    );

    const count = countReworkFromAuditLogs(workOrderId, auditLogs);

    expect(count).toBe(99);
  });
});
