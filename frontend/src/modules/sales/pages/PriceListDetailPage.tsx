/**
 * Price List Detail Page
 * Line management: add, edit, and remove product-price entries.
 * REQ-SP-002, Phase 1A Hardened with ProductPickerModal, UOM & Metadata enrichment.
 */

import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { TableSkeleton } from '@/components/shared/LoadingSkeleton'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { priceListsApi } from '@/services/sales.service'
import { PriceList, PriceListLine } from '@/types/sales.types'
import { ArrowLeft, Edit2, Trash2, Plus } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { ProductPickerModal } from '@/modules/sales/components/ProductPickerModal'

export default function PriceListDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()

  const [priceList, setPriceList] = useState<PriceList | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Add product dialog
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [addLoading, setAddLoading] = useState(false)

  // Inline edit state
  const [editingLineId, setEditingLineId] = useState<string | null>(null)
  const [editPrice, setEditPrice] = useState('')
  const editInputRef = useRef<HTMLInputElement>(null)

  // Remove confirmation
  const [removeLine, setRemoveLine] = useState<PriceListLine | null>(null)
  const [removeLoading, setRemoveLoading] = useState(false)

  const loadPriceList = async () => {
    if (!id) return
    try {
      setError(null)
      const pl = await priceListsApi.get(id)
      setPriceList(pl)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load price list')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPriceList()
  }, [id])

  // Focus inline edit input when editing starts
  useEffect(() => {
    if (editingLineId && editInputRef.current) {
      editInputRef.current.focus()
    }
  }, [editingLineId])

  const handleAddProduct = async (payload: {
    product_id: string
    product_type: 'variant' | 'finished_product'
    unit_price: number
  }) => {
    setAddLoading(true)
    try {
      const updated = await priceListsApi.addLine(id!, payload)
      setPriceList(updated)
      toast({ title: 'Product added to price list' })
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? err?.message ?? 'Failed to add product'
      toast({ title: detail, variant: 'destructive' })
      throw new Error(detail)
    } finally {
      setAddLoading(false)
    }
  }

  const handleEditSave = async (line: PriceListLine) => {
    const price = parseFloat(editPrice)
    if (isNaN(price) || price < 0) {
      toast({ title: 'Price must be 0 or greater', variant: 'destructive' })
      return
    }
    try {
      const updated = await priceListsApi.updateLine(id!, {
        product_id: line.product_id,
        product_type: line.product_type,
        unit_price: price,
      })
      setPriceList(updated)
      setEditingLineId(null)
      toast({ title: 'Price updated successfully' })
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? err?.message ?? 'Failed to update price'
      toast({ title: detail, variant: 'destructive' })
    }
  }

  const handleRemoveLine = async () => {
    if (!removeLine) return
    setRemoveLoading(true)
    try {
      await priceListsApi.removeLine(id!, removeLine.product_id, removeLine.product_type)
      setPriceList((prev) =>
        prev
          ? {
              ...prev,
              lines: prev.lines.filter(
                (l) =>
                  !(
                    l.product_id === removeLine.product_id &&
                    l.product_type === removeLine.product_type
                  )
              ),
            }
          : prev
      )
      toast({ title: 'Product removed from price list' })
      setRemoveLine(null)
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? err?.message ?? 'Failed to remove product'
      toast({ title: detail, variant: 'destructive' })
    } finally {
      setRemoveLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <TableSkeleton />
      </div>
    )
  }

  if (error || !priceList) {
    return (
      <div className="p-8 text-red-600">
        {error ?? 'Price list not found'}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/sales/price-lists')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-gray-900">{priceList.name}</h1>
              {priceList.is_default && (
                <Badge className="bg-blue-100 text-blue-800">Default</Badge>
              )}
              {priceList.is_active ? (
                <Badge className="bg-green-100 text-green-800">Active</Badge>
              ) : (
                <Badge className="bg-gray-100 text-gray-600">Inactive</Badge>
              )}
            </div>
            <p className="text-sm text-gray-500 mt-1">
              Valid from {new Date(priceList.valid_from).toLocaleDateString()}
              {priceList.valid_to
                ? ` to ${new Date(priceList.valid_to).toLocaleDateString()}`
                : ' (Open-ended)'}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/sales/price-lists/${id}/edit`)}
          >
            <Edit2 className="mr-2 h-3 w-3" />
            Edit Details
          </Button>
          <Button size="sm" onClick={() => setShowAddDialog(true)}>
            <Plus className="mr-2 h-3 w-3" />
            Add Product
          </Button>
        </div>
      </div>

      {/* Lines table */}
      {priceList.lines.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg font-medium">No products have been added to this price list yet.</p>
          <Button className="mt-4" onClick={() => setShowAddDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add First Product
          </Button>
        </div>
      ) : (
        <div className="border rounded-md bg-white overflow-hidden shadow-sm">
          <Table>
            <TableHeader>
              <TableRow className="bg-gray-50/75">
                <TableHead>Product / SKU</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>UOM</TableHead>
                <TableHead className="text-right">Unit Price</TableHead>
                <TableHead className="w-20 text-center">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {priceList.lines.map((line) => {
                const lineKey = line.id || `${line.product_type}-${line.product_id}`
                const isOrphaned = Boolean(line.is_orphaned)
                const isInactive = Boolean(line.is_inactive)

                return (
                  <TableRow key={lineKey} className="hover:bg-gray-50/50">
                    {/* SKU & Name Column */}
                    <TableCell>
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <span
                            className="font-mono text-xs font-semibold text-gray-900"
                            title={`Product ID: ${line.product_id}`}
                          >
                            {line.product_code || `Product ${line.product_id.slice(0, 8)}...`}
                          </span>
                          {isInactive && (
                            <Badge
                              variant="outline"
                              className="text-[10px] bg-gray-100 text-gray-600 border-gray-300"
                            >
                              Inactive
                            </Badge>
                          )}
                          {isOrphaned && (
                            <Badge
                              variant="outline"
                              className="text-[10px] bg-amber-50 text-amber-700 border-amber-300"
                            >
                              Orphaned
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-gray-500">
                          {line.product_name ||
                            (isOrphaned ? 'Product no longer in active catalog' : '—')}
                        </p>
                      </div>
                    </TableCell>

                    {/* Type Badge Column */}
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={`text-xs ${
                          line.product_type === 'variant'
                            ? 'bg-blue-50 text-blue-700 border-blue-200'
                            : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        }`}
                      >
                        {line.product_type === 'variant' ? 'Variant' : 'Finished Good'}
                      </Badge>
                    </TableCell>

                    {/* UOM Column */}
                    <TableCell className="text-xs text-gray-600 font-medium">
                      {line.uom_code || line.uom_name || '—'}
                    </TableCell>

                    {/* Unit Price Column (Inline Editable) */}
                    <TableCell className="text-right">
                      {editingLineId === (line.id || line.product_id) ? (
                        <div className="flex items-center justify-end gap-1.5">
                          <span className="text-xs text-gray-400">₹</span>
                          <Input
                            ref={editInputRef}
                            type="number"
                            min="0"
                            step="0.01"
                            className="w-28 text-right font-mono h-8 text-sm"
                            value={editPrice}
                            onChange={(e) => setEditPrice(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleEditSave(line)
                              if (e.key === 'Escape') setEditingLineId(null)
                            }}
                            onBlur={() => handleEditSave(line)}
                          />
                        </div>
                      ) : (
                        <span
                          className="font-medium font-mono text-sm text-gray-900 cursor-pointer hover:underline"
                          onClick={() => {
                            setEditingLineId(line.id || line.product_id)
                            setEditPrice(String(line.unit_price))
                          }}
                          title="Click to edit unit price"
                        >
                          ₹{line.unit_price.toFixed(4)}
                        </span>
                      )}
                    </TableCell>

                    {/* Actions Column */}
                    <TableCell>
                      <div className="flex items-center justify-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-gray-500 hover:text-gray-900"
                          onClick={() => {
                            setEditingLineId(line.id || line.product_id)
                            setEditPrice(String(line.unit_price))
                          }}
                          title="Edit Unit Price"
                        >
                          <Edit2 className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-destructive hover:text-destructive hover:bg-red-50"
                          onClick={() => setRemoveLine(line)}
                          title="Remove from Price List"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Searchable Product Picker Modal */}
      <ProductPickerModal
        open={showAddDialog}
        onOpenChange={setShowAddDialog}
        onAddProduct={handleAddProduct}
        loading={addLoading}
      />

      {/* Disambiguated Remove Confirmation Dialog */}
      <Dialog
        open={!!removeLine}
        onOpenChange={(open) => {
          if (!open) setRemoveLine(null)
        }}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Remove product from price list?</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 py-1">
            <p className="text-sm text-muted-foreground">
              This will remove the pricing entry for:
            </p>
            <div className="bg-gray-50 p-2.5 rounded border text-xs space-y-1">
              <p className="font-bold text-gray-900">
                {removeLine?.product_name || 'Product'}
              </p>
              <div className="flex items-center gap-2 text-gray-600">
                <span>Code: <code className="font-mono font-semibold">{removeLine?.product_code || removeLine?.product_id.slice(0, 8)}</code></span>
                <span>•</span>
                <Badge variant="outline" className="text-[10px] uppercase">
                  {removeLine?.product_type === 'variant' ? 'Variant' : 'Finished Good'}
                </Badge>
              </div>
            </div>
            <p className="text-xs text-gray-500">
              The product itself will not be deleted from the master catalog.
            </p>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRemoveLine(null)}
              disabled={removeLoading}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleRemoveLine}
              disabled={removeLoading}
            >
              {removeLoading ? 'Removing…' : 'Remove'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
