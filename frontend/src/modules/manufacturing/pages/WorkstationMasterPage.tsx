/**
 * Workstation Master List Page - Admin UI for managing manufacturing workstations.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useMemo } from "react"
import { workstationsService, Workstation } from "@/services/workstations.service"
import { DataTable } from "@/components/shared/DataTable"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Plus, Pencil, Trash2 } from "lucide-react"
import { useSearchParams } from "react-router-dom"
import { ColumnDef } from "@tanstack/react-table"
import { usePermissions } from "@/hooks/usePermissions"
import { TableSkeleton } from "@/components/shared/LoadingSkeleton"
import { toast } from "sonner"
import { WorkstationFormDrawer } from "../components/WorkstationFormDrawer"

export default function WorkstationMasterPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchQuery, setSearchQuery] = useState("")
  const { canWrite } = usePermissions()
  const queryClient = useQueryClient()

  const workstationId = searchParams.get("workstationId")
  const isDrawerOpen = workstationId !== null

  const handleCloseDrawer = () => {
    setSearchParams({})
  }

  // Fetch workstations
  const { data: workstations = [], isLoading: isFetchingWorkstations } = useQuery({
    queryKey: ["workstations"],
    queryFn: () => workstationsService.listWorkstations(),
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => workstationsService.deleteWorkstation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workstations"] })
      toast.success("Workstation deleted successfully")
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to delete workstation")
    },
  })

  // Filter workstations by search query
  const filteredWorkstations = useMemo(() => {
    if (!searchQuery.trim()) return workstations
    const q = searchQuery.toLowerCase()
    return workstations.filter(
      (ws) =>
        ws.code.toLowerCase().includes(q) ||
        ws.name.toLowerCase().includes(q)
    )
  }, [workstations, searchQuery])

  // Define columns
  const columns = useMemo<ColumnDef<Workstation>[]>(() => [
    {
      accessorKey: "code",
      header: "Code",
      cell: ({ row }) => (
        <span className="font-mono font-medium text-primary">{row.original.code}</span>
      ),
    },
    {
      accessorKey: "name",
      header: "Workstation Name",
    },
    {
      accessorKey: "capacity_hours_per_day",
      header: "Capacity (hrs/day)",
      cell: ({ row }) => (
        <span>{row.original.capacity_hours_per_day.toFixed(1)}</span>
      ),
    },
    {
      accessorKey: "hourly_rate",
      header: "Hourly Rate",
      cell: ({ row }) => (
        <span className="font-mono">${row.original.hourly_rate.toFixed(2)}</span>
      ),
    },
    {
      id: "status",
      header: "Status",
      cell: ({ row }) => (
        <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
          row.original.is_active
            ? "bg-green-100 text-green-700"
            : "bg-gray-100 text-gray-700"
        }`}>
          {row.original.is_active ? "Active" : "Inactive"}
        </span>
      ),
    },
    {
      id: "actions",
      cell: ({ row }) => {
        const handleDelete = () => {
          if (window.confirm(`Delete workstation "${row.original.name}"? This action cannot be undone.`)) {
            deleteMutation.mutate(row.original.id)
          }
        }

        return (
          <div className="flex gap-2 justify-end">
            {canWrite() && (
              <>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setSearchParams({ workstationId: row.original.id })}
                  title="Edit workstation"
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={handleDelete}
                  disabled={deleteMutation.isPending}
                  title="Delete workstation"
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </>
            )}
          </div>
        )
      },
    },
  ], [canWrite, deleteMutation, setSearchParams])

  const actionButtons = (
    <>
      {canWrite() && (
        <Button onClick={() => setSearchParams({ workstationId: "new" })}>
          <Plus className="mr-2 h-4 w-4" />
          New Workstation
        </Button>
      )}
    </>
  )

  return (
    <div className="w-full space-y-6">
      <PageHeader
        title="Workstations Master"
        description="Manage manufacturing workstations, capacity planning, and costing. Each operation is routed through specific workstations."
        action={actionButtons}
      />

      {/* Search Input */}
      <div className="flex gap-2">
        <div className="flex-1 max-w-md">
          <Input
            placeholder="Search by code or name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full"
          />
        </div>
      </div>

      {isFetchingWorkstations ? (
        <TableSkeleton rows={8} />
      ) : filteredWorkstations.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <div className="text-center">
              <h3 className="text-lg font-semibold text-muted-foreground">
                {searchQuery ? "No workstations found" : "No workstations yet"}
              </h3>
              <p className="text-sm text-muted-foreground mt-2">
                {searchQuery
                  ? "Try adjusting your search terms"
                  : "Create your first workstation (e.g., Assembly Line 1, CNC Machine 1)"}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <DataTable columns={columns} data={filteredWorkstations} />
          </CardContent>
        </Card>
      )}

      {isDrawerOpen && (
        <WorkstationFormDrawer
          workstationId={workstationId === "new" ? undefined : workstationId}
          isNew={workstationId === "new"}
          open={isDrawerOpen}
          onClose={handleCloseDrawer}
        />
      )}
    </div>
  )
}
