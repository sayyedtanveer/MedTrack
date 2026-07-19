import { useState, useMemo, useCallback, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ColumnDef } from "@tanstack/react-table"
import { Plus, Tag, Pencil, PowerOff } from "lucide-react"
import { toast } from "sonner"

import { materialService } from "@/services/material.service"
import type { Category } from "@/types/material.types"

import { PageHeader } from "@/components/layout/PageHeader"
import { DataTable } from "@/components/shared/DataTable"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { ConfirmationDialog } from "@/components/shared/ConfirmationDialog"
import { TableSkeleton } from "@/components/shared/LoadingSkeleton"
import EmptyState from "@/components/shared/EmptyState"
import { Drawer } from "@/components/shared/Drawer"
import { BusinessAssistantPanel } from "@/components/shared/BusinessAssistantPanel"
import { categoryMasterAssistant } from "@/modules/settings/business-assistant/categoryMasterAssistant"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

// ── Types ─────────────────────────────────────────────────────────────────────

type StatusFilter = "all" | "active" | "inactive"

/** Category as returned by the API — includes the optional material_count field */
type CategoryRow = Category & { material_count?: number }

interface CategoryFormState {
  name: string
  code_prefix: string
  description: string
  is_active: boolean
}

const DEFAULT_FORM: CategoryFormState = {
  name: "",
  code_prefix: "",
  description: "",
  is_active: true,
}

// ── Column definitions ────────────────────────────────────────────────────────

