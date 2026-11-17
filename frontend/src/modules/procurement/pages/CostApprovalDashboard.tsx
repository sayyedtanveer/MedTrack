import React, { useState } from "react";
import { CheckCircle2, XCircle, Loader } from "lucide-react";
import { useCostApprovals } from "@/modules/procurement/hooks/useCostApprovals";

interface RejectDialogState {
  revisionId: string | null;
  materialCode: string | null;
  isOpen: boolean;
}

/**
 * Cost Approval Dashboard
 * Displays pending cost revisions for manager approval
 * Allows bulk and individual approve/reject actions
 */
export const CostApprovalDashboard: React.FC = () => {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const { pendingRevisions, totalPending, loading, error, approve, reject, approvingId, rejectingId } =
    useCostApprovals(page, pageSize);

  const [rejectDialog, setRejectDialog] = useState<RejectDialogState>({
    revisionId: null,
    materialCode: null,
    isOpen: false,
  });
  const [rejectionReason, setRejectionReason] = useState<string>("");
  const [rejectError, setRejectError] = useState<string | null>(null);

  const handleOpenRejectDialog = (revisionId: string, materialCode: string) => {
    setRejectDialog({
      revisionId,
      materialCode,
      isOpen: true,
    });
    setRejectionReason("");
    setRejectError(null);
  };

  const handleCloseRejectDialog = () => {
    setRejectDialog({
      revisionId: null,
      materialCode: null,
      isOpen: false,
    });
    setRejectionReason("");
    setRejectError(null);
  };

  const handleConfirmReject = async () => {
    if (!rejectDialog.revisionId) return;

    if (!rejectionReason.trim()) {
      setRejectError("Rejection reason is required");
      return;
    }

    try {
      await reject(rejectDialog.revisionId, rejectionReason.trim());
      handleCloseRejectDialog();
    } catch (err) {
      setRejectError(err instanceof Error ? err.message : "Failed to reject revision");
    }
  };

  const handleApprove = async (revisionId: string) => {
    try {
      await approve(revisionId);
    } catch (err) {
      console.error("Failed to approve:", err);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center">
        <div className="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
        <p className="mt-4 text-gray-600">Loading pending approvals...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-300 rounded p-4 text-red-700">
          <p className="font-medium">Error loading approvals</p>
          <p className="text-sm mt-1">{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Cost Approval Queue</h1>
        <p className="mt-2 text-gray-600">
          Manage pending cost revision approvals ({totalPending} items)
        </p>
      </div>

      {/* Pending Revisions Table */}
      {pendingRevisions.length === 0 ? (
        <div className="bg-green-50 border border-green-300 rounded p-6 text-center">
          <CheckCircle2 className="w-12 h-12 text-green-600 mx-auto mb-3" />
          <p className="text-green-800 font-medium">No pending approvals</p>
          <p className="text-green-700 text-sm mt-1">All cost revisions have been processed</p>
        </div>
      ) : (
        <div className="overflow-x-auto bg-white rounded-lg border border-gray-200">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Material Code
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Requested By
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Current Cost
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Proposed Cost
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Variance
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                  Reason
                </th>
                <th className="px-6 py-3 text-right text-sm font-semibold text-gray-700">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {pendingRevisions.map((revision) => {
                const variance = revision.variance_percent || 0;
                const isApproving = approvingId === revision.id;
                const isRejecting = rejectingId === revision.id;

                return (
                  <tr key={revision.id} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      {/* Material code would be populated from backend */}
                      {revision.material_id.slice(0, 8).toUpperCase()}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {revision.requested_by.slice(0, 8).toUpperCase()}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {revision.current_cost.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      {revision.requested_cost.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                          variance > 0
                            ? "bg-red-100 text-red-800"
                            : variance < 0
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {variance > 0 ? "+" : ""}{variance.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      <span className="truncate block max-w-xs">{revision.reason}</span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={() => handleApprove(revision.id)}
                          disabled={isApproving || isRejecting}
                          className="inline-flex items-center gap-1 px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isApproving ? (
                            <Loader className="w-4 h-4 animate-spin" />
                          ) : (
                            <CheckCircle2 className="w-4 h-4" />
                          )}
                          Approve
                        </button>
                        <button
                          onClick={() =>
                            handleOpenRejectDialog(revision.id, revision.material_id)
                          }
                          disabled={isApproving || isRejecting}
                          className="inline-flex items-center gap-1 px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isRejecting ? (
                            <Loader className="w-4 h-4 animate-spin" />
                          ) : (
                            <XCircle className="w-4 h-4" />
                          )}
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPending > pageSize && (
        <div className="flex justify-center items-center gap-4">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">
            Page {page} of {Math.ceil(totalPending / pageSize)}
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page >= Math.ceil(totalPending / pageSize)}
            className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}

      {/* Reject Confirmation Dialog */}
      {rejectDialog.isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h2 className="text-xl font-bold mb-2">Reject Cost Revision</h2>
            <p className="text-gray-600 text-sm mb-6">
              Material: {rejectDialog.materialCode}
            </p>

            {/* Rejection Reason */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rejection Reason <span className="text-red-500">*</span>
              </label>
              <textarea
                rows={3}
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Why are you rejecting this cost proposal?"
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
              />
            </div>

            {/* Error Message */}
            {rejectError && (
              <div className="mt-3 p-3 bg-red-50 border border-red-300 rounded text-red-700 text-sm">
                {rejectError}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 justify-end mt-6">
              <button
                onClick={handleCloseRejectDialog}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmReject}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CostApprovalDashboard;
