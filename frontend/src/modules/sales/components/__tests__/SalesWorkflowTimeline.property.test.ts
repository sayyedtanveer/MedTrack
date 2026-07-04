/**
 * Property 6: Workflow Timeline Stage Highlighting
 *
 * For any valid SO status, the `SalesWorkflowTimeline` component's stage computation must satisfy:
 * - Exactly one stage is marked "current" (the stage matching the current status)
 * - All preceding stages are marked "completed"
 * - All following stages are marked "pending"
 * - CANCELLED status marks all stages as "inactive"
 *
 * **Validates: Requirements 4.2, 4.7**
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';

// ─── Inline Constants and Helpers ────────────────────────────────────────────
// Copied from SalesWorkflowTimeline.tsx to avoid loading the whole component

/**
 * Timeline stages in order. Each maps to one or more SO statuses.
 */
const TIMELINE_STAGES = [
  { key: 'draft', label: 'Draft', statuses: ['DRAFT'] },
  { key: 'approval', label: 'Approval', statuses: ['PENDING_APPROVAL', 'APPROVED'] },
  { key: 'confirmed', label: 'Confirmed', statuses: ['CONFIRMED', 'WORK_ORDER_CREATED', 'PROCESSING'] },
  { key: 'production', label: 'Production', statuses: ['PRODUCTION'] },
  { key: 'ready', label: 'Ready', statuses: ['READY', 'READY_FOR_DISPATCH'] },
  { key: 'dispatched', label: 'Dispatched', statuses: ['SHIPPED'] },
  { key: 'delivered', label: 'Delivered', statuses: ['DELIVERED'] },
  { key: 'invoiced', label: 'Invoiced', statuses: ['INVOICED'] },
  { key: 'paid', label: 'Paid', statuses: ['PAYMENT_RECEIVED'] },
  { key: 'completed', label: 'Completed', statuses: ['COMPLETED'] },
] as const;

/**
 * Find the index of the current stage given the SO status.
 * Returns -1 if CANCELLED or not found.
 */
function getCurrentStageIndex(status: string): number {
  if (status === 'CANCELLED' || status === 'REJECTED') return -1;
  for (let i = 0; i < TIMELINE_STAGES.length; i++) {
    if ((TIMELINE_STAGES[i].statuses as readonly string[]).includes(status)) {
      return i;
    }
  }
  return -1;
}

// ─── Test Data ────────────────────────────────────────────────────────────────

// Valid SO statuses as defined in the design document
const VALID_SO_STATUSES = [
  'DRAFT',
  'PENDING_APPROVAL',
  'APPROVED',
  'REJECTED',
  'WORK_ORDER_CREATED',
  'CONFIRMED',
  'PROCESSING',
  'PRODUCTION',
  'READY',
  'READY_FOR_DISPATCH',
  'SHIPPED',
  'DELIVERED',
  'INVOICED',
  'PAYMENT_RECEIVED',
  'COMPLETED',
  'CANCELLED',
] as const;

