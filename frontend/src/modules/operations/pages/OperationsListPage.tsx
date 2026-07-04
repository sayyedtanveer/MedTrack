import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Pencil, Trash2, Search, Clock, Wrench } from "lucide-react"
import { operationsService } from "@/services/operations.service"
import { workstationsService } from "@/services/workstations.service"
import { usePermissions } from "@/hooks/usePermissions"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { PageHeader } from "@/components/layout/PageHeader"
import ResponsiveDataList from "@/components/shared/ResponsiveDataList"
import { toast } from "sonner"

export default function OperationsListPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { hasRole } = usePermissions()
  const canEdit = hasRole(["ADMIN", "MANAGER"])

  const [search, setSearch] = useState("")

  const { data: operations = [], isLoading } = useQuery({
    queryKey: ["operations"],
    queryFn: operationsService.listOperations,
    staleTime: 30_000,
  })

  const { data: workstations = [] } = useQuery({
    queryKey: ["workstations"],
    queryFn: workstationsService.listWorkstations,
    staleTime: 60_000,
  })

  const wsMap = Object.fromEntries(workstations.map((w) => [w.id, w.name]))

  const deleteMutation = useMutation({
    mutationFn: (id: string) => operationsService.deleteOperation(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operations"] })
      toast.success("Operation deleted")
    },
    onError: () => toast.error("Failed to delete operation"),
  })

  const handleDelete = (id: string, name: string) => {
    if (window.confirm(`Delete operation "${name}"? This action cannot be undone.`)) {
      deleteMutation.mutate(id)
    }
  }

  const filtered = operations.filter((op) =>
    op.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="w-full space-y-6">
      <PageHeader
        title="Operations"
        description="Manage the global manufacturing operations catalog."
        action={
          canEdit ? (
            <Button onClick={() => navigate("/operations/new")}>
              <Plus className="w-4 h-4 mr-2" />
              New Operation
            </Button>
          ) : undefined
        }
      />

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Search operations..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="py-16 text-center text-muted-foreground">Loading operations...</div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center border border-dashed rounded-xl">
          <Wrench className="w-10 h-10 text-muted-foreground mb-3" />
          <p className="text-lg font-medium">No operations found</p>
          <p className="text-sm text-muted-foreground mb-4">
            {search ? "Try a different search." : "Create your first operation to get started."}
          </p>
          {canEdit && !search && (
            <Button onClick={() => navigate("/operations/new")}>
              <Plus className="w-4 h-4 mr-2" />
              New Operation
            </Button>
          )}
        </div>
      ) : (
        <ResponsiveDataList
          data={filtered}
          getRowKey={(op) => op.id}
          columns={[
            {
              key: "name",
              header: "Name",
              cell: (op) => (
                <div>
                  <div className="font-medium">{op.name}</div>
                  {op.description && (
                    <div className="mt-0.5 max-w-xs truncate text-xs text-muted-foreground">{op.description}</div>
                  )}
                </div>
              ),
            },
            {
              key: "workstation",
              header: "Workstation",
              cell: (op) =>
                op.workstation_id ? (
                  <Badge variant="secondary" className="font-normal">
                    {wsMap[op.workstation_id] ?? op.workstation_id.slice(0, 8)}
                  </Badge>
                ) : (
                  <span className="text-xs text-muted-foreground">Unassigned</span>
                ),
            },
            {
              key: "setup_time",
              header: "Setup (min)",
              headerClassName: "text-right",
              className: "text-right",
              cell: (op) => (
                <span className="inline-flex items-center justify-end gap-1">
                  <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                  {op.setup_time}
                </span>
              ),
            },
            {
              key: "run_time",
              header: "Run Time (min/unit)",
              headerClassName: "text-right",
              className: "text-right",
              cell: (op) => (
                <span className="inline-flex items-center justify-end gap-1">
                  <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                  {op.run_time}
                </span>
              ),
            },
            ...(canEdit
              ? [{
                  key: "actions",
                  header: "Actions",
                  headerClassName: "text-right",
                  className: "text-right",
                  cell: (op: typeof filtered[number]) => (
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        aria-label="Edit operation"
                        onClick={(event) => {
                          event.stopPropagation()
                          navigate(`/operations/${op.id}/edit`)
                        }}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 hover:text-destructive"
                        aria-label="Delete operation"
                        onClick={(event) => {
                          event.stopPropagation()
                          handleDelete(op.id, op.name)
                        }}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ),
                }]
              : []),
          ]}
          renderMobileCard={(op) => (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-all hover:shadow-md">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-base font-semibold text-slate-900">{op.name}</p>
                  {op.description && <p className="mt-1 text-sm text-slate-500">{op.description}</p>}
                </div>
                {op.workstation_id ? (
                  <Badge variant="secondary" className="font-normal">
                    {wsMap[op.workstation_id] ?? op.workstation_id.slice(0, 8)}
                  </Badge>
                ) : (
                  <span className="text-xs text-muted-foreground">Unassigned</span>
                )}
              </div>
              <div className="mt-4 space-y-2 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-slate-500">Setup</span>
                  <span className="inline-flex items-center gap-1"><Clock className="h-3.5 w-3.5 text-muted-foreground" />{op.setup_time} min</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-slate-500">Run time</span>
                  <span className="inline-flex items-center gap-1"><Clock className="h-3.5 w-3.5 text-muted-foreground" />{op.run_time} min/unit</span>
                </div>
              </div>
              {canEdit && (
                <div className="mt-4 flex flex-col gap-2">
                  <Button variant="outline" className="w-full" onClick={() => navigate(`/operations/${op.id}/edit`)}>
                    <Pencil className="mr-2 h-4 w-4" />
                    Edit
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full hover:text-destructive"
                    onClick={() => handleDelete(op.id, op.name)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </Button>
                </div>
              )}
            </div>
          )}
        />
      )}
    </div>
  )
}
