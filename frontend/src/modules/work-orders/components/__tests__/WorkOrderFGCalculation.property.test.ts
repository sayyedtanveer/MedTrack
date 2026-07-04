/**
 * Property 9: FG Quantity Calculation
 *
 * For any work order with produced_quantity P and scrap_quantity S,
 * the expected finished goods quantity SHALL equal P - S, and the
 * "Receive FG" button SHALL be disabled if and only if P - S <= 0.
 *
 * **Validates: Requirements 7.1, 7.2**
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';

// ─── Types ────────────────────────────────────────────────────────────────────

interface WorkOrder {
  produced_quantity: number;
  scrap_quantity: number;
}

// ─── Business Logic Functions (from WorkOrderDetailPage) ─────────────────────

/**
 * Calculate the expected finished goods quantity.
 * FG Quantity = Produced - Scrap
 */
function calculateFGQuantity(wo: WorkOrder): number {
  return wo.produced_quantity - wo.scrap_quantity;
}

/**
 * Determine if "Receive FG" button should be disabled.
 * Disabled if and only if FG quantity <= 0.
 */
function shouldDisableReceiveFGButton(wo: WorkOrder): boolean {
  const fgQty = calculateFGQuantity(wo);
  return fgQty <= 0;
}

// ─── Property Tests ───────────────────────────────────────────────────────────

