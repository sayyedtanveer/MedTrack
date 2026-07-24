/**
 * Price List Detail Page
 * Line management: add, edit, and remove product-price entries.
 * REQ-SP-002
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

export default function PriceListDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()

  const [priceList, setPriceList] = useState<PriceList | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Add product dialog
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [addProductId, setAddProductId] = useState('')
  const [addProductType, setAddProductType] = useState<'variant' | 'finished_product'>('variant')
  const [addPrice, setAddPrice] = useState('')
  const [addError, setAddError] = useState<string | null>(null)
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

  const handleAddLine = async () => {
    setAddError(null)
    const price = parseFloat(addPrice)
    if (!addProductId.trim()) {
      setAddError('Product ID is required')
      return
    }
    if (isNaN(price) || price < 0) {
      setAddError('Price must be 0 or greater')
      return
    }
    setAddLoading(true)
    try {
      const updated = await priceListsApi.addLine(id!, {
        product_id: addProductId.trim(),
        product_type: addProductType,
        unit_price: price,
      })
      setPriceList(updated)
      setShowAddDialog(false)
      setAddProductId('')
      setAddPrice('')
      setAddProductType('variant')
      toast({ title: 'Product added to price list' })
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? err?.message ?? 'Failed to add product'
      if (err?.response?.status === 409) {
        setAddError('This product is already in the price list.')
      } else {
        setAddError(detail)
      }
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
    } catch {
      toast({ title: 'Failed to update price', variant: 'destructive' })
    }
  }

  const handleRemoveLine = async () => {
    if (!removeLine) return
    setRemoveLoading(true)
    try {
      await priceListsApi.removeLine(id!, removeLine.product_id)
      setPriceList((prev) =>
        prev ? { ...prev, lines: prev.lines.filter((l) => l.id !== removeLine.id) } : prev
      )
      toast({ title: 'Product removed from price list' })
      setRemoveLine(null)
    } catch {
      toast({ title: 'Failed to remove product', variant: 'destructive' })
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
                <Badge variant="secondary">Inactive</Badge>
              )}
            </div>
            <p className="text-sm text-gray-500 mt-0.5">
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
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Product ID / SKU</TableHead>
              <TableHead>Type</TableHead>
              <TableHead className="text-right">Unit Price</TableHead>
              <TableHead className="w-20" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {priceList.lines.map((line) => (
              <TableRow key={line.id}>
                <TableCell className="font-mono text-xs">{line.product_id}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-xs">
                    {line.product_type === 'variant' ? 'Variant' : 'Finished Good'}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  {editingLineId === line.id ? (
                    <div className="flex items-center justify-end gap-2">
                      <Input
                        ref={editInputRef}
                        type="number"
                        min="0"
                        step="0.01"
                        className="w-28 text-right"
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
                    <span className="font-medium">{line.unit_price.toFixed(4)}</span>
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => {
                        setEditingLineId(line.id)
                        setEditPrice(String(line.unit_price))
                      }}
                    >
                      <Edit2 className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive hover:text-destructive"
                      onClick={() => setRemoveLine(line)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Add Product Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add Product to Price List</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <label className="text-sm font-medium">Product ID (UUID)</label>
              <Input
                placeholder="Paste product UUID"
                value={addProductId}
                onChange={(e) => setAddProductId(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Product Type</label>
              <select
                className="w-full h-9 border rounded-md px-3 text-sm"
                value={addProductType}
                onChange={(e) => setAddProductType(e.target.value as 'variant' | 'finished_product')}
              >
                <option value="variant">Variant</option>
                <option value="finished_product">Finished Product</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Unit Price</label>
              <Input
                type="number"
                min="0"
                step="0.01"
                placeholder="0.00"
                value={addPrice}
                onChange={(e) => setAddPrice(e.target.value)}
              />
            </div>
            {addError && <p className="text-xs text-destructive">{addError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddLine} disabled={addLoading}>
              {addLoading ? 'Adding…' : 'Add Product'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Remove Confirmation */}
      <Dialog open={!!removeLine} onOpenChange={(open) => { if (!open) setRemoveLine(null) }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Remove product from price list?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            This will remove the pricing entry for product{' '}
            <code className="font-mono text-xs">{removeLine?.product_id}</code>. The product itself is not affected.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoveLine(null)} disabled={removeLoading}>
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
