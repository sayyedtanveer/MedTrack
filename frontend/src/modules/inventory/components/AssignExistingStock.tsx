import { useState } from 'react'
import { isAxiosError } from 'axios'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { materialService } from '@/services/material.service'
import { extractErrorMessage } from '@/services/api-client'
import { usePermissions } from '@/hooks/usePermissions'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

export function AssignExistingStock({ initialMaterialId = '' }: { initialMaterialId?: string }) {
  const [materialId, setMaterialId] = useState(initialMaterialId)
  const [locationId, setLocationId] = useState('')
  const [remarks, setRemarks] = useState('Opening stock location reconciliation')
  const queryClient = useQueryClient()
  const { canInventoryWrite } = usePermissions()
  const materials = useQuery({
    queryKey: ['materials', 'movement-picker'],
    queryFn: () => materialService.getMaterials({ page: 1, page_size: 500 }),
  })
  const locations = useQuery({ queryKey: ['locations'], queryFn: () => materialService.getLocations() })
  const stock = useQuery({
    queryKey: ['material-stock-by-location', materialId],
    queryFn: () => materialService.getMaterialStockByLocation(materialId),
    enabled: Boolean(materialId),
    staleTime: 0,
  })
  const assignment = useMutation({
    mutationFn: () => materialService.assignExistingStock(materialId, locationId, remarks),
    onSuccess: () => {
      for (const queryKey of [
        ['material-stock-by-location', materialId], ['materials'], ['material', materialId],
        ['transactions'], ['stockLedger'], ['realtimeStock'], ['dashboard-data'],
      ]) void queryClient.invalidateQueries({ queryKey })
    },
  })
  const missing = stock.data?.unlocated_stock ?? 0
  const allowedLocations = (locations.data ?? []).filter(location =>
    location.is_active && ['warehouse', 'zone', 'rack', 'bin', 'production'].includes(location.location_type ?? location.type ?? '')
  )
  const error = stock.error || locations.error || materials.error || assignment.error
  return (
    <Card>
      <CardHeader>
        <CardTitle>Assign Existing Stock</CardTitle>
        <CardDescription>Assign stock already included in your total to its physical storage location. Total stock stays the same.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Item</Label>
          <Select value={materialId} disabled={assignment.isPending} onValueChange={value => {
            setMaterialId(value); setLocationId(''); assignment.reset()
          }}>
            <SelectTrigger aria-label="Item to locate"><SelectValue placeholder="Select an item" /></SelectTrigger>
            <SelectContent>
              {(materials.data?.items ?? []).map(material => (
                <SelectItem key={material.id} value={material.id}>{material.code} — {material.name}</SelectItem>
              ))}
              {stock.data && !materials.data?.items.some(material => material.id === materialId) && (
                <SelectItem value={materialId}>{stock.data.material_code} — {stock.data.material_name}</SelectItem>
              )}
            </SelectContent>
          </Select>
        </div>
        {stock.isFetching && materialId && <p>Checking location balances…</p>}
        {stock.data && (
          <div className="rounded-lg bg-muted p-3 text-sm space-y-1">
            <p>Total stock: {stock.data.total_stock.toFixed(2)}</p>
            <p>Assigned to locations: {stock.data.located_stock.toFixed(2)}</p>
            <p className="font-medium">Needs a location: {missing.toFixed(2)}</p>
          </div>
        )}
        {stock.data && missing === 0 && <p>No stock is waiting for a location assignment.</p>}
        {missing > 0 && <>
          <div className="space-y-2">
            <Label>Physical storage location</Label>
            <Select value={locationId} onValueChange={setLocationId} disabled={assignment.isPending}>
              <SelectTrigger aria-label="Physical storage location"><SelectValue placeholder="Select where this stock is stored" /></SelectTrigger>
              <SelectContent>{allowedLocations.map(location => (
                <SelectItem key={location.id} value={location.id}>{location.name}</SelectItem>
              ))}</SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="location-assignment-reason">Reason</Label>
            <Textarea id="location-assignment-reason" value={remarks} onChange={event => setRemarks(event.target.value)} disabled={assignment.isPending} />
          </div>
          <Button onClick={() => assignment.mutate()}
            disabled={!locationId || remarks.trim().length < 3 || stock.isFetching || assignment.isPending || !canInventoryWrite()}>
            {assignment.isPending ? 'Assigning…' : `Assign ${missing.toFixed(2)} Existing Units`}
          </Button>
        </>}
        {assignment.isSuccess && <p role="status">Location assignment recorded. Total stock was preserved.</p>}
        {error && <p role="alert" className="text-destructive">{isAxiosError(error) ? extractErrorMessage(error) : error.message}</p>}
      </CardContent>
    </Card>
  )
}