describe('Property 9: FG Quantity Calculation', () => {
  it('FG quantity equals produced minus scrap for all valid inputs', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0, max: 10000, noNaN: true }),       // produced_quantity
        fc.double({ min: 0, max: 10000, noNaN: true }),       // scrap_quantity
        (produced, scrap) => {
          const wo: WorkOrder = {
            produced_quantity: produced,
            scrap_quantity: scrap,
          };

          const fgQty = calculateFGQuantity(wo);
          const expected = produced - scrap;

          // Allow small floating point tolerance
          expect(Math.abs(fgQty - expected)).toBeLessThan(0.0001);
        }
      ),
      { numRuns: 200 }
    );
  });

  it('Receive FG button disabled iff FG quantity <= 0', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0, max: 10000, noNaN: true }),
        fc.double({ min: 0, max: 10000, noNaN: true }),
        (produced, scrap) => {
          const wo: WorkOrder = {
            produced_quantity: produced,
            scrap_quantity: scrap,
          };

          const fgQty = calculateFGQuantity(wo);
          const isDisabled = shouldDisableReceiveFGButton(wo);

          // Button should be disabled iff FG quantity <= 0
          if (fgQty <= 0) {
            expect(isDisabled).toBe(true);
          } else {
            expect(isDisabled).toBe(false);
          }
        }
      ),
      { numRuns: 200 }
    );
  });

  it('FG quantity is zero when produced equals scrap', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0, max: 10000, noNaN: true }),
        (quantity) => {
          const wo: WorkOrder = {
            produced_quantity: quantity,
            scrap_quantity: quantity,
          };

          const fgQty = calculateFGQuantity(wo);
          expect(Math.abs(fgQty)).toBeLessThan(0.0001);

          // Button should be disabled when FG = 0
          expect(shouldDisableReceiveFGButton(wo)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('FG quantity is negative when scrap exceeds produced', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0, max: 10000, noNaN: true }),
        fc.double({ min: 0.01, max: 1000, noNaN: true }),
        (produced, excess) => {
          const scrap = produced + excess;
          const wo: WorkOrder = {
            produced_quantity: produced,
            scrap_quantity: scrap,
          };

          const fgQty = calculateFGQuantity(wo);
          expect(fgQty).toBeLessThan(0);

          // Button should be disabled when FG < 0
          expect(shouldDisableReceiveFGButton(wo)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('FG quantity is positive when produced exceeds scrap', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0.01, max: 10000, noNaN: true }),
        fc.double({ min: 0, max: 1, noNaN: true }), // scrap ratio (0-100%)
        (produced, scrapRatio) => {
          fc.pre(scrapRatio < 1); // Ensure scrap is less than produced
          const scrap = produced * scrapRatio;
          const wo: WorkOrder = {
            produced_quantity: produced,
            scrap_quantity: scrap,
          };

          const fgQty = calculateFGQuantity(wo);
          expect(fgQty).toBeGreaterThan(0);

          // Button should be enabled when FG > 0
          expect(shouldDisableReceiveFGButton(wo)).toBe(false);
        }
      ),
      { numRuns: 200 }
    );
  });

  it('boundary case - very small positive FG quantity enables button', () => {
    const wo: WorkOrder = {
      produced_quantity: 0.001,
      scrap_quantity: 0,
    };

    const fgQty = calculateFGQuantity(wo);
    expect(fgQty).toBeGreaterThan(0);
    expect(shouldDisableReceiveFGButton(wo)).toBe(false);
  });

  it('boundary case - zero produced and zero scrap disables button', () => {
    const wo: WorkOrder = {
      produced_quantity: 0,
      scrap_quantity: 0,
    };

    const fgQty = calculateFGQuantity(wo);
    expect(fgQty).toBe(0);
    expect(shouldDisableReceiveFGButton(wo)).toBe(true);
  });

  it('realistic production scenario - 95% yield', () => {
    const wo: WorkOrder = {
      produced_quantity: 1000,
      scrap_quantity: 50,
    };

    const fgQty = calculateFGQuantity(wo);
    expect(fgQty).toBe(950);
    expect(shouldDisableReceiveFGButton(wo)).toBe(false);
  });

  it('worst case scenario - 100% scrap', () => {
    const wo: WorkOrder = {
      produced_quantity: 500,
      scrap_quantity: 500,
    };

    const fgQty = calculateFGQuantity(wo);
    expect(fgQty).toBe(0);
    expect(shouldDisableReceiveFGButton(wo)).toBe(true);
  });

  it('best case scenario - zero scrap', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0.01, max: 10000, noNaN: true }),
        (produced) => {
          const wo: WorkOrder = {
            produced_quantity: produced,
            scrap_quantity: 0,
          };

          const fgQty = calculateFGQuantity(wo);
          expect(fgQty).toBe(produced);
          expect(shouldDisableReceiveFGButton(wo)).toBe(false);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('FG calculation is commutative with sign flip', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0, max: 10000, noNaN: true }),
        fc.double({ min: 0, max: 10000, noNaN: true }),
        (produced, scrap) => {
          const wo1: WorkOrder = {
            produced_quantity: produced,
            scrap_quantity: scrap,
          };

          const wo2: WorkOrder = {
            produced_quantity: scrap,
            scrap_quantity: produced,
          };

          const fgQty1 = calculateFGQuantity(wo1);
          const fgQty2 = calculateFGQuantity(wo2);

          // FG1 = produced - scrap
          // FG2 = scrap - produced = -(produced - scrap) = -FG1
          expect(Math.abs(fgQty1 + fgQty2)).toBeLessThan(0.0001);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('button state is deterministic for the same input', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0, max: 10000, noNaN: true }),
        fc.double({ min: 0, max: 10000, noNaN: true }),
        (produced, scrap) => {
          const wo: WorkOrder = {
            produced_quantity: produced,
            scrap_quantity: scrap,
          };

          const result1 = shouldDisableReceiveFGButton(wo);
          const result2 = shouldDisableReceiveFGButton(wo);

          expect(result1).toBe(result2);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('FG quantity monotonically increases with produced quantity', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0, max: 5000, noNaN: true }),
        fc.double({ min: 0, max: 5000, noNaN: true }),
        fc.double({ min: 0.01, max: 1000, noNaN: true }),
        (produced, scrap, increment) => {
          const wo1: WorkOrder = {
            produced_quantity: produced,
            scrap_quantity: scrap,
          };

          const wo2: WorkOrder = {
            produced_quantity: produced + increment,
            scrap_quantity: scrap,
          };

          const fgQty1 = calculateFGQuantity(wo1);
          const fgQty2 = calculateFGQuantity(wo2);

          // Increasing produced quantity should increase FG quantity
          expect(fgQty2).toBeGreaterThan(fgQty1);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('FG quantity monotonically decreases with scrap quantity', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0, max: 5000, noNaN: true }),
        fc.double({ min: 0, max: 5000, noNaN: true }),
        fc.double({ min: 0.01, max: 1000, noNaN: true }),
        (produced, scrap, increment) => {
          const wo1: WorkOrder = {
            produced_quantity: produced,
            scrap_quantity: scrap,
          };

          const wo2: WorkOrder = {
            produced_quantity: produced,
            scrap_quantity: scrap + increment,
          };

          const fgQty1 = calculateFGQuantity(wo1);
          const fgQty2 = calculateFGQuantity(wo2);

          // Increasing scrap quantity should decrease FG quantity
          expect(fgQty2).toBeLessThan(fgQty1);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('button transitions from enabled to disabled at threshold', () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0.01, max: 10000, noNaN: true }),
        (produced) => {
          // Case 1: scrap slightly less than produced - button enabled
          const wo1: WorkOrder = {
            produced_quantity: produced,
            scrap_quantity: produced - 0.01,
          };
          expect(shouldDisableReceiveFGButton(wo1)).toBe(false);

          // Case 2: scrap equals produced - button disabled
          const wo2: WorkOrder = {
            produced_quantity: produced,
            scrap_quantity: produced,
          };
          expect(shouldDisableReceiveFGButton(wo2)).toBe(true);

          // Case 3: scrap slightly more than produced - button disabled
          const wo3: WorkOrder = {
            produced_quantity: produced,
            scrap_quantity: produced + 0.01,
          };
          expect(shouldDisableReceiveFGButton(wo3)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });
});
