/**
 * Pending Cost Revisions Panel Component
 * Displays cost revisions awaiting approval for Finance/Costing managers
 * Phase 2e Frontend Integration
 */

import React, { useState, useEffect } from "react";
import { StandardCostRevision } from "../types/pricing";
import { useCostRevisions } from "../hooks/useCostRevisions";

interface PendingCostRevisionsPanelProps {
  onRevisionApproved?: (revision: StandardCostRevision) => void;
  onRevisionRejected?: (revision: StandardCostRevision) => void;
}

export const PendingCostRevisionsPanel: React.FC<PendingCostRevisionsPanelProps> = ({
  onRevisionApproved,
  onRevisionRejected,
}) => {
  const {
    pendingRevisions,
    loading,
    error,
    currentPage,
    totalPages,
    fetchPendingRevisions,
    approveRevision,
    rejectRevision,
    nextPage,
    prevPage,
  } = useCostRevisions();

  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [rejectionReason, setRejectionReason] = useState<Record<string, string>>({});
  const [processingId, setProcessingId] = useState<string | null>(null);

  useEffect(() => {
    fetchPendingRevisions();
  }, []);

  const handleApprove = async (revision: StandardCostRevision) => {
    setProcessingId(revision.id);
    try {
      await approveRevision(revision.id);
      onRevisionApproved?.(revision);
    } catch (err) {
      console.error("Error approving revision:", err);
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (revision: StandardCostRevision) => {
    const reason = rejectionReason[revision.id] || "";
    if (!reason.trim()) {
      alert("Please provide a rejection reason");
      return;
    }

    setProcessingId(revision.id);
    try {
      await rejectRevision(revision.id, reason);
      setRejectionReason((prev) => {
        const newReasons = { ...prev };
        delete newReasons[revision.id];
        return newReasons;
      });
      setExpandedId(null);
      onRevisionRejected?.(revision);
    } catch (err) {
      console.error("Error rejecting revision:", err);
    } finally {
      setProcessingId(null);
    }
  };

  const getReasonBadge = (reason: string) => {
    const reasonMap: Record<string, string> = {
      GRN_VARIANCE: "GRN Variance",
      SUPPLIER_AGREEMENT: "Supplier Agreement",
      VARIANCE_THRESHOLD: "Variance Threshold",
      MANUAL_ADJUSTMENT: "Manual Adjustment",
    };
    return reasonMap[reason] || reason;
  };

  const getReasonColor = (reason: string) => {
    const colorMap: Record<string, string> = {
      GRN_VARIANCE: "bg-orange-100 text-orange-800",
      SUPPLIER_AGREEMENT: "bg-blue-100 text-blue-800",
      VARIANCE_THRESHOLD: "bg-yellow-100 text-yellow-800",
      MANUAL_ADJUSTMENT: "bg-purple-100 text-purple-800",
    };
    return colorMap[reason] || "bg-gray-100 text-gray-800";
  };

  return (
    <div className="w-full">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Pending Cost Revisions</h2>
        <p className="text-gray-600">
          {pendingRevisions.length} revision{pendingRevisions.length !== 1 ? "s" : ""} awaiting approval
        </p>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded text-red-800">
          Error: {error}
        </div>
      )}

      {loading && !pendingRevisions.length ? (
        <div className="text-center py-8 text-gray-500">Loading revisions...</div>
      ) : pendingRevisions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No pending cost revisions</div>
      ) : (
        <>
          {/* Revisions List */}
          <div className="space-y-3 mb-6">
            {pendingRevisions.map((revision) => (
              <div
                key={revision.id}
                className="border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
              >
                {/* Header */}
                <div
                  onClick={() => setExpandedId(expandedId === revision.id ? null : revision.id)}
                  className="p-4 cursor-pointer hover:bg-gray-50 flex items-center justify-between"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${getReasonColor(revision.reason)}`}>
                        {getReasonBadge(revision.reason)}
                      </span>
                      <span className="text-gray-500 text-xs">ID: {revision.id.slice(0, 8)}...</span>
                    </div>
                    <p className="font-semibold text-gray-900">
                      Current: ₹{revision.current_cost.toFixed(6)} → Requested: ₹{revision.requested_cost.toFixed(6)}
                    </p>
                    {revision.variance_percent !== null && (
                      <p className={`text-sm ${revision.variance_percent > 0 ? "text-red-600" : "text-green-600"}`}>
                        Variance: {revision.variance_percent > 0 ? "+" : ""}
                        {revision.variance_percent.toFixed(2)}%
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">{new Date(revision.created_at).toLocaleDateString()}</p>
                    <p className="text-sm font-semibold text-gray-900">
                      {revision.status === "PENDING" ? "⏳ Pending" : revision.status}
                    </p>
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedId === revision.id && (
                  <div className="border-t border-gray-200 bg-gray-50 p-4 space-y-4">
                    {/* Notes */}
                    {revision.notes && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 uppercase mb-1">Reason / Notes</p>
                        <p className="text-gray-700 text-sm">{revision.notes}</p>
                      </div>
                    )}

                    {/* Rejection Reason Input (if reviewing) */}
                    {expandedId === revision.id && revision.status === "PENDING" && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 uppercase mb-1">
                          Rejection Reason (if rejecting)
                        </p>
                        <textarea
                          value={rejectionReason[revision.id] || ""}
                          onChange={(e) =>
                            setRejectionReason((prev) => ({
                              ...prev,
                              [revision.id]: e.target.value,
                            }))
                          }
                          placeholder="Enter reason for rejection (if applicable)..."
                          rows={2}
                          className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    )}

                    {/* Action Buttons */}
                    {revision.status === "PENDING" && (
                      <div className="flex gap-3 justify-end border-t pt-4">
                        <button
                          onClick={() => handleReject(revision)}
                          disabled={processingId === revision.id || !rejectionReason[revision.id]?.trim()}
                          className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:bg-gray-400 text-sm font-semibold"
                        >
                          {processingId === revision.id ? "Processing..." : "Reject"}
                        </button>
                        <button
                          onClick={() => handleApprove(revision)}
                          disabled={processingId === revision.id}
                          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-400 text-sm font-semibold"
                        >
                          {processingId === revision.id ? "Processing..." : "Approve"}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded border border-gray-200">
              <button
                onClick={prevPage}
                disabled={currentPage === 1 || loading}
                className="px-3 py-2 bg-gray-300 text-gray-700 rounded disabled:bg-gray-200 text-sm"
              >
                ← Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={nextPage}
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
