/**
 * Property Test for Work Order Status-to-Action Mapping (Property 2)
 * 
 * **Validates: Requirements 6.1, 6.4, 6.6, 7.1, 8.4, 8.6, 9.4, 10.1, 12.1, 13.1**
 * 
 * Property 2: Work Order Status-to-Action Mapping
 * 
 * For any work order status, the set of action buttons displayed on the
 * Work_Order_Detail_Page SHALL be exactly the set defined in the WO_STATUS_ACTIONS
 * mapping — specifically: PLANNED shows only "Release", QC_PENDING shows only
 * "Approve QC" and "Reject QC", QC_REJECTED shows only "Send to Rework" and
 * "Scrap Batch", and so on for every status.
 */

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { WO_STATUS_ACTIONS } from '../WorkOrderActionConfig';

// All valid work order statuses per the WorkOrderStatus type
const ALL_WO_STATUSES = [
  'PLANNED',
  'RELEASED',
  'MATERIAL_PENDING',
  'MATERIAL_RESERVED',
  'MATERIAL_ISSUED',
  'IN_PRODUCTION',
  'QC_PENDING',
  'QC_APPROVED',
  'QC_REJECTED',
  'FG_RECEIVED',
  'COMPLETED',
  'CLOSED',
  'REWORK',
  'REJECTED',
  // Note: PRODUCTION_HOLD is in the config but not yet in the type union
] as const;

describe('Property 2: Work Order Status-to-Action Mapping', () => {
  it('every WO status has a defined action set (completeness)', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...ALL_WO_STATUSES),
        (status) => {
          // Every status must have a mapping (even if empty array)
          const actions = WO_STATUS_ACTIONS[status];
          expect(actions).toBeDefined();
          expect(Array.isArray(actions)).toBe(true);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('PLANNED shows only "Release Work Order" action', () => {
    const actions = WO_STATUS_ACTIONS['PLANNED'];
    expect(actions).toHaveLength(1);
    expect(actions[0].label).toBe('Release Work Order');
    expect(actions[0].actionKey).toBe('release');
  });

  it('RELEASED and MATERIAL_PENDING show no action buttons', () => {
    expect(WO_STATUS_ACTIONS['RELEASED']).toHaveLength(0);
    expect(WO_STATUS_ACTIONS['MATERIAL_PENDING']).toHaveLength(0);
  });

  it('MATERIAL_RESERVED shows no action buttons (materials table with Issue buttons per line)', () => {
    expect(WO_STATUS_ACTIONS['MATERIAL_RESERVED']).toHaveLength(0);
  });

  it('MATERIAL_ISSUED shows only "Start Production" action', () => {
    const actions = WO_STATUS_ACTIONS['MATERIAL_ISSUED'];
    expect(actions).toHaveLength(1);
    expect(actions[0].label).toBe('Start Production');
    expect(actions[0].actionKey).toBe('start');
  });

  it('IN_PRODUCTION shows no action buttons (Record Production form shown instead)', () => {
    expect(WO_STATUS_ACTIONS['IN_PRODUCTION']).toHaveLength(0);
  });

  it('QC_PENDING shows exactly "Approve QC" and "Reject QC" actions', () => {
    const actions = WO_STATUS_ACTIONS['QC_PENDING'];
    expect(actions).toHaveLength(2);
    
    const labels = actions.map(a => a.label);
    expect(labels).toContain('Approve QC');
    expect(labels).toContain('Reject QC');
    
    const actionKeys = actions.map(a => a.actionKey);
    expect(actionKeys).toContain('qc_approve');
    expect(actionKeys).toContain('qc_reject');
  });

  it('QC_APPROVED shows only "Receive FG" action', () => {
    const actions = WO_STATUS_ACTIONS['QC_APPROVED'];
    expect(actions).toHaveLength(1);
    expect(actions[0].label).toBe('Receive FG');
    expect(actions[0].actionKey).toBe('receive_fg');
  });

  it('QC_REJECTED shows exactly "Send to Rework" and "Scrap Batch" actions', () => {
    const actions = WO_STATUS_ACTIONS['QC_REJECTED'];
    expect(actions).toHaveLength(2);
    
    const labels = actions.map(a => a.label);
    expect(labels).toContain('Send to Rework');
    expect(labels).toContain('Scrap Batch');
    
    const actionKeys = actions.map(a => a.actionKey);
    expect(actionKeys).toContain('send_to_rework');
    expect(actionKeys).toContain('scrap');
  });

  it('REWORK shows only "Start Rework Production" action', () => {
    const actions = WO_STATUS_ACTIONS['REWORK'];
    expect(actions).toHaveLength(1);
    expect(actions[0].label).toBe('Start Rework Production');
    expect(actions[0].actionKey).toBe('start_rework');
  });

  it('FG_RECEIVED shows only "Complete" action', () => {
    const actions = WO_STATUS_ACTIONS['FG_RECEIVED'];
    expect(actions).toHaveLength(1);
    expect(actions[0].label).toBe('Complete');
    expect(actions[0].actionKey).toBe('complete');
  });

  it('COMPLETED and CLOSED show no action buttons', () => {
    expect(WO_STATUS_ACTIONS['COMPLETED']).toHaveLength(0);
    expect(WO_STATUS_ACTIONS['CLOSED']).toHaveLength(0);
  });

  it('REJECTED shows no action buttons', () => {
    expect(WO_STATUS_ACTIONS['REJECTED']).toHaveLength(0);
  });

  it('all action objects have required fields (label, actionKey, color)', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...ALL_WO_STATUSES),
        (status) => {
          const actions = WO_STATUS_ACTIONS[status];
          actions.forEach(action => {
            expect(action).toHaveProperty('label');
            expect(action).toHaveProperty('actionKey');
            expect(action).toHaveProperty('color');
            expect(typeof action.label).toBe('string');
            expect(typeof action.actionKey).toBe('string');
            expect(typeof action.color).toBe('string');
            expect(action.label.length).toBeGreaterThan(0);
            expect(action.actionKey.length).toBeGreaterThan(0);
            expect(action.color.length).toBeGreaterThan(0);
          });
        }
      ),
      { numRuns: 100 }
    );
  });

  it('all action keys are unique within each status', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...ALL_WO_STATUSES),
        (status) => {
          const actions = WO_STATUS_ACTIONS[status];
          const actionKeys = actions.map(a => a.actionKey);
          const uniqueKeys = new Set(actionKeys);
          expect(uniqueKeys.size).toBe(actionKeys.length);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('all action labels are unique within each status', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...ALL_WO_STATUSES),
        (status) => {
          const actions = WO_STATUS_ACTIONS[status];
          const labels = actions.map(a => a.label);
          const uniqueLabels = new Set(labels);
          expect(uniqueLabels.size).toBe(labels.length);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('no status has more than 3 actions (UX constraint)', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...ALL_WO_STATUSES),
        (status) => {
          const actions = WO_STATUS_ACTIONS[status];
          expect(actions.length).toBeLessThanOrEqual(3);
        }
      ),
      { numRuns: 100 }
    );
  });
});
