import React, { useMemo } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { StandardCostRevision } from "@/modules/procurement/types/pricing";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { format } from "date-fns";

interface MaterialCostHistoryProps {
  materialId: string;
  revisions: StandardCostRevision[];
  loading?: boolean;
}

/**
 * Material Cost History Component
 * Displays complete audit trail of cost revisions for a material
 * Shows all statuses: PENDING, APPROVED, REJECTED
 */
export const MaterialCostHistory: React.FC<MaterialCostHistoryProps> = ({
  revisions,
  loading = false,
}) => {
  // Define columns for history table
  const historyColumns = useMemo<ColumnDef<StandardCostRevision>[]>(
    () => [
      {
        accessorKey: "requested_cost",
        header: "Proposed Cost",
        cell: (info) => (
          <span className="font-medium text-gray-900">
            {(info.getValue() as number).toFixed(2)}
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: (info) => (
          <StatusBadge
            status={(info.getValue() as string) || "PENDING"}
            colorMap={{
              "PENDING": "border-amber-200 bg-amber-50 text-amber-700",
              "APPROVED": "border-green-200 bg-green-50 text-green-700",
              "REJECTED": "border-red-200 bg-red-50 text-red-700",
            }}
          />
        ),
      },
      {
        accessorKey: "reason",
        header: "Reason",
        cell: (info) => (
          <span className="text-gray-600 text-sm truncate max-w-xs">
            {info.getValue() as string}
          </span>
        ),
      },
      {
        accessorKey: "requested_by",
        header: "Requested By",
        cell: (info) => (
          <span className="text-gray-600 text-sm">
            {(info.getValue() as string).slice(0, 8).toUpperCase()}
          </span>
        ),
      },
      {
        accessorKey: "created_at",
        header: "Date",
        cell: (info) => (
          <span className="text-gray-600 text-sm">
            {format(new Date(info.getValue() as string), "MMM d, yyyy HH:mm")}
          </span>
        ),
      },
      {
        accessorFn: (revision) => {
          if (revision.status === "REJECTED") {
            return `Rejected: ${revision.rejection_reason || "No reason provided"}`;
          }
          if (revision.status === "APPROVED") {
            return `Approved by ${revision.approved_by?.slice(0, 8).toUpperCase() || "Direct save"}`;
          }
          return "Pending review";
        },
        id: "statusDetails",
        header: "Details",
        cell: (info) => (
          <span className="text-gray-600 text-sm truncate max-w-xs">
            {info.getValue() as string}
          </span>
        ),
      },
    ],
    []
  );

  if (!revisions || revisions.length === 0) {
    return (
      <div className="p-6 bg-gray-50 rounded border border-gray-200 text-center">
        <p className="text-gray-600">No cost history available for this material</p>
      </div>
    );
  }

  // Sort by created_at descending (newest first)
  const sortedRevisions = [...revisions].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Cost History</h3>
        <p className="text-sm text-gray-600 mt-1">
          Complete audit trail of cost revisions ({sortedRevisions.length} records)
        </p>
      </div>

      {loading ? (
        <div className="p-6 text-center">
          <div className="inline-block animate-spin h-6 w-6 border-3 border-blue-500 border-t-transparent rounded-full" />
          <p className="mt-2 text-gray-600">Loading history...</p>
        </div>
      ) : (
        <DataTable
          columns={historyColumns}
          data={sortedRevisions}
          searchKey="reason"
          searchPlaceholder="Search by reason..."
        />
      )}
    </div>
  );
};
