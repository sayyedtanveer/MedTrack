/**
 * Price Override Panel Component
 * Displays price overrides and variance analysis
 * Phase 2 Frontend Integration
 */

import React, { useState, useEffect } from "react";
import { PriceOverrideRecord, RecordPriceOverrideRequest } from "../types/pricing";
import { priceOverrideApi } from "../services/pricingApi";

interface PriceOverridePanelProps {
  materialId?: string;
  onOverrideRecorded?: (override: PriceOverrideRecord) => void;
}

export const PriceOverridePanel: React.FC<PriceOverridePanelProps> = ({
  materialId,
  onOverrideRecorded,
}) => {
  const [overrides, setOverrides] = useState<PriceOverrideRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [showForm, setShowForm] = useState<boolean>(false);

  // Form state
  const [formData, setFormData] = useState<RecordPriceOverrideRequest>({
    material_id: materialId || "",
    grn_id: undefined,
    suggested_price: 0,
    override_price: 0,
    override_reason: "OTHER",
    notes: "",
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState<boolean>(false);

  const pageSize = 20;

  useEffect(() => {
    fetchOverrides();
  }, [materialId, currentPage]);

  const fetchOverrides = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await priceOverrideApi.list(materialId, currentPage, pageSize);
      setOverrides(result.overrides);
      setTotalPages(Math.ceil(result.total / pageSize));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch price overrides";
      setError(message);
      console.error("Error fetching overrides:", err);
    } finally {
      setLoading(false);
    }
  };

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.material_id) errors.material_id = "Material is required";
    if (!formData.suggested_price || formData.suggested_price <= 0) {
      errors.suggested_price = "Suggested price must be > 0";
    }
    if (!formData.override_price || formData.override_price <= 0) {
      errors.override_price = "Override price must be > 0";
    }
    if (!formData.override_reason) errors.override_reason = "Reason is required";

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!validateForm()) return;

    setSubmitting(true);
    try {
      const override = await priceOverrideApi.record(formData);
      setOverrides((prev) => [override, ...prev]);
      setShowForm(false);
      setFormData({
        material_id: materialId || "",
        grn_id: undefined,
        suggested_price: 0,
        override_price: 0,
        override_reason: "OTHER",
        notes: "",
      });
      onOverrideRecorded?.(override);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to record override";
      setError(message);
      console.error("Error recording override:", err);
    } finally {
      setSubmitting(false);
    }
  };

  const getReasonBadge = (reason: string) => {
    const reasonMap: Record<string, { label: string; color: string }> = {
      QUALITY_ISSUE: { label: "Quality Issue", color: "bg-red-100 text-red-800" },
      RUSH_ORDER: { label: "Rush Order", color: "bg-orange-100 text-orange-800" },
      BULK_DISCOUNT: { label: "Bulk Discount", color: "bg-green-100 text-green-800" },
      VENDOR_PREFERENCE: { label: "Vendor Preference", color: "bg-blue-100 text-blue-800" },
      OTHER: { label: "Other", color: "bg-gray-100 text-gray-800" },
    };

    const info = reasonMap[reason] || { label: reason, color: "bg-gray-100 text-gray-800" };
    return (
      <span className={`px-2 py-1 rounded text-xs font-semibold ${info.color}`}>
        {info.label}
      </span>
    );
  };

  const getVarianceColor = (variance: number | null): string => {
    if (!variance) return "text-gray-600";
    if (variance > 10) return "text-red-600"; // Price increase > 10%
    if (variance < -10) return "text-green-600"; // Price decrease > 10%
    return "text-gray-600";
  };

  const reasonOptions = [
    { value: "QUALITY_ISSUE", label: "Quality Issue" },
    { value: "RUSH_ORDER", label: "Rush Order" },
    { value: "BULK_DISCOUNT", label: "Bulk Discount" },
    { value: "VENDOR_PREFERENCE", label: "Vendor Preference" },
    { value: "OTHER", label: "Other" },
  ];

  return (
    <div className="w-full">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Price Overrides</h2>
            <p className="text-gray-600">
              Record when actual prices differ from suggested prices
            </p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            {showForm ? "Cancel" : "Record Override"}
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded text-red-800">
          Error: {error}
        </div>
      )}

      {/* New Override Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 p-6 bg-blue-50 border border-blue-200 rounded">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Record Price Override</h3>

          {/* Material ID */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700">
              Material <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.material_id}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, material_id: e.target.value }))
              }
              placeholder="Select or enter material ID"
              className={`mt-1 w-full px-3 py-2 border rounded-md ${
                formErrors.material_id ? "border-red-500" : "border-gray-300"
              }`}
            />
            {formErrors.material_id && (
              <p className="text-red-500 text-xs mt-1">{formErrors.material_id}</p>
            )}
          </div>

          {/* GRN ID (Optional) */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700">GRN ID (Optional)</label>
            <input
              type="text"
              value={formData.grn_id || ""}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, grn_id: e.target.value || undefined }))
              }
              placeholder="Related GRN ID"
              className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          {/* Prices Grid */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Suggested Price <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={formData.suggested_price}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    suggested_price: parseFloat(e.target.value),
                  }))
                }
                placeholder="0.00"
                className={`mt-1 w-full px-3 py-2 border rounded-md ${
                  formErrors.suggested_price ? "border-red-500" : "border-gray-300"
                }`}
              />
              {formErrors.suggested_price && (
                <p className="text-red-500 text-xs mt-1">{formErrors.suggested_price}</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Override Price <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={formData.override_price}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    override_price: parseFloat(e.target.value),
                  }))
                }
                placeholder="0.00"
                className={`mt-1 w-full px-3 py-2 border rounded-md ${
                  formErrors.override_price ? "border-red-500" : "border-gray-300"
                }`}
              />
              {formErrors.override_price && (
                <p className="text-red-500 text-xs mt-1">{formErrors.override_price}</p>
              )}
            </div>
          </div>

          {/* Variance Calculation */}
          {formData.suggested_price > 0 && formData.override_price > 0 && (
            <div className="mb-4 p-3 bg-white border border-gray-300 rounded">
              <p className="text-sm text-gray-600">
                Variance:{" "}
                <span
                  className={`font-semibold ${getVarianceColor(
                    ((formData.override_price - formData.suggested_price) /
                      formData.suggested_price) *
                      100
                  )}`}
                >
                  {(
                    ((formData.override_price - formData.suggested_price) /
                      formData.suggested_price) *
                    100
                  ).toFixed(2)}
                  %
                </span>
              </p>
            </div>
          )}

          {/* Override Reason */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700">
              Reason <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.override_reason}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  override_reason: e.target.value as any,
                }))
              }
              className={`mt-1 w-full px-3 py-2 border rounded-md ${
                formErrors.override_reason ? "border-red-500" : "border-gray-300"
              }`}
            >
              <option value="">Select reason</option>
              {reasonOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            {formErrors.override_reason && (
              <p className="text-red-500 text-xs mt-1">{formErrors.override_reason}</p>
            )}
          </div>

          {/* Notes */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700">Notes (Optional)</label>
            <textarea
              value={formData.notes}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, notes: e.target.value }))
              }
              placeholder="Additional details..."
              rows={3}
              className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          {/* Form Actions */}
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 bg-gray-300 text-gray-800 rounded hover:bg-gray-400"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400"
            >
              {submitting ? "Recording..." : "Record Override"}
            </button>
          </div>
        </form>
      )}

      {/* Loading State */}
      {loading && !overrides.length ? (
        <div className="text-center py-8 text-gray-500">Loading price overrides...</div>
      ) : overrides.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No price overrides recorded</div>
      ) : (
        <>
          {/* Overrides List */}
          <div className="space-y-3 mb-6">
            {overrides.map((override) => (
              <div key={override.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      {getReasonBadge(override.override_reason)}
                      <span className="text-gray-500 text-xs">ID: {override.id.slice(0, 8)}...</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">
                      {new Date(override.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>

                {/* Prices */}
                <div className="mb-3 p-3 bg-gray-50 rounded">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Suggested</p>
                      <p className="text-lg font-semibold text-gray-900">
                        ₹{override.suggested_price.toFixed(6)}
                      </p>
                    </div>
                    <div>
                      <p className="text-center text-sm font-semibold text-gray-600">
                        {override.variance_percent !== null
                          ? `${override.variance_percent > 0 ? "+" : ""}${override.variance_percent.toFixed(2)}%`
                          : "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Override</p>
                      <p className="text-lg font-semibold text-blue-700">
                        ₹{override.override_price.toFixed(6)}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Details */}
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-gray-500">Recorded By</p>
                    <p className="text-gray-900">{override.override_by}</p>
                  </div>
                  {override.grn_id && (
                    <div>
                      <p className="text-gray-500">GRN</p>
                      <p className="text-gray-900 font-mono text-xs">{override.grn_id.slice(0, 8)}...</p>
                    </div>
                  )}
                  {override.notes && (
                    <div className="col-span-2">
                      <p className="text-gray-500">Notes</p>
                      <p className="text-gray-900">{override.notes}</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded border border-gray-200">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1 || loading}
                className="px-3 py-2 bg-gray-300 text-gray-700 rounded disabled:bg-gray-200 text-sm"
              >
                ← Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages || loading}
                className="px-3 py-2 bg-gray-300 text-gray-700 rounded disabled:bg-gray-200 text-sm"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};
