import { useState, useMemo, useCallback, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ColumnDef } from "@tanstack/react-table"
import { Plus, Ruler, Pencil, PowerOff } from "lucide-react"
import { toast } from "sonner"

import { materialService } from "@/services/material.service"
import { apiClient } from "@/services/api-client"
import type { UnitOfMeasure } from "@/types/material.types"

import { PageHeader } from "@/components/layout/PageHeader"
import { DataTable } from "@/components/shared/DataTable"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { ConfirmationDialog } from "@/components/shared/ConfirmationDialog"
import { TableSkeleton } from "@/components/shared/LoadingSkeleton"
import EmptyState from "@/components/shared/EmptyState"
import { Drawer } from "@/components/shared/Drawer"
import { BusinessAssistantPanel } from "@/components/shared/BusinessAssistantPanel"
import { unitMasterAssistant } from "@/modules/settings/business-assistant/unitMasterAssistant"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

// ── Types ─────────────────────────────────────────────────────────────────────

type StatusFilter = "all" | "active" | "inactive"

interface UnitFormState {
  code: string
  name: string
  precision: number
  is_active: boolean
}

const DEFAULT_FORM: UnitFormState = {
  code: "",
  name: "",
  precision: 2,
  is_active: true,
}

// ── Column definitions ────────────────────────────────────────────────────────

function buildColumns(
  onEdit: (unit: UnitOfMeasure) => void,
  onDeactivate: (unit: UnitOfMeasure) => void
): ColumnDef<UnitOfMeasure, unknown>[] {
  return [
    {
      accessorKey: "code",
      header: "Code",
      cell: ({ row }) => (
        <span className="font-mono text-sm font-medium text-slate-800">
          {row.original.code}
        </span>
      ),
    },
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <span className="text-sm text-slate-700">{row.original.name}</span>
      ),
    },
    {
      accessorKey: "precision",
      header: "Precision",
      cell: ({ row }) => (
        <span className="text-sm tabular-nums text-slate-600">
          {row.original.precision}
        </span>
      ),
    },
    {
      accessorKey: "is_active",
      header: "Status",
      cell: ({ row }) => (
        <StatusBadge status={row.original.is_active ? "active" : "inactive"} />
      ),
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => {
        const unit = row.original
        return (
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 gap-1.5 text-xs"
              onClick={() => onEdit(unit)}
            >
              <Pencil className="h-3.5 w-3.5" />
              Edit
            </Button>
            {unit.is_active && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 gap-1.5 text-xs text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                onClick={() => onDeactivate(unit)}
              >
                <PowerOff className="h-3.5 w-3.5" />
                Deactivate
              </Button>
            )}
          </div>
        )
      },
    },
  ]
}

// ── Unit Form (inside drawer) ─────────────────────────────────────────────────

interface UnitFormProps {
  form: UnitFormState
  isEdit: boolean
  saving: boolean
  onChange: (patch: Partial<UnitFormState>) => void
  onSubmit: () => void
  onCancel: () => void
}

