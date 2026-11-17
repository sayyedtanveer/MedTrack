import React, { useState, useMemo } from "react";
import { ColumnDef, CellContext } from "@tanstack/react-table";
import { Material } from "@/types/material.types";
import { useMaterialsForBuy } from "@/modules/inventory/hooks/useMaterialsForBuy";
import { DataTable } from "@/components/shared/DataTable";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ProposeCostDialog } from "@/modules/inventory/components/ProposeCostDialog";
import { ApprovalDialog } from "@/modules/inventory/components/ApprovalDialog";
import { useAuth } from "@/hooks/useAuth";
import ErrorBanner from "@/components/shared/ErrorBanner";
import { Loader2 } from "lucide-react";

interface ApprovalDialogState {
  revisionId: string | null;
  materialId: string | null;
  materialCode: string | null;
  isOpen: boolean;
  isReject: boolean;
}

/**
 * Material Buy Tab Component
 * Displays materials grouped by cost status using DataTable
 * Allows proposing costs and approving/rejecting (for managers)
 */
export const MaterialBuyTab: React.FC = () => {
  const {
    notConfiguredMaterials,
    pendingApprovalMaterials,
    configuredMaterials,
    loading,
    error,
    refetch,
  } = useMaterialsForBuy();

  const { user } = useAuth();
  const isManager = user?.role && ["MANAGER", "TENANT_ADMIN"].includes(user.role);

  const [selectedMaterial, setSelectedMaterial] = useState<Material | null>(null);
  const [showProposeCostDialog, setShowProposeCostDialog] = useState<boolean>(false);
  const [approvalDialog, setApprovalDialog] = useState<ApprovalDialogState>({
    revisionId: null,
    materialId: null,
    materialCode: null,
    isOpen: false,
    isReject: false,
  });

  const handleProposeClick = (material: Material) => {
    setSelectedMaterial(material);
    setShowProposeCostDialog(true);
  };

  const handleProposeCostSuccess = async () => {
    await refetch();
  };

  const handleApproveClick = (material: Material) => {
    setApprovalDialog({
      revisionId: material.id,
      materialId: material.id,
      materialCode: material.code,
      isOpen: true,
      isReject: false,
    });
  };

  const handleRejectClick = (material: Material) => {
    setApprovalDialog({
      revisionId: material.id,
      materialId: material.id,
      materialCode: material.code,
      isOpen: true,
      isReject: true,
    });
  };

  const handleCloseApprovalDialog = () => {
    setApprovalDialog({
      revisionId: null,
      materialId: null,
      materialCode: null,
      isOpen: false,
      isReject: false,
    });
  };

  // Define columns for Not Configured table
  const notConfiguredColumns = useMemo<ColumnDef<Material>[]>(
    () => [
      {
        accessorKey: "code",
        header: "Code",
        cell: (info: CellContext<Material, unknown>) => (
          <span className="font-medium text-gray-900">{info.getValue() as string}</span>
        ),
      },
      {
        accessorKey: "name",
        header: "Name",
        cell: (info) => <span className="text-gray-600">{info.getValue() as string}</span>,
      },
      {
        accessorKey: "available_stock",
        header: "Stock",
        cell: (info: CellContext<Material, unknown>) => (
          <span className="text-gray-600">
            {(info.getValue() as number)?.toFixed(2) || "0"}
          </span>
        ),
      },
      {
        accessorKey: "current_cost",
        header: "Current Cost",
        cell: (info: CellContext<Material, unknown>) => (
          <span className="text-gray-600">
            {(info.getValue() as number)?.toFixed(2) || "0.00"}
          </span>
        ),
      },
      {
        id: "action",
        header: "Action",
        cell: (info: CellContext<Material, unknown>) => (
          <button
            onClick={() => handleProposeClick(info.row.original)}
            className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
          >
            Propose Cost
          </button>
        ),
      },
    ],
    []
  );

  // Define columns for Pending Approval table
  const pendingApprovalColumns = useMemo<ColumnDef<Material>[]>(
    () => [
      {
        accessorKey: "code",
        header: "Code",
        cell: (info: CellContext<Material, unknown>) => (
          <span className="font-medium text-gray-900">{info.getValue() as string}</span>
        ),
      },
      {
        accessorKey: "name",
        header: "Name",
        cell: (info) => <span className="text-gray-600">{info.getValue() as string}</span>,
      },
      {
        accessorKey: "available_stock",
        header: "Stock",
        cell: (info: CellContext<Material, unknown>) => (
          <span className="text-gray-600">
            {(info.getValue() as number)?.toFixed(2) || "0"}
          </span>
        ),
      },
      {
        accessorKey: "current_cost",
        header: "Current Cost",
        cell: (info: CellContext<Material, unknown>) => (
          <span className="text-gray-600">
            {(info.getValue() as number)?.toFixed(2) || "0.00"}
          </span>
        ),
      },
      {
        accessorKey: "cost_status",
        header: "Status",
        cell: (info: CellContext<Material, unknown>) => (
          <StatusBadge
            status={(info.getValue() as string) || ""}
            colorMap={{
              "CONFIGURED": "border-green-200 bg-green-50 text-green-700",
              "NOT_CONFIGURED": "border-red-200 bg-red-50 text-red-700",
              "PENDING_APPROVAL": "border-amber-200 bg-amber-50 text-amber-700",
              "LEGACY": "border-slate-200 bg-slate-100 text-slate-600"
            }}
          />
        ),
      },
      ...(isManager ? [{
        id: "actions",
        header: "Actions",
        cell: (info: CellContext<Material, unknown>) => (
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => handleApproveClick(info.row.original)}
              className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
            >
              Approve
            </button>
            <button
              onClick={() => handleRejectClick(info.row.original)}
              className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
            >
              Reject
            </button>
          </div>
        ),
      }] : []),
    ],
    [isManager]
  );

  // Define columns for Configured table
  const configuredColumns = useMemo<ColumnDef<Material>[]>(
    () => [
      {
        accessorKey: "code",
        header: "Code",
        cell: (info: CellContext<Material, unknown>) => (
          <span className="font-medium text-gray-900">{info.getValue() as string}</span>
        ),
      },
      {
        accessorKey: "name",
        header: "Name",
        cell: (info) => <span className="text-gray-600">{info.getValue() as string}</span>,
      },
      {
        accessorKey: "available_stock",
        header: "Stock",
        cell: (info: CellContext<Material, unknown>) => (
          <span className="text-gray-600">
            {(info.getValue() as number)?.toFixed(2) || "0"}
          </span>
        ),
      },
      {
        accessorKey: "current_cost",
        header: "Cost",
        cell: (info: CellContext<Material, unknown>) => (
          <span className="text-green-700 font-medium">
            {(info.getValue() as number)?.toFixed(2) || "0.00"}
          </span>
        ),
      },
    ],
    []
  );

  if (loading) {
    return (
      <div className="p-8 text-center">
        <Loader2 className="inline-block animate-spin h-8 w-8 text-blue-500 mb-4" />
        <p className="text-gray-600">Loading materials...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <ErrorBanner
          message={error.message || "Error loading materials"}
          onRetry={refetch}
        />
      </div>
    );
  }

  return (
    <div className="space-y-8 p-6">
      {/* Not Configured Materials */}
      <div>
        <div className="mb-4 flex items-center gap-2">
          <span className="inline-block w-3 h-3 bg-red-500 rounded-full" />
          <h3 className="text-lg font-bold text-gray-900">
            Not Configured ({notConfiguredMaterials.length})
          </h3>
        </div>

        {notConfiguredMaterials.length === 0 ? (
          <p className="text-gray-500 text-sm">All materials have costs configured.</p>
        ) : (
          <DataTable
            columns={notConfiguredColumns}
            data={notConfiguredMaterials}
          />
        )}
      </div>

      {/* Pending Approval Materials - Show to Managers */}
      {pendingApprovalMaterials.length > 0 && (
        <div>
          <div className="mb-4 flex items-center gap-2">
            <span className="inline-block w-3 h-3 bg-yellow-500 rounded-full" />
            <h3 className="text-lg font-bold text-gray-900">
              Pending Approval ({pendingApprovalMaterials.length})
            </h3>
          </div>

          <DataTable
            columns={pendingApprovalColumns}
            data={pendingApprovalMaterials}
          />
        </div>
      )}

      {/* Configured Materials (Summary) */}
      {configuredMaterials.length > 0 && (
        <div className="pt-4 border-t border-gray-200">
          <details className="cursor-pointer">
            <summary className="text-lg font-bold text-gray-900 flex items-center gap-2 pb-4">
              <span className="inline-block w-3 h-3 bg-green-500 rounded-full" />
              Configured ({configuredMaterials.length})
            </summary>

            <div className="mt-4">
              <DataTable
                columns={configuredColumns}
                data={configuredMaterials}
              />
            </div>
          </details>
        </div>
      )}

      {/* Propose Cost Dialog */}
      <ProposeCostDialog
        material={selectedMaterial}
        isOpen={showProposeCostDialog}
        onClose={() => {
          setShowProposeCostDialog(false);
          setSelectedMaterial(null);
        }}
        onSuccess={handleProposeCostSuccess}
      />

      {/* Approval Dialog */}
      <ApprovalDialog
        isOpen={approvalDialog.isOpen}
        onClose={handleCloseApprovalDialog}
        materialCode={approvalDialog.materialCode}
        revisionId={approvalDialog.revisionId}
        isReject={approvalDialog.isReject}
        onSuccess={async () => {
          handleCloseApprovalDialog();
          await refetch();
        }}
      />
    </div>
  );
};
