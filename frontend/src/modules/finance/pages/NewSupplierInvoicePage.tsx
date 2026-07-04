import { useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation, useQuery } from "@tanstack/react-query"
import { financeService } from "@/services/finance.service"
import { supplyChainApi } from "@/services/supply-chain.service"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "@/hooks/use-toast"
import { ArrowLeft, Building2, CheckCircle2 } from "lucide-react"
import { format } from "date-fns"

export default function NewSupplierInvoicePage() {
  const navigate = useNavigate()
  
  // Quick fetch of suppliers for the dropdown
  const { data: suppliersData } = useQuery({
    queryKey: ["suppliers"],
    queryFn: async () => {
      const res = await supplyChainApi.listSuppliers()
      return res.data
    },
  })

  const [purchaseOrderQuery, setPurchaseOrderQuery] = useState("")

  const [formData, setFormData] = useState({
    supplier_id: "",
    purchase_order_id: "",
    supplier_invoice_ref: "",
    invoice_date: format(new Date(), "yyyy-MM-dd"),
    due_date: format(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), "yyyy-MM-dd"),
    subtotal: 0,
    tax_amount: 0,
    grand_total: 0,
    notes: "",
  })



  const { data: purchaseOrders = [] } = useQuery({
    queryKey: ["purchase-orders"],
    queryFn: async () => {
      const res = await supplyChainApi.listPurchaseOrders()
      return res.data
    },
  })

  const supplierPurchaseOrders = useMemo(() => {
    if (!formData.supplier_id) return purchaseOrders
    return purchaseOrders.filter((po) => po.supplier_id === formData.supplier_id)
  }, [purchaseOrders, formData.supplier_id])

  const purchaseOrderOptions = useMemo(() =>
    supplierPurchaseOrders.map((po) => ({
      id: po.id,
      label: `${po.po_number} · ${po.status} · ₹${po.total_amount.toLocaleString()}`,
      poNumber: po.po_number,
    })),
  [supplierPurchaseOrders])

  // Auto-calc grand total
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    if (name === "subtotal" || name === "tax_amount") {
      const numVal = parseFloat(value) || 0
      setFormData((prev) => {
        const next = { ...prev, [name]: numVal }
        next.grand_total = next.subtotal + next.tax_amount
        return next
      })
    } else if (name === "supplier_id") {
      setPurchaseOrderQuery("")
      setFormData((prev) => ({ ...prev, supplier_id: value, purchase_order_id: "" }))
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }))
    }
  }

  const createMutation = useMutation({
    mutationFn: financeService.createSupplierInvoice,
    onSuccess: (data) => {
      toast({
        title: "Supplier Invoice Created",
        description: `Successfully logged AP invoice ${data.invoice_number}`,
      })
      navigate("/finance/supplier-invoices")
    },
    onError: (err: any) => {
      toast({
        title: "Creation Failed",
        description: err.response?.data?.detail || err.message,
        variant: "destructive",
      })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.supplier_id) {
      toast({
        title: "Validation Error",
        description: "Supplier is required",
        variant: "destructive",
      })
      return
    }
    createMutation.mutate(formData)
  }

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/finance/supplier-invoices")} aria-label="Back to supplier invoices">
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Building2 className="w-6 h-6 text-amber-500" />
            Log Supplier Invoice (AP)
          </h1>
          <p className="text-slate-500 text-sm">Enter the details from your vendor's invoice into Accounts Payable</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Invoice Entry</CardTitle>
          <CardDescription>Fill out the vendor details, references, and amounts.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Supplier *</label>
                <select
                  name="supplier_id"
                  className="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-800 dark:bg-slate-950 dark:ring-offset-slate-950 dark:focus-visible:ring-slate-300"
                  value={formData.supplier_id}
                  onChange={handleChange}
                  required
                >
                  <option value="" disabled>Select Supplier</option>
                  {suppliersData?.map((s) => (
                    <option key={s.id} value={s.id}>{s.name} ({s.code})</option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Supplier Invoice Ref</label>
                <Input
                  name="supplier_invoice_ref"
                  placeholder="e.g. INV-99812A"
                  value={formData.supplier_invoice_ref}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Purchase Order (optional)</label>
                <Input
                  list="supplier-po-options"
                  placeholder={formData.supplier_id ? "Search by PO number" : "Select supplier first"}
                  value={purchaseOrderQuery}
                  onChange={(event) => {
                    const value = event.target.value
                    setPurchaseOrderQuery(value)
                    const exact = purchaseOrderOptions.find((option) => option.poNumber === value || option.label === value)
                    setFormData((prev) => ({ ...prev, purchase_order_id: exact?.id ?? "" }))
                  }}
                  disabled={!formData.supplier_id}
                />
                <datalist id="supplier-po-options">
                  {purchaseOrderOptions.map((option) => (
                    <option key={option.id} value={option.poNumber}>
                      {option.label}
                    </option>
                  ))}
                </datalist>
                {formData.purchase_order_id ? (
                  <p className="text-xs text-slate-500">Purchase order selected</p>
                ) : (
                  <p className="text-xs text-slate-500">Pick a supplier PO to link the invoice.</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Invoice Date *</label>
                <Input
                  type="date"
                  name="invoice_date"
                  value={formData.invoice_date}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Due Date *</label>
                <Input
                  type="date"
                  name="due_date"
                  value={formData.due_date}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 border-t pt-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-500">Subtotal *</label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 text-slate-500">₹</span>
                  <Input
                    type="number"
                    step="0.01"
                    name="subtotal"
                    className="pl-7"
                    value={formData.subtotal}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-500">Tax Amount</label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 text-slate-500">₹</span>
                  <Input
                    type="number"
                    step="0.01"
                    name="tax_amount"
                    className="pl-7"
                    value={formData.tax_amount}
                    onChange={handleChange}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-bold text-slate-900 dark:text-white">Grand Total</label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 font-bold">₹</span>
                  <Input
                    readOnly
                    type="number"
                    name="grand_total"
                    className="pl-7 bg-slate-50 border-transparent font-bold"
                    value={formData.grand_total}
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2 border-t pt-4">
              <label className="text-sm font-medium">Internal Notes</label>
              <Textarea
                rows={3}
                name="notes"
                placeholder="Optional internal notes"
                value={formData.notes}
                onChange={handleChange}
              />
            </div>

            <div className="pt-4 flex justify-end gap-3 border-t">
              <Button type="button" variant="outline" onClick={() => navigate("/finance/supplier-invoices")}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending} className="bg-amber-600 hover:bg-amber-700">
                {createMutation.isPending ? "Logging..." : (
                  <>
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Log Invoice
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
