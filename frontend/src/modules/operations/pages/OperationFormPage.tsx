import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, Save } from "lucide-react"
import { operationsService, CreateOperationInput } from "@/services/operations.service"
import { workstationsService } from "@/services/workstations.service"
import { usePermissions } from "@/hooks/usePermissions"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"

export default function OperationFormPage() {
  const { id } = useParams<{ id: string }>()
  const isNew = !id || id === "new"
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { hasRole } = usePermissions()
  const canEdit = hasRole(["ADMIN", "MANAGER"])

  const [name, setName] = useState("")
  const [operationCode, setOperationCode] = useState("")
  const [description, setDescription] = useState("")
  const [workstationId, setWorkstationId] = useState("")
  const [setupTime, setSetupTime] = useState<number>(0)
  const [runTime, setRunTime] = useState<number>(0)

  // Load workstations for selection
  const { data: workstations = [] } = useQuery({
    queryKey: ["workstations"],
    queryFn: workstationsService.listWorkstations,
    staleTime: 60_000,
  })

  // Load existing operation if editing
  const { data: operations = [] } = useQuery({
    queryKey: ["operations"],
    queryFn: operationsService.listOperations,
    enabled: !isNew,
    staleTime: 30_000,
  })

  useEffect(() => {
    if (!isNew && operations.length > 0) {
      const op = operations.find((o) => o.id === id)
      if (op) {
        setName(op.name)
        setOperationCode(op.operation_code ?? "")
        setDescription(op.description ?? "")
        setWorkstationId(op.workstation_id ?? "")
        if (op.setup_time !== undefined) {
          setSetupTime(op.setup_time)
        }
        if (op.run_time !== undefined) {
          setRunTime(op.run_time)
        }
      }
    }
  }, [operations, id, isNew])

  const mutation = useMutation({
    mutationFn: async () => {
      if (!name.trim()) throw new Error("Name is required")
      if (!workstationId) throw new Error("Workstation is required")
      if (setupTime < 0 || runTime < 0) throw new Error("Times must be non-negative")
      const payload: CreateOperationInput = {
        operation_code: operationCode.trim() || undefined,
        name: name.trim(),
        description: description.trim() || undefined,
        workstation_id: workstationId || undefined,
        setup_time: setupTime || undefined,
        run_time: runTime || undefined,
      }
      if (isNew) {
        return operationsService.createOperation(payload)
      } else {
        return operationsService.updateOperation(id!, payload)
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operations"] })
      toast.success(isNew ? "Operation created" : "Operation updated")
      navigate("/operations")
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || err?.message || "Failed to save operation")
    },
  })

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate("/operations")} aria-label="Back to operations list">
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <h1 className="text-xl font-semibold flex-1">
          {isNew ? "New Operation" : "Edit Operation"}
        </h1>
        {canEdit && (
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            <Save className="w-4 h-4 mr-2" />
            {mutation.isPending ? "Saving..." : "Save"}
          </Button>
        )}
      </div>

      <div className="rounded-xl border bg-card p-6 space-y-5">
        <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
          Real routing operations are reusable production steps, for example Cutting, Mixing,
          Assembly, QC Inspection, Sterilization, or Packing. Each operation must run at a
          workstation/resource so capacity and cost can be calculated.
        </div>

        <div className="space-y-2">
          <Label htmlFor="name">Operation Name *</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={!canEdit}
            placeholder="e.g. Final Assembly"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="op-code">Operation Code <span className="text-muted-foreground text-xs">(optional — auto-generated if blank)</span></Label>
          <Input
            id="op-code"
            value={operationCode}
            onChange={(e) => setOperationCode(e.target.value.toUpperCase().slice(0, 10))}
            disabled={!canEdit || !isNew}
            placeholder="e.g. FA, CUT, ASSY"
            maxLength={10}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={!canEdit}
            rows={2}
            placeholder="Optional description..."
          />
        </div>

        <div className="space-y-2">
          <Label>Workstation *</Label>
          <Select
            value={workstationId}
            onValueChange={setWorkstationId}
            disabled={!canEdit}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a workstation" />
            </SelectTrigger>
            <SelectContent>
              {workstations.map((ws) => (
                <SelectItem key={ws.id} value={ws.id}>
                  {ws.name} ({ws.code})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {workstations.length === 0 && (
            <p className="text-xs text-destructive">Create a workstation before creating operations.</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="setup-time">Setup Time (minutes)</Label>
            <Input
              id="setup-time"
              type="number"
              min={0}
              value={setupTime}
              onChange={(e) => setSetupTime(Number(e.target.value))}
              disabled={!canEdit}
            />
            <p className="text-xs text-muted-foreground">Time to prepare the workstation before production.</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="run-time">Run Time (minutes/unit)</Label>
            <Input
              id="run-time"
              type="number"
              min={0}
              step={0.1}
              value={runTime}
              onChange={(e) => setRunTime(Number(e.target.value))}
              disabled={!canEdit}
            />
            <p className="text-xs text-muted-foreground">Time to process one unit through this operation.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
