import { useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { Plus, Trash2 } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useToast } from "@/hooks/use-toast"
import { clientService, type ClientCatalogItem } from "../services/client.service"
import { formatCurrency } from "../utils/formatters"

type DraftLine = {
  catalog_key: string
  product_id: string
  product_type: string
  uom_id: string
  quantity: number
  tax_rate: number
}

const emptyLine = (): DraftLine => ({
  catalog_key: "",
  product_id: "",
  product_type: "",
  uom_id: "",
  quantity: 1,
  tax_rate: 0,
})

const catalogKey = (item: ClientCatalogItem) => `${item.product_type}:${item.product_id}`

export default function ClientNewOrder() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [deliveryDate, setDeliveryDate] = useState("")
  const [notes, setNotes] = useState("")
  const [lines, setLines] = useState<DraftLine[]>([emptyLine()])

  const catalogQuery = useQuery({
    queryKey: ["client-catalog"],
    queryFn: () => clientService.listCatalog(),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      clientService.createOrder({
        delivery_date: deliveryDate || undefined,
        notes: notes || undefined,
        lines: lines.map((line) => ({
          product_id: line.product_id,
          product_type: line.product_type,
          uom_id: line.uom_id,
          quantity: Number(line.quantity),
          tax_rate: Number(line.tax_rate ?? 0),
        })),
      }),
    onSuccess: (order) => {
      toast({ title: "Order submitted", description: "Your order is waiting for manager approval." })
      navigate(`/client/orders/${order.id}`)
    },
    onError: (error: Error) => {
      toast({ title: "Unable to submit order", description: error.message, variant: "destructive" })
    },
  })

  const updateLine = (index: number, patch: Partial<DraftLine>) => {
    setLines((current) => current.map((line, idx) => (idx === index ? { ...line, ...patch } : line)))
  }

  const catalog = catalogQuery.data ?? []

  const selectProduct = (index: number, key: string) => {
    const item = catalog.find((candidate) => catalogKey(candidate) === key)
    if (!item) return
    updateLine(index, {
      catalog_key: key,
      product_id: item.product_id,
      product_type: item.product_type,
      uom_id: item.uom_id ?? "",
    })
  }

  const canSubmit =
    !catalogQuery.isLoading &&
    lines.every((line) => line.product_id && line.product_type && line.uom_id && Number(line.quantity) > 0)

  return (
    <div className="space-y-6">
      <section className="rounded-[32px] border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <p className="text-xs uppercase tracking-[0.25em] text-slate-500">New Order</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900 sm:text-3xl">Submit a fresh order for approval.</h1>
        <p className="mt-3 max-w-2xl text-sm text-slate-600">
          Add products, quantities, and an optional delivery date. Pricing is resolved from the active sales price list when unit price is left blank.
        </p>
      </section>

      <Card className="rounded-[28px] border-slate-200/70">
        <CardHeader>
          <CardTitle>Order Details</CardTitle>
          <CardDescription>Submitted orders go to manager approval before inventory and production planning.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {createMutation.isError && (
            <Alert variant="destructive">
              <AlertTitle>Submission failed</AlertTitle>
              <AlertDescription>{(createMutation.error as Error).message}</AlertDescription>
            </Alert>
          )}

          {catalogQuery.isError && (
            <Alert variant="destructive">
              <AlertTitle>Catalog unavailable</AlertTitle>
              <AlertDescription>Products could not be loaded. Please try again or contact support.</AlertDescription>
            </Alert>
          )}

          {!catalogQuery.isLoading && catalog.length === 0 && (
            <Alert>
              <AlertTitle>No orderable products yet</AlertTitle>
              <AlertDescription>
                Ask your account manager to publish products to an active sales price list before placing a fresh order.
              </AlertDescription>
            </Alert>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Requested delivery date</label>
              <Input type="date" value={deliveryDate} onChange={(event) => setDeliveryDate(event.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Notes</label>
              <Input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Optional order notes" />
            </div>
          </div>

          <div className="space-y-4">
            {lines.map((line, index) => (
              <div key={index} className="grid gap-3 rounded-3xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-2 lg:grid-cols-6">
                <div className="sm:col-span-2 lg:col-span-3">
                  <label className="mb-1 block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">Product</label>
                  <Select value={line.catalog_key} onValueChange={(value) => selectProduct(index, value)} disabled={catalogQuery.isLoading || catalog.length === 0}>
                    <SelectTrigger>
                      <SelectValue placeholder={catalogQuery.isLoading ? "Loading catalog..." : "Select product"} />
                    </SelectTrigger>
                    <SelectContent>
                      {catalog.map((item) => (
                        <SelectItem key={catalogKey(item)} value={catalogKey(item)} disabled={!item.is_orderable}>
                          {item.product_code ? `${item.product_code} - ` : ""}
                          {item.product_name}
                          {!item.is_orderable ? " (setup incomplete)" : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">UOM</label>
                  <Input
                    value={catalog.find((item) => catalogKey(item) === line.catalog_key)?.uom_code ?? ""}
                    readOnly
                    placeholder="Auto"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">Qty</label>
                  <Input type="number" min="1" value={line.quantity} onChange={(event) => updateLine(index, { quantity: Number(event.target.value) })} />
                </div>
                <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-1">
                  <div className="flex-1">
                    <label className="mb-1 block text-xs font-medium uppercase tracking-[0.16em] text-slate-500">Price</label>
                    <Input
                      value={formatCurrency(catalog.find((item) => catalogKey(item) === line.catalog_key)?.unit_price)}
                      readOnly
                      placeholder="Auto"
                    />
                  </div>
                  <Button variant="ghost" size="icon" disabled={lines.length === 1} onClick={() => setLines((current) => current.filter((_, idx) => idx !== index))} aria-label="Remove line">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
            <Button type="button" variant="outline" className="w-full rounded-full sm:w-auto" onClick={() => setLines((current) => [...current, emptyLine()])}>
              <Plus className="mr-2 h-4 w-4" />
              Add Line
            </Button>
            <Button className="w-full rounded-full sm:w-auto" disabled={!canSubmit || createMutation.isPending} onClick={() => createMutation.mutate()}>
              Submit For Approval
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
