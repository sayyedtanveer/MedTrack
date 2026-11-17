/**
 * Supplier Price Agreement Form Component
 * Handles creation and editing of supplier agreements in DRAFT status
 * Phase 2e Frontend Integration
 */

import React, { useState, useCallback } from "react";
import { SupplierPriceAgreement, CreateSupplierPriceAgreementRequest } from "../types/pricing";

interface SupplierPriceAgreementFormProps {
  initialData?: SupplierPriceAgreement;
  isEditMode?: boolean;
  loading?: boolean;
  onSubmit: (data: CreateSupplierPriceAgreementRequest) => Promise<void>;
  onCancel?: () => void;
}

export const SupplierPriceAgreementForm: React.FC<SupplierPriceAgreementFormProps> = ({
  initialData,
  isEditMode = false,
  loading = false,
  onSubmit,
  onCancel,
}) => {
  const [formData, setFormData] = useState<CreateSupplierPriceAgreementRequest>({
    supplier_id: initialData?.supplier_id || "",
    material_id: initialData?.material_id || "",
    base_price: initialData?.base_price || 0,
    currency_code: initialData?.currency_code || "USD",
    quantity_tiers: initialData?.quantity_tiers || [],
    effective_from: initialData?.effective_from || new Date().toISOString().split("T")[0],
    effective_to: initialData?.effective_to || null,
    notes: initialData?.notes || "",
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const validateForm = useCallback((): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.supplier_id) newErrors.supplier_id = "Supplier is required";
    if (!formData.material_id) newErrors.material_id = "Material is required";
    if (!formData.base_price || formData.base_price <= 0) {
      newErrors.base_price = "Base price must be greater than 0";
    }
    if (!formData.currency_code) newErrors.currency_code = "Currency is required";
    if (!formData.effective_from) newErrors.effective_from = "Effective from date is required";

    if (formData.effective_to) {
      const from = new Date(formData.effective_from);
      const to = new Date(formData.effective_to);
      if (to <= from) {
        newErrors.effective_to = "Effective to must be after effective from";
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData]);

  const handleFieldChange = useCallback(
    (field: string, value: unknown) => {
      setFormData((prev) => ({
        ...prev,
        [field]: value,
      }));
      // Clear error when field is corrected
      if (errors[field]) {
        setErrors((prev) => {
          const newErrors = { ...prev };
          delete newErrors[field];
          return newErrors;
        });
      }
    },
    [errors]
  );

  const handleAddQuantityTier = useCallback(() => {
    setFormData((prev) => ({
      ...prev,
      quantity_tiers: [
        ...(prev.quantity_tiers || []),
        { min_qty: 0, max_qty: null, discount_percent: 0 },
      ],
    }));
  }, []);

  const handleUpdateQuantityTier = useCallback(
    (index: number, field: string, value: unknown) => {
      const updated = [...(formData.quantity_tiers || [])];
      updated[index] = { ...updated[index], [field]: value };
      setFormData((prev) => ({
        ...prev,
        quantity_tiers: updated,
      }));
    },
    [formData.quantity_tiers]
  );

  const handleRemoveQuantityTier = useCallback((index: number) => {
    setFormData((prev) => ({
      ...prev,
      quantity_tiers: (prev.quantity_tiers || []).filter((_, i) => i !== index),
    }));
  }, []);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!validateForm()) return;

    try {
      await onSubmit(formData);
    } catch (err) {
      console.error("Form submission error:", err);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold">
        {isEditMode ? "Edit Supplier Price Agreement" : "Create Supplier Price Agreement"}
      </h2>

      {/* Supplier & Material Fields */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Supplier <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={formData.supplier_id}
            onChange={(e) => handleFieldChange("supplier_id", e.target.value)}
            disabled={isEditMode}
            placeholder="Select supplier"
            className={`mt-1 w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.supplier_id ? "border-red-500" : "border-gray-300"
            } ${isEditMode ? "bg-gray-100" : ""}`}
          />
          {errors.supplier_id && <p className="text-red-500 text-xs mt-1">{errors.supplier_id}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            Material <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={formData.material_id}
            onChange={(e) => handleFieldChange("material_id", e.target.value)}
            disabled={isEditMode}
            placeholder="Select material"
            className={`mt-1 w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.material_id ? "border-red-500" : "border-gray-300"
            } ${isEditMode ? "bg-gray-100" : ""}`}
          />
          {errors.material_id && <p className="text-red-500 text-xs mt-1">{errors.material_id}</p>}
        </div>
      </div>

      {/* Base Price & Currency */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Base Price <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            step="0.01"
            min="0"
            value={formData.base_price}
            onChange={(e) => handleFieldChange("base_price", parseFloat(e.target.value))}
            placeholder="0.00"
            className={`mt-1 w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.base_price ? "border-red-500" : "border-gray-300"
            }`}
          />
          {errors.base_price && <p className="text-red-500 text-xs mt-1">{errors.base_price}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            Currency <span className="text-red-500">*</span>
          </label>
          <select
            value={formData.currency_code}
            onChange={(e) => handleFieldChange("currency_code", e.target.value)}
            className={`mt-1 w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.currency_code ? "border-red-500" : "border-gray-300"
            }`}
          >
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
            <option value="INR">INR</option>
            <option value="GBP">GBP</option>
            <option value="JPY">JPY</option>
          </select>
          {errors.currency_code && <p className="text-red-500 text-xs mt-1">{errors.currency_code}</p>}
        </div>
      </div>

      {/* Effective Dates */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Effective From <span className="text-red-500">*</span>
          </label>
          <input
            type="date"
            value={formData.effective_from}
            onChange={(e) => handleFieldChange("effective_from", e.target.value)}
            className={`mt-1 w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.effective_from ? "border-red-500" : "border-gray-300"
            }`}
          />
          {errors.effective_from && <p className="text-red-500 text-xs mt-1">{errors.effective_from}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Effective To (Optional)</label>
          <input
            type="date"
            value={formData.effective_to || ""}
            onChange={(e) => handleFieldChange("effective_to", e.target.value || null)}
            className={`mt-1 w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.effective_to ? "border-red-500" : "border-gray-300"
            }`}
          />
          {errors.effective_to && <p className="text-red-500 text-xs mt-1">{errors.effective_to}</p>}
        </div>
      </div>

      {/* Quantity Tiers */}
      <div className="border-t pt-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Quantity Tier Pricing (Optional)</h3>
          <button
            type="button"
            onClick={handleAddQuantityTier}
            className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
          >
            Add Tier
          </button>
        </div>

        <div className="space-y-3">
          {(formData.quantity_tiers || []).map((tier, index) => (
            <div key={index} className="flex gap-3 p-3 bg-gray-50 rounded border border-gray-300">
              <input
                type="number"
                placeholder="Min Qty"
                min="0"
                value={tier.min_qty}
                onChange={(e) =>
                  handleUpdateQuantityTier(index, "min_qty", parseFloat(e.target.value))
                }
                className="flex-1 px-2 py-1 border border-gray-300 rounded"
              />
              <input
                type="number"
                placeholder="Max Qty (optional)"
                min="0"
                value={tier.max_qty || ""}
                onChange={(e) =>
                  handleUpdateQuantityTier(index, "max_qty", e.target.value ? parseFloat(e.target.value) : null)
                }
                className="flex-1 px-2 py-1 border border-gray-300 rounded"
              />
              <input
                type="number"
                placeholder="Discount %"
                min="0"
                max="100"
                step="0.01"
                value={tier.discount_percent}
                onChange={(e) =>
                  handleUpdateQuantityTier(index, "discount_percent", parseFloat(e.target.value))
                }
                className="flex-1 px-2 py-1 border border-gray-300 rounded"
              />
              <button
                type="button"
                onClick={() => handleRemoveQuantityTier(index)}
                className="px-2 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Notes */}
      <div>
        <label className="block text-sm font-medium text-gray-700">Notes (Optional)</label>
        <textarea
          value={formData.notes}
          onChange={(e) => handleFieldChange("notes", e.target.value)}
          placeholder="Terms, conditions, special agreements..."
          rows={4}
          className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Form Actions */}
      <div className="flex gap-3 justify-end border-t pt-4">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 bg-gray-300 text-gray-800 rounded hover:bg-gray-400"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400"
        >
          {loading ? "Saving..." : isEditMode ? "Update Agreement" : "Create Agreement"}
        </button>
      </div>
    </form>
  );
};
