import { useState, useMemo, useCallback, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ColumnDef } from "@tanstack/react-table"
import { Plus, MapPin, Pencil, PowerOff } from "lucide-react"
import { toast } from "sonner"

import { materialService } from "@/services/material.service"
import type { Location } from "@/types/material.types"

import { PageHeader } from "@/components/layout/PageHeader"
import { DataTable } from "@/components/shared/DataTable"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { ConfirmationDialog } from "@/components/shared/ConfirmationDialog"
import { TableSkeleton } from "@/components/shared/LoadingSkeleton"
import EmptyState from "@/components/shared/EmptyState"
import { Drawer } from "@/components/shared/Drawer"
import { BusinessAssistantPanel } from "@/components/shared/BusinessAssistantPanel"
import { locationMasterAssistant } from "@/modules/settings/business-assistant/locationMasterAssistant"

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

// ── Constants ─────────────────────────────────────────────────────────────────

const LOCATION_TYPES = [
  "warehouse",
  "rack",
  "bin",
  "quarantine",
  "production",
  "shipping",
  "subcontractor",
] as const
type StatusFilter = "all" | "active" | "inactive"

// ── Type badge helper ─────────────────────────────────────────────────────────

function getTypeBadgeClass(type: string): string {
  switch (type) {
    case "warehouse":
      return "bg-blue-100 text-blue-800"
    case "rack":
      return "bg-slate-100 text-slate-800"
    case "bin":
      return "bg-gray-100 text-gray-800"
    case "quarantine":
      return "bg-amber-100 text-amber-800"
    case "production":
      return "bg-green-100 text-green-800"
    case "shipping":
      return "bg-indigo-100 text-indigo-800"
    case "subcontractor":
      return "bg-violet-100 text-violet-800"
    default:
      return "bg-gray-100 text-gray-800"
  }
}

// ── Sorting helper ────────────────────────────────────────────────────────────

function sortLocations(locations: Location[]): Location[] {
  return [...locations].sort((a, b) => {
    const aParent = a.parent_location_id ?? a.parent_id
    const bParent = b.parent_location_id ?? b.parent_id
    if (!aParent && bParent) return -1
    if (aParent && !bParent) return 1
    return 0
  })
}

// ── Form state ────────────────────────────────────────────────────────────────

interface LocationFormState {
  name: string
  code: string
  type: string
  parent_id: string
  is_active: boolean
}

const DEFAULT_FORM: LocationFormState = {
  name: "",
  code: "",
  type: "",
  parent_id: "",
  is_active: true,
}

// ── Column definitions ────────────────────────────────────────────────────────

