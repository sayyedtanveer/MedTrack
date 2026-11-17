import { useState, useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Edit, Trash2, Star } from "lucide-react"
import { Button } from "@/components/ui/button"
import { PageHeader } from "@/components/layout/PageHeader"
import { DataTable } from "@/components/shared/DataTable"
import { ColumnDef } from "@tanstack/react-table"
import type { Location as LocationResponse } from "@/types/material.types"
import { materialService } from "@/services/material.service"
import { StorageLocationFormDialog } from "@/modules/inventory/components/StorageLocationFormDialog"
import { usePermissions } from "@/hooks/usePermissions"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { AlertCircle, Check as CheckIcon } from "lucide-react"

interface StorageLocationWithDefault extends LocationResponse {
  isDefault?: boolean
}

export default function StorageLocationMasterPage() {
  const queryClient = useQueryClient()
  const { canWrite } = usePermissions()
  
  const [searchQuery, setSearchQuery] = useState("")
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [selectedLocation, setSelectedLocation] = useState<LocationResponse | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<LocationResponse | null>(null)
  const [defaultConfirm, setDefaultConfirm] = useState<LocationResponse | null>(null)

  // Fetch all locations
  const { data: locationsData, isLoading, error } = useQuery({
    queryKey: ["storage-locations"],
    queryFn: () => materialService.getLocations(),
  })

  // Fetch default location
  const { data: defaultLocation } = useQuery({
    queryKey: ["storage-locations-default"],
    queryFn: () => materialService.getDefaultLocation(),
  })

  const locations = useMemo<StorageLocationWithDefault[]>(() => {
    if (!locationsData) return []
    return locationsData.map(loc => ({
      ...loc,
      isDefault: defaultLocation?.id === loc.id
    }))
  }, [locationsData, defaultLocation])

  const filteredLocations = useMemo(() => {
    return locations.filter(loc => {
      const query = searchQuery.toLowerCase()
      return (
        loc.name.toLowerCase().includes(query) ||
        (loc.code?.toLowerCase().includes(query) ?? false) ||
        (loc.location_type ?? loc.type).toLowerCase().includes(query)
      )
    })
  }, [locations, searchQuery])

  // Mutation for delete
  const deleteMutation = useMutation({
    mutationFn: (locationId: string) => materialService.deleteLocation(locationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["storage-locations"] })
      setDeleteConfirm(null)
    },
  })

  // Mutation for set default
  const setDefaultMutation = useMutation({
    mutationFn: (locationId: string) => materialService.setDefaultLocation(locationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["storage-locations"] })
      queryClient.invalidateQueries({ queryKey: ["storage-locations-default"] })
      setDefaultConfirm(null)
    },
  })

  const handleFormOpen = (location?: LocationResponse) => {
    setSelectedLocation(location ?? null)
    setIsFormOpen(true)
  }

  const handleFormClose = () => {
    setIsFormOpen(false)
    setSelectedLocation(null)
  }

  const handleDelete = async (location: LocationResponse) => {
    await deleteMutation.mutateAsync(location.id)
  }

  const handleSetDefault = async (location: LocationResponse) => {
    await setDefaultMutation.mutateAsync(location.id)
  }

  // Table columns
  const columns = useMemo<ColumnDef<StorageLocationWithDefault>[]>(() => [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{row.original.name}</span>
          {row.original.isDefault && (
            <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" aria-label="Default location" />
          )}
        </div>
      ),
    },
    {
      accessorKey: "code",
      header: "Code",
      cell: ({ row }) => <code className="text-xs bg-muted px-2 py-1 rounded">{row.original.code || "—"}</code>,
    },
    {
      accessorKey: "location_type",
      header: "Type",
      cell: ({ row }) => (
        <span className="capitalize px-2 py-1 bg-blue-100 text-blue-800 rounded-md text-xs font-medium">
          {(row.original.location_type ?? row.original.type).replace(/_/g, " ")}
        </span>
      ),
    },
    {
      id: "is_active",
      header: "Status",
      cell: ({ row }) => (
        <span className={row.original.is_active ? "text-green-600" : "text-red-600"}>
          {row.original.is_active ? "Active" : "Inactive"}
        </span>
      ),
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <div className="flex gap-2 justify-end">
          {canWrite() && (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleFormOpen(row.original)}
                title="Edit location"
              >
                <Edit className="h-4 w-4" />
              </Button>
              {!row.original.isDefault && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setDefaultConfirm(row.original)}
                  title="Set as default"
                >
                  <Star className="h-4 w-4" />
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setDeleteConfirm(row.original)}
                title="Delete location"
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </>
          )}
        </div>
      ),
    },
  ], [canWrite])

  return (
    <div className="w-full space-y-6">
      <PageHeader
        title="Storage Locations"
        description="Manage storage locations (warehouses, racks, bins) and set default location for material imports."
        action={
          canWrite() && (
            <Button onClick={() => handleFormOpen()}>
              <Plus className="mr-2 h-4 w-4" />
              Add Location
            </Button>
          )
        }
      />

      {/* Search Input */}
      <div className="flex gap-2">
        <div className="flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search by name, code, or type..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
        </div>
      </div>

      {/* Default Location Info */}
      {defaultLocation && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <CheckIcon className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-medium text-blue-900">Default Location Set</h4>
            <p className="text-sm text-blue-800">
              <strong>{defaultLocation.name}</strong> {defaultLocation.code && `(${defaultLocation.code})`} is the default location for material imports.
            </p>
          </div>
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center p-8">
          <div className="text-muted-foreground">Loading locations...</div>
        </div>
      ) : error ? (
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-medium text-destructive">Error loading locations</h4>
            <p className="text-sm text-destructive/80">{error instanceof Error ? error.message : "Unknown error"}</p>
          </div>
        </div>
      ) : (
        <div className="border rounded-lg">
          <DataTable columns={columns} data={filteredLocations} />
        </div>
      )}

      {/* Form Dialog */}
      <StorageLocationFormDialog
        open={isFormOpen}
        onClose={handleFormClose}
        location={selectedLocation}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteConfirm} onOpenChange={(open) => !open && setDeleteConfirm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Location?</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{deleteConfirm?.name}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirm(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteConfirm && handleDelete(deleteConfirm)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Set Default Confirmation Dialog */}
      <Dialog open={!!defaultConfirm} onOpenChange={(open) => !open && setDefaultConfirm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Set as Default Location?</DialogTitle>
            <DialogDescription>
              Set <strong>{defaultConfirm?.name}</strong> as the default location for material imports.
              {defaultLocation && defaultLocation.id !== defaultConfirm?.id && (
                <>
                  <br />
                  <br />
                  The current default <strong>{defaultLocation.name}</strong> will be unset.
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDefaultConfirm(null)}>
              Cancel
            </Button>
            <Button
              onClick={() => defaultConfirm && handleSetDefault(defaultConfirm)}
              disabled={setDefaultMutation.isPending}
            >
              {setDefaultMutation.isPending ? "Setting..." : "Set as Default"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
