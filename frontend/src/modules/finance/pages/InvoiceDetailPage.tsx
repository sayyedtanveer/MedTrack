import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, CreditCard, Download, FileText, Receipt, Send, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { financeService } from "@/services/finance.service"
import { documentService } from "@/services/document.service"
import { toast } from "@/hooks/use-toast"

const STATUS_STYLES: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700 border-slate-200",
  SENT: "bg-blue-100 text-blue-700 border-blue-200",
  PARTIAL: "bg-amber-100 text-amber-700 border-amber-200",
  PAID: "bg-emerald-100 text-emerald-700 border-emerald-200",
  OVERDUE: "bg-red-100 text-red-700 border-red-200",
  CANCELLED: "bg-zinc-100 text-zinc-500 border-zinc-200",
  VOID: "bg-zinc-100 text-zinc-500 border-zinc-200",
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value || 0)
}

export default function InvoiceDetailPage() {
  const navigate = useNavigate()
  const { invoiceId } = useParams()
  const queryClient = useQueryClient()
  const [paymentAmount, setPaymentAmount] = useState("")
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10))
  const [paymentMethod, setPaymentMethod] = useState("BANK_TRANSFER")
  const [referenceNumber, setReferenceNumber] = useState("")
  const [paymentNotes, setPaymentNotes] = useState("")
  const [documentLoading, setDocumentLoading] = useState(false)

  const { data: invoice, isLoading, isError } = useQuery({
    queryKey: ["finance-invoice", invoiceId],
    queryFn: () => financeService.getInvoice(invoiceId!),
    enabled: !!invoiceId,
  })

  useEffect(() => {
    if (invoice) {
      setPaymentAmount(invoice.balance_due > 0 ? invoice.balance_due.toFixed(2) : "")
    }
  }, [invoice])

  const refreshFinance = () => {
    queryClient.invalidateQueries({ queryKey: ["finance-invoice", invoiceId] })
    queryClient.invalidateQueries({ queryKey: ["finance-dashboard"] })
    queryClient.invalidateQueries({ queryKey: ["invoices"] })
  }

  const sendMutation = useMutation({
    mutationFn: () => financeService.sendInvoice(invoiceId!),
    onSuccess: () => {
      toast({ title: "Invoice sent" })
      refreshFinance()
    },
    onError: (error: any) => {
      toast({
        title: "Unable to send invoice",
        description: error.message,
        variant: "destructive",
      })
    },
  })

  const voidMutation = useMutation({
    mutationFn: () => financeService.voidInvoice(invoiceId!),
    onSuccess: () => {
      toast({ title: "Invoice voided" })
      refreshFinance()
    },
    onError: (error: any) => {
      toast({
        title: "Unable to void invoice",
        description: error.message,
        variant: "destructive",
      })
    },
  })

  const paymentMutation = useMutation({
    mutationFn: () =>
      financeService.recordPayment({
        invoice_id: invoiceId!,
        amount: parseFloat(paymentAmount),
        payment_date: paymentDate,
        payment_method: paymentMethod,
        reference_number: referenceNumber || undefined,
        notes: paymentNotes || undefined,
      }),
    onSuccess: () => {
      toast({ title: "Payment recorded" })
      setReferenceNumber("")
      setPaymentNotes("")
      refreshFinance()
    },
    onError: (error: any) => {
      toast({
        title: "Unable to record payment",
        description: error.message,
        variant: "destructive",
      })
    },
  })

  const handleDownloadPDF = async () => {
    if (!invoiceId || documentLoading) return
    setDocumentLoading(true)
    try {
      const document = await documentService.generateDocument('invoice', invoiceId)
      await documentService.downloadDocumentByUrl(document.id, `INV-${invoice?.invoice_number}.pdf`)
    } catch (e: any) {
      toast({
        title: "Failed to generate PDF",
        variant: "destructive",
      })
    } finally {
      setDocumentLoading(false)
    }
  }

  const handlePrintPDF = async () => {
    if (!invoiceId || documentLoading) return
    setDocumentLoading(true)
    try {
      const document = await documentService.generateDocument('invoice', invoiceId)
      const previewUrl = await documentService.previewDocument(document.id)
      const printWindow = window.open(previewUrl, '_blank')
      if (printWindow) {
        printWindow.onload = () => {
          printWindow.print()
        }
      }
    } catch (e: any) {
      toast({
        title: "Failed to generate PDF for printing",
        variant: "destructive",
      })
    } finally {
      setDocumentLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="p-6 md:p-8">
        <div className="space-y-4">
          <div className="h-10 w-48 animate-pulse rounded-xl bg-slate-100" />
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="h-40 animate-pulse rounded-2xl bg-slate-100 lg:col-span-2" />
            <div className="h-40 animate-pulse rounded-2xl bg-slate-100" />
          </div>
        </div>
      </div>
    )
  }

  if (isError || !invoice) {
    return (
      <div className="p-6 md:p-8">
        <Card>
          <CardContent className="flex flex-col items-start gap-4 p-6">
            <div>
              <h1 className="text-lg font-semibold text-slate-900">Invoice not available</h1>
              <p className="text-sm text-slate-500">We could not load this invoice right now.</p>
            </div>
            <Button variant="outline" onClick={() => navigate("/finance/invoices")}>
              Back to invoices
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const canSend = invoice.status === "DRAFT"
  const canVoid = !["PAID", "VOID", "CANCELLED"].includes(invoice.status)
  const canRecordPayment = !["VOID", "CANCELLED", "PAID"].includes(invoice.status) && invoice.balance_due > 0

  return (
    <div className="space-y-6 p-4 md:p-6 xl:p-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-start gap-3">
          <Button variant="outline" size="icon" onClick={() => navigate("/finance/invoices")} aria-label="Back to invoices">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">Finance</p>
            <h1 className="text-2xl font-semibold text-slate-900">{invoice.invoice_number}</h1>
            <p className="text-sm text-slate-500">
              {invoice.client_name} · Due {invoice.due_date}
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
          <Button
            variant="outline"
            className="w-full sm:w-auto"
            onClick={handlePrintPDF}
            disabled={documentLoading}
          >
            <FileText className="mr-2 h-4 w-4" />
            {documentLoading ? '…' : 'Print'}
          </Button>
          <Button
            variant="outline"
            className="w-full sm:w-auto"
            onClick={handleDownloadPDF}
            disabled={documentLoading}
          >
            <Download className="mr-2 h-4 w-4" />
            {documentLoading ? '…' : 'Download PDF'}
          </Button>
          {canSend && (
            <Button
              className="w-full sm:w-auto"
              onClick={() => sendMutation.mutate()}
              disabled={sendMutation.isPending}
            >
              <Send className="mr-2 h-4 w-4" />
              {sendMutation.isPending ? "Sending..." : "Send Invoice"}
            </Button>
          )}
          {canVoid && (
            <Button
              variant="outline"
              className="w-full border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 sm:w-auto"
              onClick={() => voidMutation.mutate()}
              disabled={voidMutation.isPending}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              {voidMutation.isPending ? "Voiding..." : "Void Invoice"}
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <CardTitle>Invoice Summary</CardTitle>
              <CardDescription>Customer billing snapshot with totals and status.</CardDescription>
            </div>
            <span className={`inline-flex w-fit items-center rounded-full border px-3 py-1 text-xs font-semibold ${STATUS_STYLES[invoice.status] || STATUS_STYLES.DRAFT}`}>
              {invoice.status}
            </span>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Client</p>
              <p className="mt-2 text-base font-semibold text-slate-900">{invoice.client_name}</p>
              <p className="mt-1 text-sm text-slate-500">{invoice.client_address || "Address not captured"}</p>
              <p className="mt-1 text-sm text-slate-500">GST: {invoice.client_gst_number || "—"}</p>
            </div>
            <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Dates</p>
              <div className="mt-2 space-y-1 text-sm text-slate-600">
                <p>Invoice date: {invoice.invoice_date}</p>
                <p>Due date: {invoice.due_date}</p>
                <p>Sales order: {invoice.sales_order_id || "Manual invoice"}</p>
              </div>
            </div>
            <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Grand total</p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">{formatCurrency(invoice.grand_total)}</p>
            </div>
            <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Balance due</p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">{formatCurrency(invoice.balance_due)}</p>
              <p className="mt-1 text-sm text-slate-500">Paid so far: {formatCurrency(invoice.paid_amount)}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Totals</CardTitle>
            <CardDescription>Commercial totals for this invoice.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Subtotal</span>
              <span className="font-medium text-slate-900">{formatCurrency(invoice.subtotal)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Discount</span>
              <span className="font-medium text-slate-900">{formatCurrency(invoice.discount_amount)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Tax</span>
              <span className="font-medium text-slate-900">{formatCurrency(invoice.tax_amount)}</span>
            </div>
            <div className="border-t border-slate-100 pt-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-700">Grand total</span>
                <span className="text-lg font-semibold text-slate-900">{formatCurrency(invoice.grand_total)}</span>
              </div>
            </div>
            {invoice.terms && (
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-3 text-slate-600">
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Terms</p>
                <p className="mt-2">{invoice.terms}</p>
              </div>
            )}
            {invoice.notes && (
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-3 text-slate-600">
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Notes</p>
                <p className="mt-2 whitespace-pre-wrap">{invoice.notes}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {canRecordPayment && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-blue-600" />
              Record Payment
            </CardTitle>
            <CardDescription>Capture incoming cash against this invoice and keep AR current.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Amount</label>
              <Input value={paymentAmount} onChange={(event) => setPaymentAmount(event.target.value)} type="number" min="0" step="0.01" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Payment date</label>
              <Input value={paymentDate} onChange={(event) => setPaymentDate(event.target.value)} type="date" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Method</label>
              <select
                className="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                value={paymentMethod}
                onChange={(event) => setPaymentMethod(event.target.value)}
              >
                {["BANK_TRANSFER", "CASH", "CHEQUE", "ONLINE", "UPI", "OTHER"].map((method) => (
                  <option key={method} value={method}>
                    {method.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Reference</label>
              <Input value={referenceNumber} onChange={(event) => setReferenceNumber(event.target.value)} placeholder="Bank ref / cheque no." />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">Notes</label>
              <Textarea value={paymentNotes} onChange={(event) => setPaymentNotes(event.target.value)} rows={1} placeholder="Optional notes" />
            </div>
          </CardContent>
          <CardContent className="pt-0">
            <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
              <Button
                className="w-full sm:w-auto"
                onClick={() => paymentMutation.mutate()}
                disabled={paymentMutation.isPending || !paymentAmount || Number(paymentAmount) <= 0}
              >
                <Receipt className="mr-2 h-4 w-4" />
                {paymentMutation.isPending ? "Recording..." : "Record Payment"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-blue-600" />
              Invoice Lines
            </CardTitle>
            <CardDescription>Snapshot of the billed items and commercial values.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {invoice.lines.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">
                No invoice lines were stored for this invoice.
              </div>
            ) : (
              invoice.lines.map((line) => (
                <div key={line.id} className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                  <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p className="font-medium text-slate-900">{line.description || line.product_id}</p>
                      <p className="text-sm text-slate-500">
                        {line.product_type} · Qty {line.quantity} · Tax {line.tax_rate}%
                      </p>
                    </div>
                    <p className="text-base font-semibold text-slate-900">{formatCurrency(line.total)}</p>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Receipt className="h-4 w-4 text-emerald-600" />
              Payments & Receipts
            </CardTitle>
            <CardDescription>Every receipt posted against this invoice stays downloadable here.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {invoice.payments.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">
                No payments have been posted yet.
              </div>
            ) : (
              invoice.payments.map((payment) => (
                <div key={payment.id} className="flex flex-col gap-3 rounded-2xl border border-slate-100 bg-slate-50 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-medium text-slate-900">{payment.payment_number}</p>
                    <p className="text-sm text-slate-500">
                      {payment.payment_date} · {payment.payment_method.replace(/_/g, " ")}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <p className="font-semibold text-slate-900">{formatCurrency(payment.amount)}</p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => financeService.downloadReceiptPdf(payment.id, payment.payment_number)}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Receipt PDF
                    </Button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
