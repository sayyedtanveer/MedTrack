/**
 * ProductPickerModal Component
 * Searchable product and variant picker for Sales Price Lists.
 * Supports active item_variants and finished materials with explicit reference price display.
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Search, Loader2, Check, Package, Layers } from 'lucide-react';
import { productService } from '@/services/product.service';
import { materialService } from '@/services/material.service';

export interface PickerItem {
  id: string;
  code: string;
  name: string;
  product_type: 'variant' | 'finished_product';
  uom_code: string | null;
  uom_name?: string | null;
  /** Catalog selling price reference if available (variants only). Never cost. */
  catalog_reference_price?: number | null;
}

export interface ProductPickerModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAddProduct: (payload: {
    product_id: string;
    product_type: 'variant' | 'finished_product';
    unit_price: number;
  }) => Promise<void>;
  loading?: boolean;
}

type FilterTab = 'all' | 'variant' | 'finished_product';

export const ProductPickerModal: React.FC<ProductPickerModalProps> = ({
  open,
  onOpenChange,
  onAddProduct,
  loading = false,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [activeTab, setActiveTab] = useState<FilterTab>('all');
  const [isSearching, setIsSearching] = useState(false);

  const [variants, setVariants] = useState<PickerItem[]>([]);
  const [finishedGoods, setFinishedGoods] = useState<PickerItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<PickerItem | null>(null);
  const [unitPriceInput, setUnitPriceInput] = useState<string>('');
  const [validationError, setValidationError] = useState<string | null>(null);

  // Debounce search input by 300ms
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm.trim());
    }, 300);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setSearchTerm('');
      setDebouncedSearch('');
      setSelectedItem(null);
      setUnitPriceInput('');
      setValidationError(null);
    }
  }, [open]);

  // Fetch variants and finished materials concurrently
  useEffect(() => {
    if (!open) return;

    let isMounted = true;
    setIsSearching(true);

    const fetchData = async () => {
      try {
        const [variantRes, materialRes] = await Promise.allSettled([
          productService.searchVariants({
            search: debouncedSearch || undefined,
            is_active: true,
            page_size: 50,
          }),
          materialService.getMaterials({
            query: debouncedSearch || undefined,
            material_type: 'finished',
            is_active: true,
            page: 1,
            page_size: 50,
          }),
        ]);

        if (!isMounted) return;

        // Process Variants
        if (variantRes.status === 'fulfilled' && variantRes.value?.items) {
          const mappedVariants: PickerItem[] = variantRes.value.items.map((v) => ({
            id: v.id,
            code: v.code,
            name: v.name,
            product_type: 'variant',
            uom_code: v.base_unit_code ?? null,
            catalog_reference_price:
              v.selling_price !== undefined && v.selling_price !== null && Number(v.selling_price) > 0
                ? Number(v.selling_price)
                : null,
          }));
          setVariants(mappedVariants);
        } else {
          setVariants([]);
        }

        // Process Finished Materials
        // Note: Finished materials do not possess a selling_price in MaterialModel;
        // catalog_reference_price is strictly null (never substitute current_cost).
        if (materialRes.status === 'fulfilled' && materialRes.value?.items) {
          const mappedMaterials: PickerItem[] = materialRes.value.items.map((m) => ({
            id: m.id,
            code: m.code,
            name: m.name,
            product_type: 'finished_product',
            uom_code: (m as any).base_unit ?? (m as any).unit_code ?? null,
            catalog_reference_price: null,
          }));
          setFinishedGoods(mappedMaterials);
        } else {
          setFinishedGoods([]);
        }
      } catch (err) {
        if (isMounted) {
          setVariants([]);
          setFinishedGoods([]);
        }
      } finally {
        if (isMounted) {
          setIsSearching(false);
        }
      }
    };

    fetchData();

    return () => {
      isMounted = false;
    };
  }, [open, debouncedSearch]);

  // Filter items by active tab
  const displayedItems = useMemo(() => {
    if (activeTab === 'variant') return variants;
    if (activeTab === 'finished_product') return finishedGoods;
    return [...variants, ...finishedGoods];
  }, [activeTab, variants, finishedGoods]);

  const handleSelectItem = (item: PickerItem) => {
    setSelectedItem(item);
    setValidationError(null);
    if (item.catalog_reference_price !== null && item.catalog_reference_price !== undefined) {
      setUnitPriceInput(item.catalog_reference_price.toFixed(2));
    } else {
      setUnitPriceInput('');
    }
  };

  const handleSave = async () => {
    if (!selectedItem) {
      setValidationError('Please select a product from the list.');
      return;
    }

    const price = parseFloat(unitPriceInput);
    if (isNaN(price) || price < 0) {
      setValidationError('Price List Unit Price must be 0 or greater.');
      return;
    }

    try {
      await onAddProduct({
        product_id: selectedItem.id,
        product_type: selectedItem.product_type,
        unit_price: price,
      });
      onOpenChange(false);
    } catch (err: any) {
      setValidationError(err?.message || 'Failed to add product to price list.');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[90vh] flex flex-col p-6">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold">Add Product to Price List</DialogTitle>
        </DialogHeader>

        {/* Search Bar */}
        <div className="space-y-3 pt-2">
          <label className="text-sm font-semibold text-gray-700 block">
            Search product / SKU
          </label>
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search by product name or SKU..."
              className="pl-9"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              autoFocus
            />
          </div>

          {/* Filter Tabs */}
          <div className="flex gap-2 pt-1 border-b pb-2">
            <button
              type="button"
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                activeTab === 'all'
                  ? 'bg-slate-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              All Products ({variants.length + finishedGoods.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('variant')}
              className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                activeTab === 'variant'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Variants ({variants.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('finished_product')}
              className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                activeTab === 'finished_product'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Finished Goods ({finishedGoods.length})
            </button>
          </div>
        </div>

        {/* Product Results List */}
        <div className="flex-1 overflow-y-auto max-h-56 min-h-36 border rounded-md my-2 divide-y divide-gray-100 bg-gray-50/50">
          {isSearching ? (
            <div className="flex items-center justify-center py-10 text-gray-500">
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
              <span className="text-sm">Searching active catalog products...</span>
            </div>
          ) : displayedItems.length === 0 ? (
            <div className="text-center py-10 text-gray-500 text-sm">
              No active products found matching "{debouncedSearch}".
            </div>
          ) : (
            displayedItems.map((item) => {
              const isSelected = selectedItem?.id === item.id && selectedItem?.product_type === item.product_type;
              return (
                <div
                  key={`${item.product_type}-${item.id}`}
                  onClick={() => handleSelectItem(item)}
                  className={`p-3 cursor-pointer flex items-center justify-between transition-colors ${
                    isSelected
                      ? 'bg-blue-50 border-l-4 border-l-blue-600'
                      : 'hover:bg-gray-100'
                  }`}
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className={`text-xs ${
                          item.product_type === 'variant'
                            ? 'bg-blue-50 text-blue-700 border-blue-200'
                            : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        }`}
                      >
                        {item.product_type === 'variant' ? (
                          <span className="flex items-center gap-1">
                            <Layers className="h-3 w-3" /> Variant
                          </span>
                        ) : (
                          <span className="flex items-center gap-1">
                            <Package className="h-3 w-3" /> Finished Good
                          </span>
                        )}
                      </Badge>
                      <span className="font-mono text-xs font-semibold text-gray-800">
                        {item.code}
                      </span>
                      {item.uom_code && (
                        <span className="text-xs text-gray-500 font-medium bg-gray-200/60 px-1.5 py-0.5 rounded">
                          {item.uom_code}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-900 font-medium">{item.name}</p>
                    <p className="text-xs text-gray-500">
                      Catalog Reference:{' '}
                      {item.catalog_reference_price !== null && item.catalog_reference_price !== undefined ? (
                        <span className="font-medium text-gray-700">
                          ₹{item.catalog_reference_price.toFixed(2)}
                        </span>
                      ) : (
                        <span className="italic text-gray-400">Not set</span>
                      )}
                    </p>
                  </div>

                  {isSelected && (
                    <div className="h-6 w-6 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0">
                      <Check className="h-4 w-4" />
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Selected Product Card & Price Input */}
        {selectedItem && (
          <div className="border border-blue-200 bg-blue-50/50 rounded-lg p-4 space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-blue-700">
                  Selected Product
                </span>
                <p className="text-sm font-bold text-gray-900 mt-0.5">
                  {selectedItem.code} · {selectedItem.name}
                  {selectedItem.uom_code ? ` · ${selectedItem.uom_code}` : ''}
                </p>
              </div>
              <Badge
                className={`text-xs ${
                  selectedItem.product_type === 'variant'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-emerald-100 text-emerald-800'
                }`}
              >
                {selectedItem.product_type === 'variant' ? 'Variant' : 'Finished Good'}
              </Badge>
            </div>

            {/* Catalog Selling Price Reference */}
            <div className="text-xs text-gray-600 flex items-center gap-1.5 bg-white/70 px-2.5 py-1.5 rounded border border-blue-100">
              <span className="font-medium text-gray-700">Catalog Selling Price (reference):</span>
              {selectedItem.catalog_reference_price !== null &&
              selectedItem.catalog_reference_price !== undefined ? (
                <span className="font-semibold text-gray-900">
                  ₹{selectedItem.catalog_reference_price.toFixed(2)}
                </span>
              ) : (
                <span className="italic text-gray-400">Not set</span>
              )}
            </div>

            {/* Price List Unit Price Input */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-800 block">
                Price List Unit Price *
              </label>
              <div className="relative">
                <span className="absolute left-3 top-2 text-sm text-gray-500 font-medium">
                  ₹
                </span>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="0.00"
                  className="pl-7 bg-white font-mono"
                  value={unitPriceInput}
                  onChange={(e) => setUnitPriceInput(e.target.value)}
                />
              </div>
              <p className="text-[11px] text-gray-500 mt-1">
                ℹ Suggested value only. Confirm or edit before saving.
              </p>
            </div>
          </div>
        )}

        {validationError && (
          <p className="text-xs text-red-600 font-medium mt-1">{validationError}</p>
        )}

        <DialogFooter className="mt-3">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={!selectedItem || loading}
            className="bg-slate-900 hover:bg-slate-800"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Adding…
              </>
            ) : (
              'Add Product'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ProductPickerModal;
