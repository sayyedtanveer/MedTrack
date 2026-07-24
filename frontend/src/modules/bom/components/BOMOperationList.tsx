import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Loader2, GripVertical, AlertCircle, Trash2 } from "lucide-react"
import { bomService } from "@/services/bom.service"
import { BOM } from "@/types/bom.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Lock, Search } from "lucide-react"
import { OperationFormDrawer } from "@/modules/manufacturing/components/OperationFormDrawer"

interface BOMOperationListProps {
  bom: BOM
  canEdit: boolean
}

interface AttachForm {
  operation_id: string
  sequence: string
}

export function BOMOperationList({ bom, canEdit }: BOMOperationListProps) {
  const qc = useQueryClient()
  const [form, setForm] = useState<AttachForm>({ operation_id: "", sequence: "" })
  const [showForm, setShowForm] = useState(false)
  const [attachError, setAttachError] = useState<string | null>(null)
  
  // Search & Inline Create
  const [opSearch, setOpSearch] = useState("")
  const [showCreateOp, setShowCreateOp] = useState(false)

  // Fetch available operations
  const { data: operations, isLoading: loadingOps } = useQuery({
    queryKey: ["operations"],
    queryFn: bomService.getOperations,
    staleTime: 60_000,
  })

  // Fetch workstations for name lookup
  const { data: workstations } = useQuery({
    queryKey: ["workstations"],
    queryFn: bomService.getWorkstations,
    staleTime: 60_000,
  })

  // Attach operation mutation
  const attachMutation = useMutation({
    mutationFn: () =>
      bomService.attachOperation(bom.id, {
        operation_id: form.operation_id,
        sequence: parseInt(form.sequence, 10),
      }),
    onSuccess: () => {
      toast.success("Operation attached")
      qc.invalidateQueries({ queryKey: ["bom", bom.id] })
      setForm({ operation_id: "", sequence: "" })
      setShowForm(false)
      setAttachError(null)
    },
    onError: (err: any) => {
      setAttachError(
        err?.response?.data?.detail || err?.message || "Failed to attach operation"
      )
    },
  })

  const removeMutation = useMutation({
    mutationFn: (bomOperationId: string) => bomService.removeOperation(bom.id, bomOperationId),
    onSuccess: () => {
      toast.success("Operation removed")
      qc.invalidateQueries({ queryKey: ["bom", bom.id] })
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || err?.message || "Failed to remove operation")
    },
  })

  const getWsName = (wsId: string) =>
    workstations?.find((w) => w.id === wsId)?.name ?? wsId.slice(0, 8) + "..."

  const getOp = (opId: string) =>
    operations?.find((o) => o.id === opId)

  // Derive attached operations from BOM (API returns them as part of BOM or we show placeholder)
  // Since the BOM object doesn't directly carry attached operations (only lines),
  // we show a form to attach and note they're managed server-side.
  const attachedOps = (bom as any).operations as { id: string; operation_id: string; sequence: number }[] | undefined

  const usedSequences = new Set(attachedOps?.map((o) => o.sequence) ?? [])
  const selectedOperation = operations?.find((op) => op.id === form.operation_id)

  const nextSequence = () => {
    if (!attachedOps || attachedOps.length === 0) return "10"
    return String(Math.max(...attachedOps.map((o) => o.sequence)) + 10)
  }

  const filteredOperations = (operations ?? []).filter(op =>
    op.name.toLowerCase().includes(opSearch.toLowerCase())
  )

  return (
    <div className="space-y-4">
      {/* Operations table */}
      {loadingOps ? (
        <div className="space-y-2">
          {[1, 2].map((i) => <Skeleton key={i} className="h-12 w-full rounded-md" />)}
        </div>
      ) : !attachedOps || attachedOps.length === 0 ? (
        <div className="flex flex-col items-center justify-center border border-dashed rounded-lg py-10 gap-2 text-muted-foreground">
          <GripVertical className="w-6 h-6" />
          <p className="text-sm">No operations attached to this BOM.</p>
          {canEdit && (
            <Button variant="outline" size="sm" onClick={() => { setShowForm(true); setForm((f) => ({ ...f, sequence: nextSequence() })) }}>
              <Plus className="w-3.5 h-3.5 mr-1.5" />
              Attach First Operation
            </Button>
          )}
          {!canEdit && bom.is_active && (
            <TooltipProvider>
              <Tooltip delayDuration={300}>
                <TooltipTrigger asChild>
                  <div className="inline-block cursor-not-allowed">
                    <Button variant="outline" size="sm" disabled className="pointer-events-none opacity-50">
                      <Plus className="w-3.5 h-3.5 mr-1.5" />
                      Attach First Operation
                    </Button>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Active BOM cannot be edited. Create a new version to modify.</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <div className="overflow-x-auto min-w-0">
            <table className="w-full text-sm">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground w-16">Seq</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground min-w-48">Operation</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground hidden md:table-cell min-w-40">Workstation</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground hidden sm:table-cell w-24">Setup</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground hidden sm:table-cell w-28">Run Time</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {[...attachedOps]
                .sort((a, b) => a.sequence - b.sequence)
                .map((ao) => {
                  const op = getOp(ao.operation_id)
                  
                  return (
                    <tr key={ao.id} className="group hover:bg-muted/20 transition-colors">
                      <td className="px-3 py-2">
                        <Badge variant="outline" className="font-mono text-xs font-semibold bg-muted/50">
                          {ao.sequence}
                        </Badge>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-col gap-0.5">
                          <span className="font-medium">{op?.name ?? "Unknown Operation"}</span>
                          {op?.description && (
                            <span className="text-xs text-muted-foreground line-clamp-1">{op.description}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2 text-muted-foreground hidden md:table-cell">
                        <div className="flex flex-col gap-0.5">
                          <span className="font-medium text-foreground">{op ? getWsName(op.workstation_id) : "—"}</span>
                          {op && (
                            <span className="text-xs text-muted-foreground">
                              {workstations?.find(w => w.id === op.workstation_id)?.capacity_hours_per_day}h/day
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2 text-muted-foreground hidden sm:table-cell">
                        {op ? (
                          <span className="font-mono font-medium">{op.setup_time || 0}m</span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="px-3 py-2 text-muted-foreground hidden sm:table-cell">
                        {op ? (
                          <span className="font-mono font-medium">{op.run_time || 0}m</span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex items-center justify-end gap-1 opacity-100 group-hover:opacity-100 transition-opacity">
                        {canEdit ? (
                          <>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 opacity-0 group-hover:opacity-100 text-destructive hover:bg-destructive/10"
                                title="Delete operation"
                                aria-label="Delete operation"
                                onClick={() => removeMutation.mutate(ao.id)}
                                disabled={removeMutation.isPending}
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </Button>
                            </>
                          ) : bom.is_active ? (
                            <TooltipProvider>
                              <Tooltip delayDuration={300}>
                                <TooltipTrigger asChild>
                                  <div className="inline-block cursor-not-allowed">
                                    <Button variant="ghost" size="sm" disabled className="pointer-events-none opacity-30 h-7 w-7">
                                      <Lock className="w-3.5 h-3.5" />
                                    </Button>
                                  </div>
                                </TooltipTrigger>
                                <TooltipContent side="left">
                                  <p>Active BOM cannot be edited.</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  )
                })}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {/* Attach form */}
      {(canEdit || bom.is_active) && (
        <div className="space-y-3">
          {!showForm ? (
            canEdit ? (
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => { setShowForm(true); setForm((f) => ({ ...f, sequence: nextSequence() })) }}
              >
                <Plus className="w-3.5 h-3.5 mr-1.5" />
                Attach Operation
              </Button>
            ) : (
              <TooltipProvider>
                <Tooltip delayDuration={300}>
                  <TooltipTrigger asChild>
                    <div className="inline-block cursor-not-allowed w-full">
                      <Button variant="outline" size="sm" disabled className="w-full pointer-events-none opacity-50">
                        <Plus className="w-3.5 h-3.5 mr-1.5" />
                        Attach Operation
                      </Button>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Active BOM cannot be edited. Create a new version.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )
          ) : (
            <div className="rounded-lg border bg-muted/20 p-4 space-y-3">
              <h4 className="text-sm font-medium">Attach New Operation</h4>
              <p className="text-xs text-muted-foreground">
                Operations define the routing steps for production. Use sequence numbers like 10, 20, 30 so another step can be inserted later.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Operation selector */}
                <div className="space-y-1.5 sm:col-span-1">
                  <div className="flex items-center justify-between">
                    <Label>Operation</Label>
                    <Button variant="link" size="sm" className="h-auto p-0" onClick={() => setShowCreateOp(true)}>
                      + Create New
                    </Button>
                  </div>
                  {loadingOps ? (
                    <Skeleton className="h-9 w-full" />
                  ) : (
                    <div className="space-y-2">
                      <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input 
                          placeholder="Search operations..." 
                          className="pl-8" 
                          value={opSearch}
                          onChange={(e) => setOpSearch(e.target.value)}
                        />
                      </div>
                      <Select
                        value={form.operation_id}
                        onValueChange={(v) => setForm((f) => ({ ...f, operation_id: v }))}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select operation..." />
                        </SelectTrigger>
                        <SelectContent>
                          {filteredOperations.map((op) => (
                            <SelectItem key={op.id} value={op.id}>
                              <span className="font-medium">{op.name}</span>
                              <span className="text-muted-foreground text-xs ml-2">
                                @ {getWsName(op.workstation_id)}
                              </span>
                            </SelectItem>
                          ))}
                          {filteredOperations.length === 0 && (
                            <div className="py-2 text-center text-sm text-muted-foreground">No operations found.</div>
                          )}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                </div>

                {/* Sequence — manual input */}
                <div className="space-y-1.5">
                  <Label>
                    Sequence
                    <span className="text-xs text-muted-foreground ml-1">(manual)</span>
                  </Label>
                  <Input
                    type="number"
                    min={1}
                    step={10}
                    placeholder="e.g. 10, 20, 30"
                    value={form.sequence}
                    onChange={(e) => setForm((f) => ({ ...f, sequence: e.target.value }))}
                    className={cn(
                      usedSequences.has(parseInt(form.sequence, 10)) && form.sequence
                        ? "border-destructive"
                        : ""
                    )}
                  />
                  {usedSequences.has(parseInt(form.sequence, 10)) && form.sequence && (
                    <p className="text-xs text-destructive flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" />
                      Sequence already in use
                    </p>
                  )}
                </div>
              </div>

              {selectedOperation && (
                <div className="rounded-md border bg-card p-3 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">{selectedOperation.name}</span>
                  {" "}runs at {getWsName(selectedOperation.workstation_id)} with {selectedOperation.setup_time || 0} min setup and {selectedOperation.run_time || 0} min per unit.
                </div>
              )}

              {attachError && (
                <Alert variant="destructive">
                  <AlertCircle className="w-4 h-4" />
                  <AlertDescription>{attachError}</AlertDescription>
                </Alert>
              )}

              <div className="flex gap-2 justify-end">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => { setShowForm(false); setAttachError(null) }}
                  disabled={attachMutation.isPending}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={() => attachMutation.mutate()}
                  disabled={
                    !form.operation_id ||
                    !form.sequence ||
                    isNaN(parseInt(form.sequence, 10)) ||
                    usedSequences.has(parseInt(form.sequence, 10)) ||
                    attachMutation.isPending
                  }
                >
                  {attachMutation.isPending && (
                    <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                  )}
                  Attach
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {showCreateOp && (
        <OperationFormDrawer 
          isNew 
          open={showCreateOp} 
          onClose={() => {
            setShowCreateOp(false)
            qc.invalidateQueries({ queryKey: ["operations"] })
          }} 
        />
      )}
    </div>
  )
}