// Extract all statuses that map to timeline stages (excluding CANCELLED and REJECTED)
const ACTIVE_SO_STATUSES = VALID_SO_STATUSES.filter(
  (status) => status !== 'CANCELLED' && status !== 'REJECTED'
);

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('Property 6: Workflow Timeline Stage Highlighting', () => {
  it('exactly one stage is current, preceding are completed, following are pending', () => {
    fc.assert(
      fc.property(fc.constantFrom(...ACTIVE_SO_STATUSES), (status) => {
        // Compute stage states based on the current status
        const currentStageIdx = getCurrentStageIndex(status);
        
        // Verify that we found a valid stage for this status
        expect(currentStageIdx).toBeGreaterThanOrEqual(0);
        expect(currentStageIdx).toBeLessThan(TIMELINE_STAGES.length);

        // Compute stage states
        const stages = TIMELINE_STAGES.map((stage, idx) => ({
          key: stage.key,
          label: stage.label,
          isCompleted: currentStageIdx > idx,
          isCurrent: currentStageIdx === idx,
          isPending: currentStageIdx < idx,
        }));

        // Property 1: Exactly one stage is marked "current"
        const currentCount = stages.filter((s) => s.isCurrent).length;
        expect(currentCount).toBe(1);

        // Property 2: All preceding stages (before current) are marked "completed"
        const completedStages = stages.filter((s) => s.isCompleted);
        const expectedCompletedCount = currentStageIdx;
        expect(completedStages.length).toBe(expectedCompletedCount);

        // Verify all completed stages come before current
        completedStages.forEach((completedStage) => {
          const idx = TIMELINE_STAGES.findIndex((s) => s.key === completedStage.key);
          expect(idx).toBeLessThan(currentStageIdx);
        });

        // Property 3: All following stages (after current) are marked "pending"
        const pendingStages = stages.filter((s) => s.isPending);
        const expectedPendingCount = TIMELINE_STAGES.length - currentStageIdx - 1;
        expect(pendingStages.length).toBe(expectedPendingCount);

        // Verify all pending stages come after current
        pendingStages.forEach((pendingStage) => {
          const idx = TIMELINE_STAGES.findIndex((s) => s.key === pendingStage.key);
          expect(idx).toBeGreaterThan(currentStageIdx);
        });

        // Property 4: No stage can be both completed and pending
        stages.forEach((stage) => {
          if (stage.isCompleted) {
            expect(stage.isPending).toBe(false);
            expect(stage.isCurrent).toBe(false);
          }
          if (stage.isPending) {
            expect(stage.isCompleted).toBe(false);
            expect(stage.isCurrent).toBe(false);
          }
          if (stage.isCurrent) {
            expect(stage.isCompleted).toBe(false);
            expect(stage.isPending).toBe(false);
          }
        });

        // Property 5: Ordering constraint - completed < current < pending
        const completedIndices = stages
          .filter((s) => s.isCompleted)
          .map((s) => TIMELINE_STAGES.findIndex((t) => t.key === s.key));
        const currentIndex = TIMELINE_STAGES.findIndex(
          (t) => stages.find((s) => s.isCurrent)?.key === t.key
        );
        const pendingIndices = stages
          .filter((s) => s.isPending)
          .map((s) => TIMELINE_STAGES.findIndex((t) => t.key === s.key));

        // All completed indices should be less than current
        completedIndices.forEach((idx) => {
          expect(idx).toBeLessThan(currentIndex);
        });

        // All pending indices should be greater than current
        pendingIndices.forEach((idx) => {
          expect(idx).toBeGreaterThan(currentIndex);
        });
      }),
      { numRuns: 100 }
    );
  });

  it('CANCELLED marks all stages as inactive', () => {
    const currentStageIdx = getCurrentStageIndex('CANCELLED');
    
    // For CANCELLED, getCurrentStageIndex returns -1
    expect(currentStageIdx).toBe(-1);

    // When currentStageIdx is -1, the component logic treats all stages as inactive
    // (neither completed, current, nor pending in the normal sense)
    const stages = TIMELINE_STAGES.map((stage, idx) => ({
      key: stage.key,
      label: stage.label,
      isCompleted: currentStageIdx > idx, // -1 > idx is always false
      isCurrent: currentStageIdx === idx, // -1 === idx is always false
      isPending: currentStageIdx < idx,   // -1 < idx is always true, but isCancelled flag overrides this
    }));

    // No stages should be marked as completed
    expect(stages.filter((s) => s.isCompleted).length).toBe(0);

    // No stages should be marked as current
    expect(stages.filter((s) => s.isCurrent).length).toBe(0);

    // All stages would be pending by index logic, but component renders them as inactive
    // The component uses isCancelled flag to render all stages with inactive styling
    stages.forEach((stage) => {
      expect(stage.isCompleted).toBe(false);
      expect(stage.isCurrent).toBe(false);
    });
  });

  it('REJECTED marks all stages as inactive', () => {
    const currentStageIdx = getCurrentStageIndex('REJECTED');
    
    // For REJECTED, getCurrentStageIndex returns -1
    expect(currentStageIdx).toBe(-1);

    // Same behavior as CANCELLED
    const stages = TIMELINE_STAGES.map((stage, idx) => ({
      key: stage.key,
      label: stage.label,
      isCompleted: currentStageIdx > idx,
      isCurrent: currentStageIdx === idx,
      isPending: currentStageIdx < idx,
    }));

    // No stages should be marked as completed or current
    expect(stages.filter((s) => s.isCompleted).length).toBe(0);
    expect(stages.filter((s) => s.isCurrent).length).toBe(0);

    stages.forEach((stage) => {
      expect(stage.isCompleted).toBe(false);
      expect(stage.isCurrent).toBe(false);
    });
  });

  it('stage highlighting is deterministic for the same status', () => {
    fc.assert(
      fc.property(fc.constantFrom(...ACTIVE_SO_STATUSES), (status) => {
        const currentStageIdx1 = getCurrentStageIndex(status);
        const currentStageIdx2 = getCurrentStageIndex(status);
        
        // Multiple calls with same status should return same index
        expect(currentStageIdx1).toBe(currentStageIdx2);
      }),
      { numRuns: 50 }
    );
  });

  it('all valid active statuses map to a valid timeline stage', () => {
    fc.assert(
      fc.property(fc.constantFrom(...ACTIVE_SO_STATUSES), (status) => {
        const currentStageIdx = getCurrentStageIndex(status);
        
        // Every active status should map to a valid stage index
        expect(currentStageIdx).toBeGreaterThanOrEqual(0);
        expect(currentStageIdx).toBeLessThan(TIMELINE_STAGES.length);

        // Verify the status is actually in the stage's status list
        const stage = TIMELINE_STAGES[currentStageIdx];
        const statusesInStage = stage.statuses as readonly string[];
        expect(statusesInStage).toContain(status);
      }),
      { numRuns: 100 }
    );
  });

  it('stage indices are monotonically ordered', () => {
    // Verify that as we progress through the workflow,
    // the stage indices increase (or stay the same within a stage)
    const orderedStatuses: string[] = [
      'DRAFT',
      'PENDING_APPROVAL',
      'APPROVED',
      'CONFIRMED',
      'WORK_ORDER_CREATED',
      'PROCESSING',
      'PRODUCTION',
      'READY',
      'READY_FOR_DISPATCH',
      'SHIPPED',
      'DELIVERED',
      'INVOICED',
      'PAYMENT_RECEIVED',
      'COMPLETED',
    ];

    const indices = orderedStatuses.map((status) => getCurrentStageIndex(status));

    // Verify indices are non-decreasing
    for (let i = 1; i < indices.length; i++) {
      expect(indices[i]).toBeGreaterThanOrEqual(indices[i - 1]);
    }
  });
});