function buildColumns(
  allLocations: Location[],
  onEdit: (loc: Location) => void,
  onDelete: (loc: Location) => void
): ColumnDef<Location, unknown>[] {
  return [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => {
        const loc = row.original
        const hasParent = !!(loc.parent_location_id ?? loc.parent_id)
        return (
          <span
            className={`text-sm text-slate-700 ${hasParent ? "pl-6" : ""}`}
          >
            {loc.name}
          </span>
        )
      },
    },
    {
      accessorKey: "code",
      header: "Code",
      cell: ({ row }) => (
        <span className="font-mono text-sm text-slate-600">
          {row.original.code ?? "—"}
        </span>
      ),
    },
    {
      id: "type",
      header: "Type",
      cell: ({ row }) => {
        const loc = row.original
        const displayType = loc.location_type ?? loc.type
        return (
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${getTypeBadgeClass(displayType)}`}
          >
            {displayType}
          </span>
        )
      },
    },
    {
      id: "parent",
      header: "Parent",
      cell: ({ row }) => {
        const loc = row.original
        const parentId = loc.parent_location_id ?? loc.parent_id
        if (!parentId) return <span className="text-sm text-slate-400">—</span>
        const parent = allLocations.find((l) => l.id === parentId)
        return (
          <span className="text-sm text-slate-600">{parent?.name ?? "—"}</span>
        )
      },
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
        const loc = row.original
        return (
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 gap-1.5 text-xs"
              onClick={() => onEdit(loc)}
            >
              <Pencil className="h-3.5 w-3.5" />
              Edit
            </Button>
            {loc.is_active && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 gap-1.5 text-xs text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                onClick={() => onDelete(loc)}
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

// ── Location Form (inside drawer) ─────────────────────────────────────────────

interface LocationFormProps {
  form: LocationFormState
  isEdit: boolean
  saving: boolean
  editingId?: string
  allLocations: Location[]
  onChange: (patch: Partial<LocationFormState>) => void
  onSubmit: () => void
  onCancel: () => void
}

function LocationForm({
  form,
  isEdit,
  saving,
  editingId,
  allLocations,
  onChange,
  onSubmit,
  onCancel,
}: LocationFormProps) {
  const activeLocations = allLocations.filter(
    (l) => l.is_active && l.id !== editingId
  )

  return (
    <div className="flex flex-col gap-5">
      {/* Name */}
      <div className="space-y-1.5">
        <Label htmlFor="loc-name">
          Name <span className="text-red-500">*</span>
        </Label>
        <Input
          id="loc-name"
          value={form.name}
          placeholder="e.g. Raw Material Store, Rack A, Shelf 1"
          onChange={(e) => onChange({ name: e.target.value })}
        />
      </div>

      {/* Code */}
      <div className="space-y-1.5">
        <Label htmlFor="loc-code">Code</Label>
        <Input
          id="loc-code"
          value={form.code}
          placeholder="e.g. WH-01, RACK-A, BIN-A1"
          onChange={(e) => onChange({ code: e.target.value })}
        />
      </div>

      {/* Type */}
      <div className="space-y-1.5">
        <Label htmlFor="loc-type">
          Type <span className="text-red-500">*</span>
        </Label>
        <Select
          value={form.type}
          onValueChange={(v) => onChange({ type: v })}
        >
          <SelectTrigger id="loc-type">
            <SelectValue placeholder="Select type" />
          </SelectTrigger>
          <SelectContent>
            {LOCATION_TYPES.map((t) => (
              <SelectItem key={t} value={t}>
                <span className="capitalize">{t}</span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Parent */}
      <div className="space-y-1.5">
        <Label htmlFor="loc-parent">Parent Location</Label>
        <Select
          value={form.parent_id || "_none"}
          onValueChange={(v) => onChange({ parent_id: v === "_none" ? "" : v })}
        >
          <SelectTrigger id="loc-parent">
            <SelectValue placeholder="None (root location)" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="_none">None (root location)</SelectItem>
            {activeLocations.map((l) => (
              <SelectItem key={l.id} value={l.id}>
                {l.name}
                {l.code ? ` (${l.code})` : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Active */}
      <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
        <Checkbox
          id="loc-active"
          checked={form.is_active}
          onCheckedChange={(checked) => onChange({ is_active: !!checked })}
        />
        <div className="space-y-0.5">
          <Label htmlFor="loc-active" className="cursor-pointer text-sm font-medium">
            Active
          </Label>
          <p className="text-xs text-slate-500">
            Inactive locations are hidden from material assignment dropdowns.
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="outline" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
        <Button onClick={onSubmit} disabled={saving}>
          {saving ? "Saving…" : isEdit ? "Save Changes" : "Create Location"}
        </Button>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function LocationMasterPage() {
  const queryClient = useQueryClient()

  // ── Query ────────────────────────────────────────────────────────────────
  const { data: locations = [], isLoading } = useQuery({
    queryKey: ["locations"],
    queryFn: () => materialService.getLocations(),
  })

  // ── Search + filter state ────────────────────────────────────────────────
  const [searchInput, setSearchInput] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")
  const [typeFilter, setTypeFilter] = useState<string>("all")

  // Debounce: 300 ms
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput.trim()), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const sorted = useMemo(() => sortLocations(locations), [locations])

  const filtered = useMemo(() => {
    const q = debouncedSearch.toLowerCase()
    return sorted.filter((l) => {
      const matchesSearch =
        !q ||
        l.name.toLowerCase().includes(q) ||
        (l.code ?? "").toLowerCase().includes(q)
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "active" ? l.is_active : !l.is_active)
      const displayType = l.location_type ?? l.type
      const matchesType = typeFilter === "all" || displayType === typeFilter
      return matchesSearch && matchesStatus && matchesType
    })
  }, [sorted, debouncedSearch, statusFilter, typeFilter])

  // ── Drawer state ─────────────────────────────────────────────────────────
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingLocation, setEditingLocation] = useState<Location | null>(null)
  const [form, setForm] = useState<LocationFormState>(DEFAULT_FORM)

  const openCreate = useCallback(() => {
    setEditingLocation(null)
    setForm(DEFAULT_FORM)
    setDrawerOpen(true)
  }, [])

  const openEdit = useCallback((loc: Location) => {
    setEditingLocation(loc)
    setForm({
      name: loc.name,
      code: loc.code ?? "",
      type: loc.location_type ?? loc.type,
      parent_id: loc.parent_location_id ?? loc.parent_id ?? "",
      is_active: loc.is_active,
    })
    setDrawerOpen(true)
  }, [])

  const closeDrawer = useCallback(() => {
    setDrawerOpen(false)
    setEditingLocation(null)
    setForm(DEFAULT_FORM)
  }, [])

  const patchForm = useCallback((patch: Partial<LocationFormState>) => {
    setForm((prev) => ({ ...prev, ...patch }))
  }, [])

  // ── Create mutation ──────────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: (body: {
      name: string
      type: string
      code?: string | null
      parent_id?: string | null
      is_active: boolean
    }) => materialService.createLocation(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["locations"] })
      toast.success("Location created successfully.")
      closeDrawer()
    },
    onError: (err: Error) => {
      toast.error((err as any)?.message || "Failed to create location.")
    },
  })

  // ── Update mutation ──────────────────────────────────────────────────────
  const updateMutation = useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string
      body: { name?: string; code?: string | null; parent_id?: string | null; is_active?: boolean }
    }) => materialService.updateLocation(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["locations"] })
      toast.success("Location updated successfully.")
      closeDrawer()
    },
    onError: (err: Error) => {
      toast.error((err as any)?.message || "Failed to update location.")
    },
  })

  const handleSubmit = useCallback(() => {
    if (!form.name.trim()) {
      toast.error("Name is required.")
      return
    }
    if (!form.type) {
      toast.error("Type is required.")
      return
    }

    const parentId = form.parent_id || null

    if (editingLocation) {
      updateMutation.mutate({
        id: editingLocation.id,
        body: {
          name: form.name,
          code: form.code || null,
          parent_id: parentId,
          is_active: form.is_active,
        },
      })
    } else {
      createMutation.mutate({
        name: form.name,
        type: form.type,
        code: form.code || null,
        parent_id: parentId,
        is_active: form.is_active,
      })
    }
  }, [form, editingLocation, createMutation, updateMutation])

  const isSaving = createMutation.isPending || updateMutation.isPending

  // ── Delete (with 409 handling) ───────────────────────────────────────────
  const [deleteTarget, setDeleteTarget] = useState<Location | null>(null)

  const deleteMutation = useMutation({
    mutationFn: (id: string) => materialService.deleteLocation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["locations"] })
      toast.success("Location deactivated successfully.")
      setDeleteTarget(null)
    },
    onError: (err) => {
      setDeleteTarget(null)
      const detail = (err as any)?.response?.data?.detail ?? ""
      if ((err as any)?.response?.status === 409) {
        if (detail.includes("child")) {
          toast.error(
            `Cannot delete "${deleteTarget?.name}" — it has active child locations.`
          )
        } else {
          toast.error(
            `Cannot delete "${deleteTarget?.name}" — materials are assigned here. Deactivate it instead.`
          )
        }
      } else {
        toast.error("Failed to delete location.")
      }
    },
  })

  const openDelete = useCallback((loc: Location) => {
    setDeleteTarget(loc)
  }, [])

  // ── Columns ──────────────────────────────────────────────────────────────
  const columns = useMemo(
    () => buildColumns(locations, openEdit, openDelete),
    [locations, openEdit, openDelete]
  )

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Storage Locations"
        description="Define physical storage areas used for material assignment, GRN receipts, and QC workflows."
        action={
          <div className="flex items-center gap-2">
            <BusinessAssistantPanel
              config={locationMasterAssistant}
              triggerLabel="Business Assistant"
            />
            <Button onClick={openCreate} className="gap-2">
              <Plus className="h-4 w-4" />
              Add Location
            </Button>
          </div>
        }
      />

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Input
          placeholder="Search by name or code…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="max-w-xs"
        />
        <Select
          value={typeFilter}
          onValueChange={(v) => setTypeFilter(v)}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {LOCATION_TYPES.map((t) => (
              <SelectItem key={t} value={t}>
                <span className="capitalize">{t}</span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={statusFilter}
          onValueChange={(v) => setStatusFilter(v as StatusFilter)}
        >
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
      ) : locations.length === 0 ? (
        <EmptyState
          icon={MapPin}
          title="No storage locations yet"
          description="Create your first location to start tracking where materials are stored."
          action={{ label: "Add Location", onClick: openCreate }}
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={MapPin}
          title="No locations match your filters"
          variant="filtered"
          action={{
            label: "Clear filters",
            onClick: () => {
              setSearchInput("")
              setStatusFilter("all")
              setTypeFilter("all")
            },
          }}
        />
      ) : (
        <DataTable columns={columns} data={filtered} />
      )}

      {/* Create / Edit Drawer */}
      <Drawer
        open={drawerOpen}
        onOpenChange={(open) => {
          if (!open) closeDrawer()
        }}
        title={
          editingLocation
            ? `Edit Location — ${editingLocation.name}`
            : "Add Storage Location"
        }
      >
        <LocationForm
          form={form}
          isEdit={!!editingLocation}
          saving={isSaving}
          editingId={editingLocation?.id}
          allLocations={locations}
          onChange={patchForm}
          onSubmit={handleSubmit}
          onCancel={closeDrawer}
        />
      </Drawer>

      {/* Delete confirmation */}
      <ConfirmationDialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
        title="Deactivate Location"
        message={
          deleteTarget
            ? `Deactivate "${deleteTarget.name}"? It will be hidden from all material assignment dropdowns. Existing records that reference this location are not affected.`
            : ""
        }
        confirmLabel="Deactivate"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => {
          if (deleteTarget) deleteMutation.mutate(deleteTarget.id)
        }}
      />
    </div>
  )
}
