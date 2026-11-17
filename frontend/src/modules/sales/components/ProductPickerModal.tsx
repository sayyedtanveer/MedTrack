/**
 * ProductPickerModal Component
 * Searchable product and variant picker for Sales Price Lists.
 * Mobile-responsive, fully accessible, user-friendly interface.
 * Supports active item_variants and finished materials with explicit reference price display.
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
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
import { Search, Loader2, Check, Package, Layers, X, AlertCircle } from 'lucide-react';
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
  const [apiError, setApiError] = useState<string | null>(null);

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
      setApiError(null);
    }
  }, [open]);

  // Fetch variants and finished materials concurrently
  useEffect(() => {
    if (!open) return;

    let isMounted = true;
    setIsSearching(true);
    setApiError(null);

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
        } else if (variantRes.status === 'rejected') {
          console.error('Failed to fetch variants:', variantRes.reason);
          setApiError('Failed to load product variants');
          setVariants([]);
        } else {
          setVariants([]);
        }

        // Process Finished Materials
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
        } else if (materialRes.status === 'rejected') {
          console.error('Failed to fetch materials:', materialRes.reason);
          setApiError('Failed to load finished goods');
          setFinishedGoods([]);
        } else {
          setFinishedGoods([]);
        }
      } catch (err) {
        if (isMounted) {
          console.error('Unexpected error during product fetch:', err);
          setApiError('An unexpected error occurred. Please try again.');
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

  const handleSelectItem = useCallback((item: PickerItem) => {
    setSelectedItem(item);
    setValidationError(null);
    if (item.catalog_reference_price !== null && item.catalog_reference_price !== undefined) {
      setUnitPriceInput(item.catalog_reference_price.toFixed(2));
    } else {
      setUnitPriceInput('');
    }
  }, []);

  const handleSave = async () => {
    if (!selectedItem) {
      setValidationError('Please select a product from the list.');
      return;
    }

    const price = parseFloat(unitPriceInput);
    if (isNaN(price) || price < 0) {
      setValidationError('Price must be a valid number ≥ 0.');
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
      <DialogContent className="w-[95vw] max-w-2xl max-h-[95vh] flex flex-col p-3 sm:p-6 rounded-lg gap-0">
        {/* Header */}
        <DialogHeader className="flex flex-row items-center justify-between mb-2 shrink-0">
          <DialogTitle className="text-base sm:text-xl font-bold">Add Product to Price List</DialogTitle>
          <button
            onClick={() => onOpenChange(false)}
            className="text-gray-500 hover:text-gray-700 p-1"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </DialogHeader>

        {/* Search Bar and Filters */}
        <div className="space-y-2 sm:space-y-3 mb-2 sm:mb-4 shrink-0">
          {/* Search Input */}
          <div>
            <label className="text-xs sm:text-sm font-semibold text-gray-700 block mb-1.5">
              Search product / SKU
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Enter product name or SKU..."
                className="pl-9 text-sm w-full"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                autoFocus
                disabled={isSearching}
              />
            </div>
          </div>

          {/* API Error Alert */}
          {apiError && (
            <div className="flex gap-2 items-start p-2 bg-red-50 border border-red-200 rounded-md text-red-700 text-xs">
              <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
              <span>{apiError}</span>
            </div>
          )}

          {/* Filter Tabs */}
          <div className="flex gap-1.5 overflow-x-auto pb-1 sm:pb-2 border-b scrollbar-thin">
            {[
              { id: 'all', label: 'All', count: variants.length + finishedGoods.length, shortLabel: 'All' },
              { id: 'variant', label: 'Variants', count: variants.length, shortLabel: 'Variants' },
              { id: 'finished_product', label: 'Finished Goods', count: finishedGoods.length, shortLabel: 'FG' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as FilterTab)}
                className={`px-2.5 sm:px-3 py-1.5 text-xs sm:text-sm font-medium rounded-full whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? tab.id === 'variant'
                      ? 'bg-blue-600 text-white'
                      : tab.id === 'finished_product'
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-900 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <span className="sm:hidden">{tab.shortLabel}</span>
                <span className="hidden sm:inline">{tab.label}</span>
                <span className="ml-1 opacity-75">({tab.count})</span>
              </button>
            ))}
          </div>
        </div>

        {/* Product Results List - Scrollable with fixed max height */}
        <div
          className="overflow-y-auto border rounded-md divide-y divide-gray-100 bg-gray-50/50 mb-2 sm:mb-4 min-h-[120px] max-h-[35vh] sm:max-h-[40vh]"
        >
          {isSearching ? (
            <div className="flex items-center justify-center py-8 text-gray-500">
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
              <span className="text-xs sm:text-sm">Searching active products...</span>
            </div>
          ) : displayedItems.length === 0 ? (
            <div className="text-center py-8 text-gray-500 text-xs sm:text-sm px-4">
              <Package className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No active products found</p>
              {debouncedSearch && <p className="text-xs mt-1">matching "{debouncedSearch}"</p>}
            </div>
          ) : (
            displayedItems.map((item) => {
              const isSelected = selectedItem?.id === item.id && selectedItem?.product_type === item.product_type;
              return (
                <div
                  key={`${item.product_type}-${item.id}`}
                  onClick={() => handleSelectItem(item)}
                  className={`p-2.5 sm:p-3 cursor-pointer flex items-center justify-between gap-2 sm:gap-3 transition-colors ${
                    isSelected
                      ? 'bg-blue-50 border-l-4 border-l-blue-600'
                      : 'hover:bg-gray-100'
                  }`}
                  role="button"
                  tabIndex={0}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <Badge
                        variant="outline"
                        className={`text-[10px] sm:text-xs px-1.5 py-0 ${
                          item.product_type === 'variant'
                            ? 'bg-blue-50 text-blue-700 border-blue-200'
                            : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        }`}
                      >
                        {item.product_type === 'variant' ? (
                          <span className="flex items-center gap-0.5">
                            <Layers className="h-2.5 w-2.5" /> Var
                          </span>
                        ) : (
                          <span className="flex items-center gap-0.5">
                            <Package className="h-2.5 w-2.5" /> FG
                          </span>
                        )}
                      </Badge>
                      <span className="font-mono text-xs sm:text-sm font-semibold text-gray-800 truncate max-w-[120px] sm:max-w-none">
                        {item.code}
                      </span>
                      {item.uom_code && (
                        <span className="text-[10px] sm:text-xs text-gray-500 font-medium bg-gray-200/60 px-1.5 py-0.5 rounded whitespace-nowrap">
                          {item.uom_code}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-900 font-medium truncate mt-0.5">{item.name}</p>
                    <p className="text-xs text-gray-600 mt-0.5">
                      Ref:{' '}
                      {item.catalog_reference_price !== null && item.catalog_reference_price !== undefined ? (
                        <span className="font-semibold text-gray-900">
                          ₹{item.catalog_reference_price.toFixed(2)}
                        </span>
                      ) : (
                        <span className="italic text-gray-400">Not set</span>
                      )}
                    </p>
                  </div>

                  {isSelected && (
                    <div className="h-5 w-5 sm:h-6 sm:w-6 rounded-full bg-blue-600 text-white flex items-center justify-center flex-shrink-0">
                      <Check className="h-3 w-3 sm:h-4 sm:w-4" />
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Selected Product Details & Price Input */}
        {selectedItem && (
          <div className="border border-blue-200 bg-blue-50/50 rounded-lg p-2.5 sm:p-4 space-y-2 sm:space-y-3 mb-2 sm:mb-4 shrink-0">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <span className="text-xs font-semibold uppercase tracking-wider text-blue-700 block">
                  Selected Product
                </span>
                <p className="text-sm font-bold text-gray-900 mt-0.5 truncate">
                  {selectedItem.code} · {selectedItem.name}
                </p>
                {selectedItem.uom_code && (
                  <p className="text-xs text-gray-600 mt-0.5">UOM: {selectedItem.uom_code}</p>
                )}
              </div>
              <Badge
                className={`text-xs flex-shrink-0 ${
                  selectedItem.product_type === 'variant'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-emerald-100 text-emerald-800'
                }`}
              >
                {selectedItem.product_type === 'variant' ? 'Variant' : 'Finished'}
              </Badge>
            </div>

            {/* Catalog Reference Price */}
            <div className="text-xs bg-white/70 px-2.5 py-1.5 rounded border border-blue-100">
              <span className="font-medium text-gray-700">Catalog Price (reference):</span>
              {selectedItem.catalog_reference_price !== null &&
              selectedItem.catalog_reference_price !== undefined ? (
                <span className="ml-1 font-semibold text-gray-900">
                  ₹{selectedItem.catalog_reference_price.toFixed(2)}
                </span>
              ) : (
                <span className="ml-1 italic text-gray-400">Not set</span>
              )}
            </div>

            {/* Price Input */}
            <div className="space-y-1">
              <label className="text-xs sm:text-sm font-semibold text-gray-800 block">
                Price List Unit Price <span className="text-red-600">*</span>
              </label>
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-sm text-gray-500 font-medium">₹</span>
                <Input
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="0.01"
                  placeholder="0.00"
                  className="pl-7 bg-white font-mono text-sm w-full"
                  value={unitPriceInput}
                  onChange={(e) => {
                    setUnitPriceInput(e.target.value);
                    setValidationError(null);
                  }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Validation Error */}
        {validationError && (
          <div className="flex gap-2 items-start p-2 bg-red-50 border border-red-200 rounded-md text-red-700 text-xs mb-2 shrink-0">
            <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
            <span>{validationError}</span>
          </div>
        )}

        {/* Footer Actions */}
        <DialogFooter className="flex gap-2 flex-col-reverse sm:flex-row shrink-0 mt-auto">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading || isSearching}
            className="w-full sm:w-auto text-sm"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={!selectedItem || loading || isSearching}
            className="w-full sm:w-auto bg-slate-900 hover:bg-slate-800 text-sm"
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
