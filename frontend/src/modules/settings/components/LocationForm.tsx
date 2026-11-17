import type { Location } from "@/types/material.types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

export const LOCATION_TYPES = [
  "warehouse",
  "rack",
  "bin",
  "quarantine",
  "production",
  "shipping",
  "subcontractor",
] as const

export interface LocationFormState {
  name: string
  code: string
  type: string
  parent_id: string
  is_active: boolean
  is_default: boolean
}

export const DEFAULT_FORM: LocationFormState = {
  name: "",
  code: "",
  type: "",
  parent_id: "",
  is_active: true,
  is_default: false,
}

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

export function LocationForm({
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

      {/* Default Location */}
      <div className="flex items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
        <Checkbox
          id="loc-default"
          checked={form.is_default}
          onCheckedChange={(checked) => onChange({ is_default: !!checked })}
        />
        <div className="space-y-0.5">
          <Label htmlFor="loc-default" className="cursor-pointer text-sm font-medium text-blue-900">
            Set as Default Location
          </Label>
          <p className="text-xs text-blue-700">
            Default location is pre-selected in material import templates and forms.
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

