/**
 * Property 21: Status Color Uniqueness
 * 
 * Validates: Requirements 10.5, 11.1
 * 
 * For any two distinct non-error SO statuses, the assigned badge colors SHALL differ.
 * Same rule applies for WO statuses.
 */

import { describe, it, expect } from 'vitest';
import { SO_STATUS_COLOR_MAP } from '../SalesOrderStatusConfig';
import { WO_STATUS_COLORS } from '../../../work-orders/components/WorkOrderStatusConfig';

describe('Property 21: Status Color Uniqueness', () => {
  it('distinct non-error SO statuses have distinct badge colors', () => {
    // **Validates: Requirements 10.5, 11.1**
    
    // Get all non-error SO statuses (exclude REJECTED, CANCELLED)
    const normalStatuses = Object.keys(SO_STATUS_COLOR_MAP).filter(
      (s) => !['REJECTED', 'CANCELLED'].includes(s)
    );

    // Generate all pairs and verify colors differ
    for (let i = 0; i < normalStatuses.length; i++) {
      for (let j = i + 1; j < normalStatuses.length; j++) {
        const status1 = normalStatuses[i];
        const status2 = normalStatuses[j];
        const color1 = SO_STATUS_COLOR_MAP[status1];
        const color2 = SO_STATUS_COLOR_MAP[status2];

        // Colors should differ for distinct statuses
        expect(color1).not.toBe(color2);
      }
    }
  });

  it('distinct non-error WO statuses have distinct badge colors', () => {
    // **Validates: Requirements 10.5, 11.1**
    
    // Get all non-error WO statuses (exclude REJECTED, QC_REJECTED, CLOSED)
    // Note: QC_REJECTED and REJECTED are error statuses that can share colors
    const normalStatuses = Object.keys(WO_STATUS_COLORS).filter(
      (s) => !['REJECTED', 'QC_REJECTED', 'CLOSED'].includes(s)
    );

    // Generate all pairs and verify colors differ
    for (let i = 0; i < normalStatuses.length; i++) {
      for (let j = i + 1; j < normalStatuses.length; j++) {
        const status1 = normalStatuses[i];
        const status2 = normalStatuses[j];
        const color1 = WO_STATUS_COLORS[status1];
        const color2 = WO_STATUS_COLORS[status2];

        // Colors should differ for distinct statuses
        expect(color1).not.toBe(color2);
      }
    }
  });
});
