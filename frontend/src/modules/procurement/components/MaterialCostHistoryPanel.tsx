/**
 * Material Cost History Panel Component
 * Displays append-only audit log of material cost changes
 * Phase 2 Frontend Integration
 */

import React, { useState, useEffect } from "react";
import { MaterialCostHistory } from "../types/pricing";
import { materialCostHistoryApi } from "../services/pricingApi";

interface MaterialCostHistoryPanelProps {
  materialId: string;
  materialName?: string;
}

export const MaterialCostHistoryPanel: React.FC<MaterialCostHistoryPanelProps> = ({
  materialId,
  materialName = "Material",
}) => {
  const [history, setHistory] = useState<MaterialCostHistory[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [filterChangeType, setFilterChangeType] = useState<string | null>(null);

  const pageSize = 20;

  useEffect(() => {
    fetchHistory();
  }, [materialId, currentPage, filterChangeType]);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      if (filterChangeType) {
        const result = await materialCostHistoryApi.getHistoryByChangeType(
          materialId,
          filterChangeType,
          currentPage
        );
        setHistory(result.history);
        setTotalPages(Math.ceil(result.total / pageSize));
      } else {
        const result = await materialCostHistoryApi.getHistory(
          materialId,
          currentPage,
          pageSize
        );
        setHistory(result.history);
        setTotalPages(Math.ceil(result.total / pageSize));
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch cost history";
      setError(message);
      console.error("Error fetching cost history:", err);
    } finally {
      setLoading(false);
    }
  };

  const getChangeTypeBadge = (changeType: string) => {
    const typeMap: Record<string, { label: string; color: string }> = {
      GRN_RECEIPT: { label: "GRN Receipt", color: "bg-blue-100 text-blue-800" },
      GRN_REVERSAL: { label: "GRN Reversal", color: "bg-orange-100 text-orange-800" },
      COST_REVISION_APPROVED: { label: "Cost Revision Approved", color: "bg-green-100 text-green-800" },
      COST_REVISION_REJECTED: { label: "Cost Revision Rejected", color: "bg-red-100 text-red-800" },
      MANUAL_OVERRIDE: { label: "Manual Override", color: "bg-purple-100 text-purple-800" },
    };

    const info = typeMap[changeType] || { label: changeType, color: "bg-gray-100 text-gray-800" };
    return (
      <span className={`px-2 py-1 rounded text-xs font-semibold ${info.color}`}>
        {info.label}
      </span>
    );
  };

  const getSourceBadge = (sourceType: string) => {
    const sourceMap: Record<string, string> = {
      GRN: "Goods Receipt Note",
      PO_RECEIPT: "PO Receipt",
      SUPPLIER_AGREEMENT: "Supplier Agreement",
      MANUAL: "Manual Entry",
    };

    return sourceMap[sourceType] || sourceType;
  };

  const changeTypeOptions = [
    { value: "GRN_RECEIPT", label: "GRN Receipt" },
    { value: "GRN_REVERSAL", label: "GRN Reversal" },
    { value: "COST_REVISION_APPROVED", label: "Cost Revision Approved" },
    { value: "COST_REVISION_REJECTED", label: "Cost Revision Rejected" },
    { value: "MANUAL_OVERRIDE", label: "Manual Override" },
  ];

  return (
    <div className="w-full">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Cost History</h2>
        <p className="text-gray-600">
          {materialName} — Append-only audit log of all cost changes
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded text-red-800">
          Error: {error}
        </div>
      )}

      {/* Filter */}
      <div className="mb-6 flex gap-3 items-center">
        <label htmlFor="filter" className="text-sm font-medium text-gray-700">
          Filter by Change Type:
        </label>
        <select
          id="filter"
          value={filterChangeType || ""}
          onChange={(e) => {
            setFilterChangeType(e.target.value || null);
            setCurrentPage(1);
          }}
          className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Types</option>
          {changeTypeOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Loading State */}
      {loading && !history.length ? (
        <div className="text-center py-8 text-gray-500">Loading cost history...</div>
      ) : history.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No cost history entries found</div>
      ) : (
        <>
          {/* History Timeline */}
          <div className="space-y-4 mb-6">
            {history.map((entry) => (
              <div
                key={entry.id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                {/* Entry Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      {getChangeTypeBadge(entry.change_type)}
                      <span className="text-gray-500 text-xs">
                        ID: {entry.id.slice(0, 8)}...
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">
                      {new Date(entry.created_at).toLocaleDateString()}{" "}
                      {new Date(entry.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                </div>

                {/* Cost Change */}
                <div className="mb-3 p-3 bg-gray-50 rounded">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Previous Cost</p>
                      <p className="text-lg font-semibold text-gray-900">
                        {entry.old_cost !== null ? `₹${entry.old_cost.toFixed(6)}` : "N/A"}
                      </p>
                    </div>
                    <div className="text-2xl text-gray-400">→</div>
                    <div>
                      <p className="text-sm text-gray-600">New Cost</p>
                      <p className="text-lg font-semibold text-green-700">
                        ₹{entry.new_cost.toFixed(6)}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Details */}
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-gray-500">Source</p>
                    <p className="text-gray-900">{getSourceBadge(entry.source_type)}</p>
                  </div>
                  {entry.source_id && (
                    <div>
                      <p className="text-gray-500">Source ID</p>
                      <p className="text-gray-900 font-mono text-xs">{entry.source_id.slice(0, 8)}...</p>
                    </div>
                  )}
                  {entry.approved_by && (
                    <div>
                      <p className="text-gray-500">Approved By</p>
                      <p className="text-gray-900">{entry.approved_by}</p>
                    </div>
                  )}
                  {entry.notes && (
                    <div className="col-span-2">
                      <p className="text-gray-500">Notes</p>
                      <p className="text-gray-900">{entry.notes}</p>
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
