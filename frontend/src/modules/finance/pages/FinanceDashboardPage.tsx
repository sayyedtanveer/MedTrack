import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { financeService, type Invoice, type SupplierInvoice } from "@/services/finance.service"
import { Link, useNavigate } from "react-router-dom"
import {
  IndianRupee, TrendingUp, TrendingDown, AlertCircle, CheckCircle2,
  Clock, FileText, Plus, Search, RefreshCw, Eye,
  CreditCard, Building2, BarChart3, ArrowUpRight, ArrowDownRight,
  Settings2,
} from "lucide-react"
import { toast } from "@/hooks/use-toast"

const STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700 border-slate-200",
  SENT: "bg-blue-100 text-blue-700 border-blue-200",
  PARTIAL: "bg-amber-100 text-amber-700 border-amber-200",
  PAID: "bg-emerald-100 text-emerald-700 border-emerald-200",
  OVERDUE: "bg-red-100 text-red-700 border-red-200",
  CANCELLED: "bg-zinc-100 text-zinc-500 border-zinc-200",
  VOID: "bg-zinc-100 text-zinc-400 border-zinc-200",
  PENDING: "bg-orange-100 text-orange-700 border-orange-200",
}

function MetricCard({
  title, value, subtitle, icon: Icon, trend, color = "blue",
}: {
  title: string
  value: string
  subtitle?: string
  icon: React.ElementType
  trend?: "up" | "down" | "neutral"
  color?: "blue" | "green" | "red" | "amber" | "purple"
}) {
  const colorMap = {
    blue: "from-blue-500 to-blue-600",
    green: "from-emerald-500 to-emerald-600",
    red: "from-red-500 to-red-600",
    amber: "from-amber-500 to-amber-600",
    purple: "from-purple-500 to-purple-600",
  }
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className={`p-3 rounded-xl bg-gradient-to-br ${colorMap[color]} shadow-sm`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        {trend && (
          <span className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${
            trend === "up" ? "text-emerald-600 bg-emerald-50" :
            trend === "down" ? "text-red-600 bg-red-50" :
            "text-slate-500 bg-slate-50"
          }`}>
            {trend === "up" ? <ArrowUpRight className="w-3 h-3" /> :
             trend === "down" ? <ArrowDownRight className="w-3 h-3" /> : null}
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
      <p className="text-sm font-medium text-slate-600 dark:text-slate-400 mt-1">{title}</p>
      {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
    </div>
  )
}

function formatCurrency(n: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n)
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${STATUS_COLORS[status] || "bg-gray-100 text-gray-600 border-gray-200"}`}>
      {status}
    </span>
  )
}

// ── Payment Modal ─────────────────────────────────────────────────────────
function PaymentModal({
  invoice,
  onClose,
  onSuccess,
}: {
  invoice: Invoice
  onClose: () => void
  onSuccess: () => void
}) {
  const [amount, setAmount] = useState(invoice.balance_due.toFixed(2))
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10))
  const [paymentMethod, setPaymentMethod] = useState("BANK_TRANSFER")
  const [referenceNumber, setReferenceNumber] = useState("")

  const mutation = useMutation({
    mutationFn: () =>
      financeService.recordPayment({
        invoice_id: invoice.id,
        amount: parseFloat(amount),
        payment_date: paymentDate,
        payment_method: paymentMethod,
        reference_number: referenceNumber || undefined,
      }),
    onSuccess: () => {
      toast({ title: "Payment recorded successfully", variant: "default" })
      onSuccess()
      onClose()
    },
    onError: (e: any) => {
      toast({ title: "Payment failed", description: e.message, variant: "destructive" })
    },
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">Record Payment</h3>
        <p className="text-sm text-slate-500 mb-6">Invoice {invoice.invoice_number} — Balance: {formatCurrency(invoice.balance_due)}</p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Amount (₹)</label>
            <input
              id="payment-amount"
              type="number"
              step="0.01"
              max={invoice.balance_due}
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Payment Date</label>
            <input
              id="payment-date"
              type="date"
              value={paymentDate}
              onChange={(e) => setPaymentDate(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Method</label>
            <select
              id="payment-method"
              value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
            >
              {["BANK_TRANSFER", "CASH", "CHEQUE", "ONLINE", "UPI", "OTHER"].map((m) => (
                <option key={m} value={m}>{m.replace("_", " ")}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Reference # (optional)</label>
            <input
              id="payment-ref"
              type="text"
              value={referenceNumber}
              onChange={(e) => setReferenceNumber(e.target.value)}
              placeholder="Bank ref / cheque number"
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            id="cancel-payment-btn"
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          >
            Cancel
          </button>
          <button
            id="submit-payment-btn"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg text-sm font-medium hover:from-blue-700 hover:to-blue-800 transition-all disabled:opacity-50 shadow-sm"
          >
            {mutation.isPending ? "Processing..." : "Record Payment"}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main Finance Dashboard ────────────────────────────────────────────────
export default function FinanceDashboardPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [activeTab, setActiveTab] = useState<"overview" | "invoices" | "supplier" | "ledger">("overview")
  const [statusFilter, setStatusFilter] = useState("")
  const [searchQuery, setSearchQuery] = useState("")
  const [paymentModalInvoice, setPaymentModalInvoice] = useState<Invoice | null>(null)
  const [siPage, setSiPage] = useState(1)
  const [invPage, setInvPage] = useState(1)

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ["finance-dashboard"],
    queryFn: financeService.getDashboard,
    retry: 1,
  })

  const { data: invoicesData, isLoading: invLoading } = useQuery({
    queryKey: ["invoices", statusFilter, invPage],
    queryFn: () => financeService.listInvoices({
      status: statusFilter || undefined,
      page: invPage,
      page_size: 15,
    }),
    enabled: activeTab === "invoices" || activeTab === "overview",
  })

  const { data: arAging } = useQuery({
    queryKey: ["ar-aging"],
    queryFn: financeService.getARaging,
    enabled: activeTab === "overview",
  })

  const { data: siData } = useQuery({
    queryKey: ["supplier-invoices", siPage],
    queryFn: () => financeService.listSupplierInvoices({ page: siPage, page_size: 15 }),
    enabled: activeTab === "supplier",
  })

  const sendMutation = useMutation({
    mutationFn: (id: string) => financeService.sendInvoice(id),
    onSuccess: () => {
      toast({ title: "Invoice sent successfully" })
      qc.invalidateQueries({ queryKey: ["invoices"] })
    },
    onError: (e: any) => toast({ title: "Error", description: e.message, variant: "destructive" }),
  })

  const filteredInvoices = (invoicesData?.items || []).filter(
    (inv) =>
      !searchQuery ||
      inv.invoice_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inv.client_name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header */}
      <div className="bg-white dark:bg-slate-800 border-b border-slate-100 dark:border-slate-700 px-8 py-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <div className="p-2 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl">
                <IndianRupee className="w-5 h-5 text-white" />
              </div>
              Finance & Accounting
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              AR/AP · Invoices · Payments · Ledger
            </p>
          </div>
          <div className="flex gap-3">
            <button
              id="refresh-finance-btn"
              onClick={() => qc.invalidateQueries({ queryKey: ["finance-dashboard"] })}
              className="flex items-center gap-2 px-4 py-2 border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-xl text-sm hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
            <button
              id="finance-settings-btn"
              onClick={() => navigate("/finance/settings")}
              className="flex items-center gap-2 px-4 py-2 border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-xl text-sm hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              <Settings2 className="w-4 h-4" />
              Settings
            </button>
            <button
              id="new-invoice-btn"
              onClick={() => navigate("/finance/invoices/new")}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-xl text-sm font-medium hover:from-emerald-700 hover:to-teal-700 transition-all shadow-sm"
            >
              <Plus className="w-4 h-4" />
              New Invoice
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mt-6 bg-slate-100 dark:bg-slate-700/50 p-1 rounded-xl w-fit">
          {[
            { id: "overview", label: "Overview", icon: BarChart3 },
            { id: "invoices", label: "Invoices", icon: FileText },
            { id: "supplier", label: "Payables", icon: Building2 },
            { id: "ledger", label: "Ledger", icon: CreditCard },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              id={`tab-${id}`}
              onClick={() => setActiveTab(id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === id
                  ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm"
                  : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-8 py-6">
        {/* ── Overview Tab ─────────────────────────────────────────────── */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* KPI Cards */}
            {dashLoading ? (
              <div className="grid grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="bg-white rounded-2xl p-6 h-32 animate-pulse border border-slate-100" />
                ))}
              </div>
            ) : dashboard ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                  icon={TrendingUp}
                  title="Total Billed (AR)"
                  value={formatCurrency(dashboard.ar.total_billed)}
                  subtitle={`${dashboard.ar.open_count} open invoices`}
                  color="blue"
                />
                <MetricCard
                  icon={CheckCircle2}
                  title="Collected"
                  value={formatCurrency(dashboard.ar.total_collected)}
                  subtitle="Payments received"
                  color="green"
                />
                <MetricCard
                  icon={AlertCircle}
                  title="Outstanding (AR)"
                  value={formatCurrency(dashboard.ar.total_outstanding)}
                  subtitle="Balance due from clients"
                  color={dashboard.ar.total_outstanding > 0 ? "amber" : "green"}
                />
                <MetricCard
                  icon={TrendingDown}
                  title="Outstanding (AP)"
                  value={formatCurrency(dashboard.ap.outstanding)}
                  subtitle={`${dashboard.ap.open_count} supplier invoices`}
                  color="red"
                />
              </div>
            ) : null}

            {/* Revenue Trend + AR Aging */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Revenue Trend */}
              <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
                <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-blue-500" />
                  Revenue Trend (6 months)
                </h3>
                {dashboard?.revenue_trend?.length ? (
                  <div className="space-y-3">
                    {dashboard.revenue_trend.map((row) => {
                      const pct = row.revenue > 0 ? (row.collected / row.revenue) * 100 : 0
                      return (
                        <div key={row.month}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-slate-600 dark:text-slate-400">{row.month}</span>
                            <span className="font-medium text-slate-900 dark:text-white">{formatCurrency(row.revenue)}</span>
                          </div>
                          <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-2">
                            <div
                              className="bg-gradient-to-r from-blue-500 to-teal-500 h-2 rounded-full transition-all"
                              style={{ width: `${Math.min(pct, 100)}%` }}
                            />
                          </div>
                          <p className="text-xs text-slate-400 mt-0.5">{pct.toFixed(0)}% collected</p>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400 text-center py-8">No revenue data yet</p>
                )}
              </div>

              {/* AR Aging */}
              <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
                <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-amber-500" />
                  AR Aging by Client
                </h3>
                {arAging && arAging.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-slate-500 border-b border-slate-100 dark:border-slate-700">
                          <th className="pb-2 text-left font-medium">Client</th>
                          <th className="pb-2 text-right font-medium">Current</th>
                          <th className="pb-2 text-right font-medium text-amber-600">1-30d</th>
                          <th className="pb-2 text-right font-medium text-orange-600">31-60d</th>
                          <th className="pb-2 text-right font-medium text-red-600">60+d</th>
                          <th className="pb-2 text-right font-medium text-slate-700">Total</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-50 dark:divide-slate-700">
                        {arAging.slice(0, 6).map((row) => (
                          <tr key={row.client_id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50">
                            <td className="py-2 font-medium text-slate-700 dark:text-slate-300 truncate max-w-[100px]">{row.client_name}</td>
                            <td className="py-2 text-right text-slate-600">{formatCurrency(row.current_amount || 0)}</td>
                            <td className="py-2 text-right text-amber-600">{formatCurrency(row.overdue_1_30 || 0)}</td>
                            <td className="py-2 text-right text-orange-600">{formatCurrency(row.overdue_31_60 || 0)}</td>
                            <td className="py-2 text-right text-red-600">
                              {formatCurrency((row.overdue_61_90 || 0) + (row.overdue_90_plus || 0))}
                            </td>
                            <td className="py-2 text-right font-semibold text-slate-900 dark:text-white">{formatCurrency(row.total_outstanding || 0)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-sm text-slate-400 text-center py-8">No outstanding receivables</p>
                )}
              </div>
            </div>

            {/* Recent Invoices */}
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
              <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
                <h3 className="font-semibold text-slate-900 dark:text-white">Recent Invoices</h3>
                <button
                  id="view-all-invoices-btn"
                  onClick={() => setActiveTab("invoices")}
                  className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
                >
                  View All <ArrowUpRight className="w-3 h-3" />
                </button>
              </div>
              <InvoiceTable
                invoices={(invoicesData?.items || []).slice(0, 5)}
                loading={invLoading}
                onSend={(id) => sendMutation.mutate(id)}
                onPayment={setPaymentModalInvoice}
              />
            </div>
          </div>
        )}

        {/* ── Invoices Tab ─────────────────────────────────────────────── */}
        {activeTab === "invoices" && (
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
            {/* Filters */}
            <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex flex-wrap gap-3 items-center">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  id="invoice-search"
                  placeholder="Search invoices..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
              <select
                id="status-filter"
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setInvPage(1) }}
                className="px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="">All Status</option>
                {["DRAFT", "SENT", "PARTIAL", "PAID", "OVERDUE", "CANCELLED", "VOID"].map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <InvoiceTable
              invoices={filteredInvoices}
              loading={invLoading}
              onSend={(id) => sendMutation.mutate(id)}
              onPayment={setPaymentModalInvoice}
            />

            {/* Pagination */}
            {invoicesData && invoicesData.pages > 1 && (
              <div className="px-6 py-4 border-t border-slate-100 dark:border-slate-700 flex items-center justify-between">
                <p className="text-sm text-slate-500">
                  Page {invoicesData.page} of {invoicesData.pages} ({invoicesData.total} total)
                </p>
                <div className="flex gap-2">
                  <button
                    id="prev-page-btn"
                    disabled={invPage <= 1}
                    onClick={() => setInvPage((p) => p - 1)}
                    className="px-3 py-1.5 border border-slate-200 dark:border-slate-600 rounded-lg text-sm disabled:opacity-50 hover:bg-slate-50 dark:hover:bg-slate-700"
                  >
                    Previous
                  </button>
                  <button
                    id="next-page-btn"
                    disabled={invPage >= (invoicesData.pages || 1)}
                    onClick={() => setInvPage((p) => p + 1)}
                    className="px-3 py-1.5 border border-slate-200 dark:border-slate-600 rounded-lg text-sm disabled:opacity-50 hover:bg-slate-50 dark:hover:bg-slate-700"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Supplier Invoices Tab ────────────────────────────────────── */}
        {activeTab === "supplier" && (
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
            <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
              <h3 className="font-semibold text-slate-900 dark:text-white">Supplier Invoices (AP)</h3>
              <button
                id="new-supplier-invoice-btn"
                onClick={() => navigate("/finance/supplier-invoices/new")}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-xl text-sm font-medium shadow-sm hover:from-emerald-700 hover:to-teal-700 transition-all"
              >
                <Plus className="w-4 h-4" />
                New Supplier Invoice
              </button>
            </div>
            <SupplierInvoiceTable
              invoices={siData?.items || []}
              loading={!siData}
            />
            {siData && siData.pages > 1 && (
              <div className="px-6 py-4 border-t border-slate-100 dark:border-slate-700 flex justify-between items-center">
                <p className="text-sm text-slate-500">
                  Page {siData.page} of {siData.pages}
                </p>
                <div className="flex gap-2">
                  <button disabled={siPage <= 1} onClick={() => setSiPage(p => p - 1)}
                    className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50">Previous</button>
                  <button disabled={siPage >= siData.pages} onClick={() => setSiPage(p => p + 1)}
                    className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50">Next</button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Ledger Tab ───────────────────────────────────────────────── */}
        {activeTab === "ledger" && <LedgerTab />}
      </div>

      {/* Payment Modal */}
      {paymentModalInvoice && (
        <PaymentModal
          invoice={paymentModalInvoice}
          onClose={() => setPaymentModalInvoice(null)}
          onSuccess={() => {
            qc.invalidateQueries({ queryKey: ["invoices"] })
            qc.invalidateQueries({ queryKey: ["finance-dashboard"] })
            qc.invalidateQueries({ queryKey: ["invoice", paymentModalInvoice.id] })
          }}
        />
      )}
    </div>
  )
}

// ── Invoice Table ────────────────────────────────────────────────────────
function InvoiceTable({
  invoices,
  loading,
  onSend,
  onPayment,
}: {
  invoices: Invoice[]
  loading: boolean
  onSend: (id: string) => void
  onPayment: (inv: Invoice) => void
}) {
  if (loading) {
    return (
      <div className="p-6 space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-12 bg-slate-100 dark:bg-slate-700 rounded-lg animate-pulse" />
        ))}
      </div>
    )
  }
  if (!invoices.length) {
    return (
      <div className="py-16 text-center">
        <FileText className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
        <p className="text-slate-500 dark:text-slate-400">No invoices found</p>
      </div>
    )
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-xs text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-700">
            {["Invoice #", "Client", "Date", "Due Date", "Amount", "Paid", "Balance", "Status", "Actions"].map((h) => (
              <th key={h} className="px-6 py-3 text-left font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50 dark:divide-slate-700">
          {invoices.map((inv) => (
            <tr key={inv.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
              <td className="px-6 py-4">
                <Link
                  to={`/finance/invoices/${inv.id}`}
                  className="font-medium text-blue-600 hover:text-blue-700 text-sm"
                >
                  {inv.invoice_number}
                </Link>
              </td>
              <td className="px-6 py-4 text-sm text-slate-700 dark:text-slate-300">{inv.client_name}</td>
              <td className="px-6 py-4 text-sm text-slate-500">{inv.invoice_date}</td>
              <td className="px-6 py-4 text-sm text-slate-500">{inv.due_date}</td>
              <td className="px-6 py-4 text-sm font-medium text-slate-900 dark:text-white">{formatCurrency(inv.grand_total)}</td>
              <td className="px-6 py-4 text-sm text-emerald-600 font-medium">{formatCurrency(inv.paid_amount)}</td>
              <td className="px-6 py-4 text-sm font-semibold text-slate-900 dark:text-white">{formatCurrency(inv.balance_due)}</td>
              <td className="px-6 py-4"><StatusBadge status={inv.status} /></td>
              <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                  <Link to={`/finance/invoices/${inv.id}`}>
                    <button id={`view-inv-${inv.id}`} className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors">
                      <Eye className="w-4 h-4" />
                    </button>
                  </Link>
                  {inv.status === "DRAFT" && (
                    <button
                      id={`send-inv-${inv.id}`}
                      onClick={() => onSend(inv.id)}
                      className="px-2.5 py-1 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                    >
                      Send
                    </button>
                  )}
                  {["SENT", "PARTIAL", "OVERDUE"].includes(inv.status) && inv.balance_due > 0 && (
                    <button
                      id={`pay-inv-${inv.id}`}
                      onClick={() => onPayment(inv)}
                      className="px-2.5 py-1 text-xs font-medium text-emerald-600 border border-emerald-200 rounded-lg hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors"
                    >
                      Pay
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Supplier Invoice Table ───────────────────────────────────────────────
function SupplierInvoiceTable({
  invoices,
  loading,
}: {
  invoices: SupplierInvoice[]
  loading: boolean
}) {
  if (loading) {
    return (
      <div className="p-6 space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-12 bg-slate-100 dark:bg-slate-700 rounded-lg animate-pulse" />
        ))}
      </div>
    )
  }
  if (!invoices.length) {
    return (
      <div className="py-16 text-center">
        <Building2 className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
        <p className="text-slate-500 dark:text-slate-400">No supplier invoices found</p>
      </div>
    )
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-xs text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-700">
            {["Invoice #", "Supplier", "Ref", "Invoice Date", "Due Date", "Total", "Paid", "Balance", "Status"].map((h) => (
              <th key={h} className="px-6 py-3 text-left font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50 dark:divide-slate-700">
          {invoices.map((si) => (
            <tr key={si.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
              <td className="px-6 py-4 text-sm font-medium text-slate-700 dark:text-slate-300">{si.invoice_number}</td>
              <td className="px-6 py-4 text-sm text-slate-700 dark:text-slate-300">{si.supplier_name}</td>
              <td className="px-6 py-4 text-sm text-slate-400">{si.supplier_invoice_ref || "—"}</td>
              <td className="px-6 py-4 text-sm text-slate-500">{si.invoice_date}</td>
              <td className="px-6 py-4 text-sm text-slate-500">{si.due_date}</td>
              <td className="px-6 py-4 text-sm font-medium text-slate-900 dark:text-white">{formatCurrency(si.grand_total)}</td>
              <td className="px-6 py-4 text-sm text-emerald-600 font-medium">{formatCurrency(si.paid_amount)}</td>
              <td className="px-6 py-4 text-sm font-semibold text-slate-900 dark:text-white">{formatCurrency(si.balance_due)}</td>
              <td className="px-6 py-4"><StatusBadge status={si.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Ledger Tab ───────────────────────────────────────────────────────────
function LedgerTab() {
  const [page, setPage] = useState(1)
  const [refType, setRefType] = useState("")

  const { data, isLoading } = useQuery({
    queryKey: ["ledger", refType, page],
    queryFn: () => financeService.getLedger({ reference_type: refType || undefined, page, page_size: 25 }),
  })

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
      <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center gap-4">
        <h3 className="font-semibold text-slate-900 dark:text-white flex-1">Financial Ledger</h3>
        <select
          id="ledger-ref-filter"
          value={refType}
          onChange={(e) => { setRefType(e.target.value); setPage(1) }}
          className="px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
        >
          <option value="">All Types</option>
          {["invoice", "payment", "supplier_invoice", "supplier_payment"].map((t) => (
            <option key={t} value={t}>{t.replace("_", " ").toUpperCase()}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="p-6 space-y-3">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-10 bg-slate-100 dark:bg-slate-700 rounded animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-slate-500 border-b border-slate-100 dark:border-slate-700">
                {["Reference", "Type", "Account", "Debit", "Credit", "Description", "Date"].map((h) => (
                  <th key={h} className="px-6 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 dark:divide-slate-700">
              {(data?.items || []).map((entry) => (
                <tr key={entry.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
                  <td className="px-6 py-3 font-mono text-xs text-slate-500">{entry.reference_id.slice(0, 8)}…</td>
                  <td className="px-6 py-3">
                    <span className="text-xs font-medium px-2 py-0.5 bg-slate-100 dark:bg-slate-700 rounded-full text-slate-600 dark:text-slate-400">
                      {entry.reference_type}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-slate-600 dark:text-slate-400">{entry.account_type}</td>
                  <td className="px-6 py-3 text-emerald-600 font-medium">{entry.debit > 0 ? formatCurrency(entry.debit) : "—"}</td>
                  <td className="px-6 py-3 text-red-600 font-medium">{entry.credit > 0 ? formatCurrency(entry.credit) : "—"}</td>
                  <td className="px-6 py-3 text-slate-500 max-w-xs truncate">{entry.description}</td>
                  <td className="px-6 py-3 text-slate-400 text-xs">{entry.created_at.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!data?.items?.length && (
            <div className="py-16 text-center">
              <CreditCard className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
              <p className="text-slate-500 dark:text-slate-400">No ledger entries yet</p>
            </div>
          )}
        </div>
      )}

      {data && data.pages > 1 && (
        <div className="px-6 py-4 border-t border-slate-100 dark:border-slate-700 flex justify-between items-center">
          <p className="text-sm text-slate-500">Page {data.page} of {data.pages} ({data.total} entries)</p>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50">Previous</button>
            <button disabled={page >= data.pages} onClick={() => setPage(p => p + 1)} className="px-3 py-1.5 border rounded-lg text-sm disabled:opacity-50">Next</button>
          </div>
        </div>
      )}
    </div>
  )
}
