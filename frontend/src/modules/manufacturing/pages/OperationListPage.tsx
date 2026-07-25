// Operation Master & Workstations Management - Combined Page with Tabs

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, useMemo } from "react"
import { operationService, Operation } from "@/services/operation.service"
import { workstationsService, Workstation } from "@/services/workstations.service"
import { DataTable } from "@/components/shared/DataTable"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Plus, Pencil, Trash2, Eye, EyeOff } from "lucide-react"
import { useSearchParams } from "react-router-dom"
import { ColumnDef } from "@tanstack/react-table"
import { usePermissions } from "@/hooks/usePermissions"
import { TableSkeleton } from "@/components/shared/LoadingSkeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { OperationFormDrawer } from "../components/OperationFormDrawer"
import { WorkstationFormDrawer } from "../components/WorkstationFormDrawer"
import { toast } from "sonner"

export default function OperationListPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchQuery, setSearchQuery] = useState("")
  const [workstationSearch, setWorkstationSearch] = useState("")
  const [activeTab, setActiveTab] = useState("operations")
  const { canWrite } = usePermissions()
  const queryClient = useQueryClient()

  // Get IDs from URL params
  const operationId = searchParams.get("operationId")
  const workstationId = searchParams.get("workstationId")
  const isOperationDrawerOpen = operationId !== null
  const isWorkstationDrawerOpen = workstationId !== null

  const handleCloseOperationDrawer = () => {
    const newParams = new URLSearchParams(searchParams)
    newParams.delete("operationId")
    setSearchParams(newParams)
  }

  const handleCloseWorkstationDrawer = () => {
    const newParams = new URLSearchParams(searchParams)
    newParams.delete("workstationId")
    setSearchParams(newParams)
  }

  // Fetch operations
  const { data: operationsData, isLoading: isFetchingOperations } = useQuery({
    queryKey: ["operations", searchQuery],
    queryFn: () => operationService.listOperations({
      query: searchQuery || undefined,
    }),
  })

  // Fetch workstations
  const { data: workstationsData = [], isLoading: isFetchingWorkstations } = useQuery({
    queryKey: ["workstations"],
    queryFn: () => workstationsService.listWorkstations(),
  })

  // Deactivate operation
  const deactivateMutation = useMutation({
    mutationFn: (id: string) => operationService.deactivateOperation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operations"] })
      toast.success("Operation deactivated")
    },
  })

  // Reactivate operation
  const reactivateMutation = useMutation({
    mutationFn: (id: string) => operationService.reactivateOperation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operations"] })
      toast.success("Operation reactivated")
    },
  })

  // Delete workstation
  const deleteWorkstationMutation = useMutation({
    mutationFn: (id: string) => workstationsService.deleteWorkstation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workstations"] })
      toast.success("Workstation deleted successfully")
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to delete workstation")
    },
  })

  // Define operation columns
  const operationColumns = useMemo<ColumnDef<Operation>[]>(() => [
    {
      accessorKey: "operation_code",
      header: "Code",
      cell: ({ row }) => (
        <span className="font-mono font-medium text-primary text-sm">{row.original.operation_code}</span>
      ),
    },
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <span className="font-medium text-sm">{row.original.name}</span>
      ),
    },
    {
      accessorKey: "operation_type",
      header: "Type",
      cell: ({ row }) => (
        <span className="capitalize text-xs text-muted-foreground">
          {row.original.operation_type}
        </span>
      ),
    },
    {
      accessorKey: "default_sequence",
      header: "Seq",
      cell: ({ row }) => (
        <span className="font-mono text-sm">{row.original.default_sequence}</span>
      ),
    },
    {
      accessorKey: "estimated_time_minutes",
      header: "Time (min)",
      cell: ({ row }) => (
        <span className="text-sm">{row.original.estimated_time_minutes ? row.original.estimated_time_minutes.toFixed(0) : "-"}</span>
      ),
    },
    {
      id: "qc_required",
      header: "QC",
      cell: ({ row }) => (
        row.original.qc_required ? (
          <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-1 text-xs font-medium text-amber-700">
            Yes
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">No</span>
        )
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
      header: "Actions",
      cell: ({ row }) => {
        return (
          <div className="flex gap-1 justify-end">
            {canWrite() && (
              <>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setSearchParams({ operationId: row.original.id })}
                  title="Edit operation"
                  className="h-8 w-8 p-0"
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                {row.original.is_active ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deactivateMutation.mutate(row.original.id)}
                    disabled={deactivateMutation.isPending}
                    title="Deactivate operation"
                    className="h-8 w-8 p-0"
                  >
                    <EyeOff className="h-4 w-4 text-amber-600" />
                  </Button>
                ) : (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => reactivateMutation.mutate(row.original.id)}
                    disabled={reactivateMutation.isPending}
                    title="Reactivate operation"
                    className="h-8 w-8 p-0"
                  >
                    <Eye className="h-4 w-4 text-green-600" />
                  </Button>
                )}
              </>
            )}
          </div>
        )
      },
    },
  ], [canWrite, deactivateMutation, reactivateMutation, setSearchParams])

  // Define workstation columns
  const workstationColumns = useMemo<ColumnDef<Workstation>[]>(() => [
    {
      accessorKey: "code",
      header: "Code",
      cell: ({ row }) => (
        <span className="font-mono font-medium text-primary text-sm">{row.original.code}</span>
      ),
    },
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <span className="font-medium text-sm">{row.original.name}</span>
      ),
    },
    {
      accessorKey: "capacity_hours_per_day",
      header: "Capacity (hrs/day)",
      cell: ({ row }) => (
        <span className="text-sm">{row.original.capacity_hours_per_day.toFixed(1)}</span>
      ),
    },
    {
      accessorKey: "hourly_rate",
      header: "Hourly Rate",
      cell: ({ row }) => (
        <span className="font-mono text-sm">₹{row.original.hourly_rate.toFixed(2)}</span>
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
      header: "Actions",
      cell: ({ row }) => {
        return (
          <div className="flex gap-1 justify-end">
            {canWrite() && (
              <>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setSearchParams({ workstationId: row.original.id })}
                  title="Edit workstation"
                  className="h-8 w-8 p-0"
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => {
                    if (window.confirm(`Delete workstation "${row.original.name}"? This action cannot be undone.`)) {
                      deleteWorkstationMutation.mutate(row.original.id)
                    }
                  }}
                  disabled={deleteWorkstationMutation.isPending}
                  title="Delete workstation"
                  className="h-8 w-8 p-0"
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </>
            )}
          </div>
        )
      },
    },
  ], [canWrite, deleteWorkstationMutation, setSearchParams])

  const operationItems = operationsData?.items || []
  // Filter workstations by search query
  const workstationItems = workstationsData.filter((ws) =>
    !workstationSearch ||
    ws.code.toLowerCase().includes(workstationSearch.toLowerCase()) ||
    ws.name.toLowerCase().includes(workstationSearch.toLowerCase())
  )

  return (
    <div className="w-full space-y-6 pb-6">
      <PageHeader
        title="Manufacturing Master"
        description="Manage operations and workstations - the foundation of your production process"
      />

      {/* Tab Navigation */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2 mb-6">
          <TabsTrigger value="operations" className="flex items-center gap-2">
            <span>Operations</span>
            {operationItems.length > 0 && (
              <span className="ml-1 inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                {operationItems.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="workstations" className="flex items-center gap-2">
            <span>Workstations</span>
            {workstationItems.length > 0 && (
              <span className="ml-1 inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                {workstationItems.length}
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Operations Tab */}
        <TabsContent value="operations" className="space-y-4">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div className="flex-1 max-w-sm">
              <Input
                placeholder="Search operations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full"
              />
            </div>
            {canWrite() && (
              <Button 
                onClick={() => setSearchParams({ operationId: "new" })}
                className="w-full md:w-auto"
              >
                <Plus className="mr-2 h-4 w-4" />
                New Operation
              </Button>
            )}
          </div>

          {isFetchingOperations ? (
            <TableSkeleton rows={5} />
          ) : operationItems.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <div className="text-center">
                  <h3 className="text-lg font-semibold text-muted-foreground">No operations yet</h3>
                  <p className="text-sm text-muted-foreground mt-2">
                    Create your first operation like Cutting, Assembly, or Inspection.
                  </p>
                  {canWrite() && (
                    <Button
                      onClick={() => setSearchParams({ operationId: "new" })}
                      className="mt-4"
                      variant="default"
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      Create First Operation
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="w-full overflow-x-auto rounded-lg border">
              <DataTable columns={operationColumns} data={operationItems} />
            </div>
          )}
        </TabsContent>

        {/* Workstations Tab */}
        <TabsContent value="workstations" className="space-y-4">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div className="flex-1 max-w-sm">
              <Input
                placeholder="Search workstations..."
                value={workstationSearch}
                onChange={(e) => setWorkstationSearch(e.target.value)}
                className="w-full"
              />
            </div>
            {canWrite() && (
              <Button 
                onClick={() => setSearchParams({ workstationId: "new" })}
                className="w-full md:w-auto"
              >
                <Plus className="mr-2 h-4 w-4" />
                New Workstation
              </Button>
            )}
          </div>

          {isFetchingWorkstations ? (
            <TableSkeleton rows={5} />
          ) : workstationItems.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <div className="text-center">
                  <h3 className="text-lg font-semibold text-muted-foreground">No workstations yet</h3>
                  <p className="text-sm text-muted-foreground mt-2">
                    Set up your production workstations (machines, stations, areas).
                  </p>
                  {canWrite() && (
                    <Button
                      onClick={() => setSearchParams({ workstationId: "new" })}
                      className="mt-4"
                      variant="default"
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      Create First Workstation
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="w-full overflow-x-auto rounded-lg border">
              <DataTable columns={workstationColumns} data={workstationItems} />
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Operation Form Drawer */}
      <OperationFormDrawer
        operationId={operationId && operationId !== "new" ? operationId : undefined}
        isNew={operationId === "new"}
        open={isOperationDrawerOpen}
        onClose={handleCloseOperationDrawer}
      />

      {/* Workstation Form Drawer */}
      <WorkstationFormDrawer
        workstationId={workstationId && workstationId !== "new" ? workstationId : undefined}
        isNew={workstationId === "new"}
        open={isWorkstationDrawerOpen}
        onClose={handleCloseWorkstationDrawer}
      />
    </div>
  )
}