function UnitForm({ form, isEdit, saving, onChange, onSubmit, onCancel }: UnitFormProps) {
  return (
    <div className="flex flex-col gap-5">
      {/* Code */}
      <div className="space-y-1.5">
        <Label htmlFor="unit-code">
          Code <span className="text-red-500">*</span>
        </Label>
        <Input
          id="unit-code"
          value={form.code}
          disabled={isEdit}
          placeholder="e.g. KG, ML, PCS"
          className={isEdit ? "bg-slate-50 text-slate-500" : ""}
          onChange={(e) => onChange({ code: e.target.value.toUpperCase() })}
        />
        {isEdit && (
          <p className="text-xs text-slate-400">Code cannot be changed after creation.</p>
        )}
      </div>

      {/* Name */}
      <div className="space-y-1.5">
        <Label htmlFor="unit-name">
          Name <span className="text-red-500">*</span>
        </Label>
        <Input
          id="unit-name"
          value={form.name}
          placeholder="e.g. Kilogram, Milliliter, Pieces"
          onChange={(e) => onChange({ name: e.target.value })}
        />
      </div>

      {/* Precision */}
      <div className="space-y-1.5">
        <Label htmlFor="unit-precision">Precision (decimal places)</Label>
        <Select
          value={String(form.precision)}
          onValueChange={(v) => onChange({ precision: Number(v) })}
        >
          <SelectTrigger id="unit-precision">
            <SelectValue placeholder="Select precision" />
          </SelectTrigger>
          <SelectContent>
            {[0, 1, 2, 3, 4, 5, 6].map((p) => (
              <SelectItem key={p} value={String(p)}>
                {p} — {p === 0 ? "whole numbers only" : `up to ${(0.1 ** p).toFixed(p)}`}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Active */}
      <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
        <Checkbox
          id="unit-active"
          checked={form.is_active}
          onCheckedChange={(checked) => onChange({ is_active: !!checked })}
        />
        <div className="space-y-0.5">
          <Label htmlFor="unit-active" className="cursor-pointer text-sm font-medium">
            Active
          </Label>
          <p className="text-xs text-slate-500">
            Inactive units are hidden from dropdowns.
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="outline" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
        <Button onClick={onSubmit} disabled={saving}>
          {saving ? "Saving…" : isEdit ? "Save Changes" : "Create Unit"}
        </Button>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function UnitMasterPage() {
  const queryClient = useQueryClient()

  // ── Query ────────────────────────────────────────────────────────────────
  const { data: units = [], isLoading } = useQuery({
    queryKey: ["units"],
    queryFn: materialService.getUnits,
  })

  // ── Search + filter state ────────────────────────────────────────────────
  const [searchInput, setSearchInput] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")

  // Debounce: 300 ms
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput.trim()), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const filtered = useMemo(() => {
    const q = debouncedSearch.toLowerCase()
    return units.filter((u) => {
      const matchesSearch =
        !q || u.code.toLowerCase().includes(q) || u.name.toLowerCase().includes(q)
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "active" ? u.is_active : !u.is_active)
      return matchesSearch && matchesStatus
    })
  }, [units, debouncedSearch, statusFilter])

  // ── Drawer state ─────────────────────────────────────────────────────────
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingUnit, setEditingUnit] = useState<UnitOfMeasure | null>(null)
  const [form, setForm] = useState<UnitFormState>(DEFAULT_FORM)

  const openCreate = useCallback(() => {
    setEditingUnit(null)
    setForm(DEFAULT_FORM)
    setDrawerOpen(true)
  }, [])

  const openEdit = useCallback((unit: UnitOfMeasure) => {
    setEditingUnit(unit)
    setForm({
      code: unit.code,
      name: unit.name,
      precision: unit.precision,
      is_active: unit.is_active,
    })
    setDrawerOpen(true)
  }, [])

  const closeDrawer = useCallback(() => {
    setDrawerOpen(false)
    setEditingUnit(null)
    setForm(DEFAULT_FORM)
  }, [])

  const patchForm = useCallback((patch: Partial<UnitFormState>) => {
    setForm((prev) => ({ ...prev, ...patch }))
  }, [])

  // ── Create mutation ──────────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: (body: { code: string; name: string; precision: number; is_active: boolean }) =>
      apiClient.post("/inventory/master-data/units", body).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["units"] })
      toast.success("Unit created successfully.")
      closeDrawer()
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to create unit.")
    },
  })

  // ── Update mutation ──────────────────────────────────────────────────────
  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: { name?: string; precision?: number; is_active?: boolean } }) =>
      materialService.updateUnit(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["units"] })
      toast.success("Unit updated successfully.")
      closeDrawer()
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to update unit.")
    },
  })

  const handleSubmit = useCallback(() => {
    if (!form.code.trim()) {
      toast.error("Code is required.")
      return
    }
    if (!form.name.trim()) {
      toast.error("Name is required.")
      return
    }
    if (editingUnit) {
      updateMutation.mutate({
        id: editingUnit.id,
        body: { name: form.name, precision: form.precision, is_active: form.is_active },
      })
    } else {
      createMutation.mutate({
        code: form.code,
        name: form.name,
        precision: form.precision,
        is_active: form.is_active,
      })
    }
  }, [form, editingUnit, createMutation, updateMutation])

  const isSaving = createMutation.isPending || updateMutation.isPending

  // ── Deactivate (delete) ──────────────────────────────────────────────────
  const [deactivateTarget, setDeactivateTarget] = useState<UnitOfMeasure | null>(null)

  const deleteMutation = useMutation({
    mutationFn: (id: string) => materialService.deleteUnit(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["units"] })
      toast.success("Unit deactivated successfully.")
      setDeactivateTarget(null)
    },
    onError: (err: Error & { response?: { status?: number } }) => {
      setDeactivateTarget(null)
      const status = (err as any)?.response?.status
      if (status === 409) {
        toast.error(
          "Cannot deactivate this unit — it is referenced by existing materials or records."
        )
      } else {
        toast.error(err.message || "Failed to deactivate unit.")
      }
    },
  })

  const openDeactivate = useCallback((unit: UnitOfMeasure) => {
    setDeactivateTarget(unit)
  }, [])

  // ── Columns ──────────────────────────────────────────────────────────────
  const columns = useMemo(
    () => buildColumns(openEdit, openDeactivate),
    [openEdit, openDeactivate]
  )

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Units of Measure"
        description="Define measurement units used across materials, products, and BOMs."
        action={
          <div className="flex items-center gap-2">
            <BusinessAssistantPanel
              config={unitMasterAssistant}
              triggerLabel="Business Assistant"
            />
            <Button onClick={openCreate} className="gap-2">
              <Plus className="h-4 w-4" />
              Add Unit
            </Button>
          </div>
        }
      />

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Input
          placeholder="Search by code or name…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="max-w-xs"
        />
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Inactive</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {isLoading ? (
        <TableSkeleton rows={6} />
      ) : units.length === 0 ? (
        <EmptyState
          icon={Ruler}
          title="No units of measure yet"
          description="Create your first unit to start configuring materials and products."
          action={{ label: "Add Unit", onClick: openCreate }}
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Ruler}
          title="No units match your filters"
          variant="filtered"
          action={{
            label: "Clear filters",
            onClick: () => {
              setSearchInput("")
              setStatusFilter("all")
            },
          }}
        />
      ) : (
        <DataTable columns={columns} data={filtered} />
      )}

      {/* Create / Edit Drawer */}
      <Drawer
        open={drawerOpen}
        onOpenChange={(open) => { if (!open) closeDrawer() }}
        title={editingUnit ? `Edit Unit — ${editingUnit.code}` : "Add Unit of Measure"}
      >
        <UnitForm
          form={form}
          isEdit={!!editingUnit}
          saving={isSaving}
          onChange={patchForm}
          onSubmit={handleSubmit}
          onCancel={closeDrawer}
        />
      </Drawer>

      {/* Deactivate confirmation */}
      <ConfirmationDialog
        open={!!deactivateTarget}
        onOpenChange={(open) => { if (!open) setDeactivateTarget(null) }}
        title="Deactivate Unit"
        message={
          deactivateTarget
            ? `Deactivate "${deactivateTarget.name}" (${deactivateTarget.code})? It will be hidden from all dropdowns. Existing records that use this unit are not affected.`
            : ""
        }
        confirmLabel="Deactivate"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => {
          if (deactivateTarget) deleteMutation.mutate(deactivateTarget.id)
        }}
      />
    </div>
  )
}
