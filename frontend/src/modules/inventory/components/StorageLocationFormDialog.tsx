import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { materialService } from "@/services/material.service"
import type { Location } from "@/types/material.types"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { LocationForm, DEFAULT_FORM, type LocationFormState } from "@/modules/settings/components/LocationForm"

interface Props {
  open: boolean
  onClose: () => void
  location: Location | null
}

export function StorageLocationFormDialog({ open, onClose, location }: Props) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<LocationFormState>(DEFAULT_FORM)
  const [error, setError] = useState<string | null>(null)
  const { data: locations = [] } = useQuery({
    queryKey: ["storage-locations"], queryFn: () => materialService.getLocations(), enabled: open,
  })
  useEffect(() => {
    if (!open) return
    setError(null)
    setForm(location ? {
      name: location.name, code: location.code ?? "", type: location.location_type ?? location.type,
      parent_id: location.parent_location_id ?? location.parent_id ?? "",
      is_active: location.is_active, is_default: location.is_default ?? false,
    } : DEFAULT_FORM)
  }, [open, location])
  const mutation = useMutation({
    mutationFn: async () => {
      if (!form.name.trim() || !form.type) throw new Error("Name and type are required.")
      const body = { name: form.name.trim(), code: form.code || null, parent_id: form.parent_id || null,
        is_active: form.is_active, is_default: form.is_default }
      if (location) return materialService.updateLocation(location.id, body)
      return materialService.createLocation({ ...body, type: form.type })
    },
    onSuccess: () => {
      for (const key of ["storage-locations", "storage-locations-default", "locations"]) {
        queryClient.invalidateQueries({ queryKey: [key] })
      }
      onClose()
    },
    onError: (err: Error) => setError(err.message),
  })
  return <Dialog open={open} onOpenChange={(value) => { if (!value) onClose() }}>
    <DialogContent>
      <DialogHeader><DialogTitle>{location ? "Edit Location" : "Add Location"}</DialogTitle></DialogHeader>
      {error && <p role="alert" className="text-destructive">{error}</p>}
      <LocationForm form={form} isEdit={!!location} saving={mutation.isPending} editingId={location?.id}
        allLocations={locations} onChange={(patch) => setForm((current) => ({ ...current, ...patch }))}
        onSubmit={() => mutation.mutate()} onCancel={onClose} />
    </DialogContent>
  </Dialog>
}
