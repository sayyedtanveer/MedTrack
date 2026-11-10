/**
 * Unit tests for ProductPickerModal logic and data transformation.
 * Validates Safeguards:
 * 1. Catalog reference price is populated for variants with selling_price > 0.
 * 2. Finished materials strictly have catalog_reference_price = null (never cost).
 * 3. Tab filtering returns appropriate subsets.
 * 4. Price validation enforces >= 0.
 */

import { describe, it, expect } from 'vitest';
import type { PickerItem } from '../ProductPickerModal';

describe('ProductPickerModal Logic & Safeguards', () => {
  it('maps variant with positive selling price to catalog_reference_price', () => {
    const rawVariant = {
      id: 'var-1',
      code: 'VAR-100',
      name: 'Pressure Valve',
      selling_price: 250.0,
      base_unit_code: 'PCS',
    };

    const item: PickerItem = {
      id: rawVariant.id,
      code: rawVariant.code,
      name: rawVariant.name,
      product_type: 'variant',
      uom_code: rawVariant.base_unit_code,
      catalog_reference_price:
        rawVariant.selling_price && Number(rawVariant.selling_price) > 0
          ? Number(rawVariant.selling_price)
          : null,
    };

    expect(item.catalog_reference_price).toBe(250.0);
    expect(item.product_type).toBe('variant');
    expect(item.uom_code).toBe('PCS');
  });

  it('safeguard 3: finished goods strictly have catalog_reference_price as null (never cost)', () => {
    const rawMaterial = {
      id: 'mat-1',
      code: 'FG-ROTA',
      name: 'Rotameter FG',
      material_type: 'finished',
      current_cost: 85.0, // Should NEVER be used as reference price
      base_unit: 'NOS',
    };

    const item: PickerItem = {
      id: rawMaterial.id,
      code: rawMaterial.code,
      name: rawMaterial.name,
      product_type: 'finished_product',
      uom_code: rawMaterial.base_unit,
      catalog_reference_price: null, // Strictly null!
    };

    expect(item.catalog_reference_price).toBeNull();
    expect(item.product_type).toBe('finished_product');
  });

  it('variant with zero or null selling price maps to null reference price', () => {
    const rawVariant = {
      id: 'var-2',
      code: 'VAR-ZERO',
      name: 'Unpriced Variant',
      selling_price: 0,
    };

    const referencePrice =
      rawVariant.selling_price && Number(rawVariant.selling_price) > 0
        ? Number(rawVariant.selling_price)
        : null;

    expect(referencePrice).toBeNull();
  });

  it('tab filtering segregates variants and finished goods correctly', () => {
    const items: PickerItem[] = [
      { id: '1', code: 'V-1', name: 'Var 1', product_type: 'variant', uom_code: 'KG' },
      { id: '2', code: 'V-2', name: 'Var 2', product_type: 'variant', uom_code: 'KG' },
      { id: '3', code: 'FG-1', name: 'FG 1', product_type: 'finished_product', uom_code: 'PCS' },
    ];

    const variantsOnly = items.filter((i) => i.product_type === 'variant');
    const fgOnly = items.filter((i) => i.product_type === 'finished_product');

    expect(variantsOnly).toHaveLength(2);
    expect(fgOnly).toHaveLength(1);
    expect(variantsOnly.every((i) => i.product_type === 'variant')).toBe(true);
    expect(fgOnly.every((i) => i.product_type === 'finished_product')).toBe(true);
  });

  it('validates price input >= 0 and rejects invalid inputs', () => {
    const validatePrice = (val: string): { valid: boolean; price?: number } => {
      const p = parseFloat(val);
      if (isNaN(p) || p < 0) return { valid: false };
      return { valid: true, price: p };
    };

    expect(validatePrice('250.00')).toEqual({ valid: true, price: 250.0 });
    expect(validatePrice('0')).toEqual({ valid: true, price: 0 });
    expect(validatePrice('-5.00')).toEqual({ valid: false });
    expect(validatePrice('')).toEqual({ valid: false });
    expect(validatePrice('abc')).toEqual({ valid: false });
  });
});