function buildColumns(
  onEdit: (category: CategoryRow) => void,
  onDeactivate: (category: CategoryRow) => void
): ColumnDef<CategoryRow, unknown>[] {
  return [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <span className="text-sm font-medium text-slate-800">{row.original.name}</span>
      ),
    },
    {
      accessorKey: "code_prefix",
      header: "Code Prefix",
      cell: ({ row }) => (
        <span className="font-mono text-sm font-medium text-slate-700">
          {row.original.code_prefix}
        </span>
      ),
    },
    {
      accessorKey: "description",
      header: "Description",
      cell: ({ row }) => {
        const desc = row.original.description
        if (!desc) return <span className="text-sm text-slate-400">—</span>
        const truncated = desc.length > 40 ? desc.slice(0, 40) + "…" : desc
        return <span className="text-sm text-slate-600">{truncated}</span>
      },
    },
    {
      accessorKey: "material_count",
      header: "Material Count",
      cell: ({ row }) => (
        <span className="text-sm tabular-nums text-slate-600">
          {row.original.material_count ?? 0}
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
        const category = row.original
        return (
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 gap-1.5 text-xs"
              onClick={() => onEdit(category)}
            >
              <Pencil className="h-3.5 w-3.5" />
              Edit
            </Button>
            {category.is_active && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 gap-1.5 text-xs text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                onClick={() => onDeactivate(category)}
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

// ── Category Form (inside drawer) ─────────────────────────────────────────────

interface CategoryFormProps {
  form: CategoryFormState
  isEdit: boolean
  saving: boolean
  codePrefixError: string
  onChange: (patch: Partial<CategoryFormState>) => void
  onCodePrefixBlur: () => void
  onSubmit: () => void
  onCancel: () => void
}

function CategoryForm({
  form,
  isEdit,
  saving,
  codePrefixError,
  onChange,
  onCodePrefixBlur,
  onSubmit,
  onCancel,
}: CategoryFormProps) {
  return (
    <div className="flex flex-col gap-5">
      {/* Name */}
      <div className="space-y-1.5">
        <Label htmlFor="cat-name">
          Name <span className="text-red-500">*</span>
        </Label>
        <Input
          id="cat-name"
          value={form.name}
          placeholder="e.g. Metal, Packaging, Chemical"
          onChange={(e) => onChange({ name: e.target.value })}
        />
      </div>

      {/* Code Prefix */}
      <div className="space-y-1.5">
        <Label htmlFor="cat-code-prefix">
          Code Prefix <span className="text-red-500">*</span>
        </Label>
        <Input
          id="cat-code-prefix"
          value={form.code_prefix}
          placeholder="e.g. MET, PKG, CHM"
          maxLength={6}
          onChange={(e) => onChange({ code_prefix: e.target.value.toUpperCase() })}
          onBlur={onCodePrefixBlur}
          className={codePrefixError ? "border-red-400 focus-visible:ring-red-400" : ""}
        />
        {codePrefixError ? (
          <p className="text-xs text-red-500">{codePrefixError}</p>
        ) : (
          <p className="text-xs text-slate-400">
            2–6 uppercase letters or digits. Used in auto-generated item codes.
          </p>
        )}
      </div>

      {/* Description */}
      <div className="space-y-1.5">
        <Label htmlFor="cat-description">Description</Label>
        <Textarea
          id="cat-description"
          value={form.description}
          placeholder="Optional description of what materials belong in this category"
          rows={3}
          onChange={(e) => onChange({ description: e.target.value })}
        />
      </div>

      {/* Active */}
      <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
        <Checkbox
          id="cat-active"
          checked={form.is_active}
          onCheckedChange={(checked) => onChange({ is_active: !!checked })}
        />
        <div className="space-y-0.5">
          <Label htmlFor="cat-active" className="cursor-pointer text-sm font-medium">
            Active
          </Label>
          <p className="text-xs text-slate-500">
            Inactive categories are hidden from material and product dropdowns.
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="outline" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
        <Button onClick={onSubmit} disabled={saving}>
          {saving ? "Saving…" : isEdit ? "Save Changes" : "Create Category"}
        </Button>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function CategoryMasterPage() {
  const queryClient = useQueryClient()

  // ── Query ────────────────────────────────────────────────────────────────
  const { data: categories = [], isLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: materialService.getCategories,
  })

  const typedCategories = categories as CategoryRow[]

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
    return typedCategories.filter((c) => {
      const matchesSearch =
        !q ||
        c.name.toLowerCase().includes(q) ||
        c.code_prefix.toLowerCase().includes(q)
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "active" ? c.is_active : !c.is_active)
      return matchesSearch && matchesStatus
    })
  }, [typedCategories, debouncedSearch, statusFilter])

  // ── Drawer state ─────────────────────────────────────────────────────────
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingCategory, setEditingCategory] = useState<CategoryRow | null>(null)
  const [form, setForm] = useState<CategoryFormState>(DEFAULT_FORM)
  const [codePrefixError, setCodePrefixError] = useState("")

  const openCreate = useCallback(() => {
    setEditingCategory(null)
    setForm(DEFAULT_FORM)
    setCodePrefixError("")
    setDrawerOpen(true)
  }, [])

  const openEdit = useCallback((category: CategoryRow) => {
    setEditingCategory(category)
    setForm({
      name: category.name,
      code_prefix: category.code_prefix,
      description: category.description ?? "",
      is_active: category.is_active,
    })
    setCodePrefixError("")
    setDrawerOpen(true)
  }, [])

  const closeDrawer = useCallback(() => {
    setDrawerOpen(false)
    setEditingCategory(null)
    setForm(DEFAULT_FORM)
    setCodePrefixError("")
  }, [])

  const patchForm = useCallback((patch: Partial<CategoryFormState>) => {
    setForm((prev) => {
      const next = { ...prev, ...patch }

      // Auto-suggest code_prefix from name when code_prefix is still empty
      if ("name" in patch && !prev.code_prefix) {
        next.code_prefix = patch.name!
          .toUpperCase()
          .replace(/[^A-Z0-9]/g, "")
          .slice(0, 3)
      }

      // Clear error when user edits code_prefix
      if ("code_prefix" in patch) {
        setCodePrefixError("")
      }

      return next
    })
  }, [])

  const validateCodePrefix = useCallback((): boolean => {
    const CODE_PREFIX_RE = /^[A-Z0-9]{2,6}$/
    if (!CODE_PREFIX_RE.test(form.code_prefix)) {
      setCodePrefixError("Must be 2–6 uppercase letters or digits")
      return false
    }
    setCodePrefixError("")
    return true
  }, [form.code_prefix])

  // ── Create mutation ──────────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: (body: {
      name: string
      code_prefix: string
      description?: string
      is_active: boolean
    }) => materialService.createCategory(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] })
      toast.success("Category created successfully.")
      closeDrawer()
    },
    onError: (err: Error) => {
      toast.error((err as any)?.message || "Failed to create category.")
    },
  })

  // ── Update mutation ──────────────────────────────────────────────────────
  const updateMutation = useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string
      body: { name?: string; code_prefix?: string; description?: string; is_active?: boolean }
    }) => materialService.updateCategory(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] })
      toast.success("Category updated successfully.")
      closeDrawer()
    },
    onError: (err: Error) => {
      toast.error((err as any)?.message || "Failed to update category.")
    },
  })

  const handleSubmit = useCallback(() => {
    if (!form.name.trim()) {
      toast.error("Name is required.")
      return
    }
    if (!validateCodePrefix()) {
      return
    }
    if (editingCategory) {
      updateMutation.mutate({
        id: editingCategory.id,
        body: {
          name: form.name,
          code_prefix: form.code_prefix,
          description: form.description || undefined,
          is_active: form.is_active,
        },
      })
    } else {
      createMutation.mutate({
        name: form.name,
        code_prefix: form.code_prefix,
        description: form.description || undefined,
        is_active: form.is_active,
      })
    }
  }, [form, editingCategory, createMutation, updateMutation, validateCodePrefix])

  const isSaving = createMutation.isPending || updateMutation.isPending

  // ── Deactivate (delete) ──────────────────────────────────────────────────
  const [deactivateTarget, setDeactivateTarget] = useState<CategoryRow | null>(null)

  const deleteMutation = useMutation({
    mutationFn: (id: string) => materialService.deleteCategory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] })
      toast.success("Category deactivated successfully.")
      setDeactivateTarget(null)
    },
    onError: (err) => {
      setDeactivateTarget(null)
      const detail = (err as any)?.response?.data?.detail ?? ""
      if ((err as any)?.response?.status === 409) {
        toast.error(`Cannot delete "${deactivateTarget?.name}" — ${detail}`)
      } else {
        toast.error("Failed to delete category.")
      }
    },
  })

  const openDeactivate = useCallback((category: CategoryRow) => {
    setDeactivateTarget(category)
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
        title="Material Categories"
        description="Classify materials and products. Categories drive item code generation via the code prefix."
        action={
          <div className="flex items-center gap-2">
            <BusinessAssistantPanel
              config={categoryMasterAssistant}
              triggerLabel="Business Assistant"
            />
            <Button onClick={openCreate} className="gap-2">
              <Plus className="h-4 w-4" />
              Add Category
            </Button>
          </div>
        }
      />

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Input
          placeholder="Search by name or code prefix…"
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
      ) : typedCategories.length === 0 ? (
        <EmptyState
          icon={Tag}
          title="No categories configured"
          description="Add your first category to start classifying materials."
          action={{ label: "Add Category", onClick: openCreate }}
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Tag}
          title="No categories match your filters"
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
        onOpenChange={(open) => {
          if (!open) closeDrawer()
        }}
        title={editingCategory ? `Edit Category — ${editingCategory.name}` : "Add Category"}
      >
        <CategoryForm
          form={form}
          isEdit={!!editingCategory}
          saving={isSaving}
          codePrefixError={codePrefixError}
          onChange={patchForm}
          onCodePrefixBlur={validateCodePrefix}
          onSubmit={handleSubmit}
          onCancel={closeDrawer}
        />
      </Drawer>

      {/* Deactivate confirmation */}
      <ConfirmationDialog
        open={!!deactivateTarget}
        onOpenChange={(open) => {
          if (!open) setDeactivateTarget(null)
        }}
        title="Deactivate Category"
        message={
          deactivateTarget
            ? `Deactivate "${deactivateTarget.name}" (${deactivateTarget.code_prefix})? It will be hidden from all dropdowns. Existing materials that use this category are not affected.`
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
