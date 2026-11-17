import { BOMCostAnalysisReport } from "@/modules/reports/pages/BOMCostAnalysisReport"
import { usePermissions } from "@/hooks/usePermissions"
import { Input } from "@/components/ui/input"
import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useSearchParams } from "react-router-dom"
import { financeService } from "@/services/finance.service"
import {
  BarChart3, Package, Factory, ShoppingCart, Truck, ClipboardCheck,
  IndianRupee, RefreshCw, AlertTriangle,
} from "lucide-react"

interface ReportSection {
  id: string
  label: string
  icon: React.ElementType
  color: string
  endpoints: { key: string; label: string; fn: () => Promise<any> }[]
}

const REPORT_SECTIONS: ReportSection[] = [
  {
    id: "inventory",
    label: "Inventory",
    icon: Package,
    color: "from-blue-500 to-blue-600",
    endpoints: [
      { key: "inventory-summary", label: "Stock Summary", fn: financeService.getInventorySummary },
      { key: "inventory-turnover", label: "Inventory Turnover", fn: financeService.getInventoryTurnover },
    ],
  },
  {
    id: "production",
    label: "Production",
    icon: Factory,
    color: "from-purple-500 to-purple-600",
    endpoints: [
      { key: "production-summary", label: "Work Order Summary", fn: financeService.getProductionSummary },
      { key: "production-efficiency", label: "Scrap & Efficiency", fn: financeService.getProductionEfficiency },
    ],
  },
  {
    id: "sales",
    label: "Sales",
    icon: ShoppingCart,
    color: "from-emerald-500 to-emerald-600",
    endpoints: [
      { key: "sales-summary", label: "Sales Summary", fn: financeService.getSalesSummary },
      { key: "top-clients", label: "Top Clients", fn: () => financeService.getTopClients(10) },
    ],
  },
  {
    id: "procurement",
    label: "Procurement",
    icon: Truck,
    color: "from-amber-500 to-amber-600",
    endpoints: [
      { key: "procurement-summary", label: "PO Summary", fn: financeService.getProcurementSummary },
    ],
  },
  {
    id: "quality",
    label: "Quality",
    icon: ClipboardCheck,
    color: "from-cyan-500 to-cyan-600",
    endpoints: [
      { key: "quality-summary", label: "Inspection Results", fn: financeService.getQualitySummary },
    ],
  },
  {
    id: "finance",
    label: "Finance",
    icon: IndianRupee,
    color: "from-rose-500 to-rose-600",
    endpoints: [
      { key: "finance-summary", label: "AR/AP Summary", fn: financeService.getFinanceSummary },
      { key: "finance-ap-aging", label: "AP Aging", fn: financeService.getFinanceAPAging },
      { key: "finance-trial-balance", label: "Trial Balance", fn: financeService.getFinanceTrialBalance },
      { key: "finance-profit-loss", label: "Profit & Loss", fn: financeService.getFinanceProfitLoss },
      { key: "finance-balance-sheet", label: "Balance Sheet", fn: financeService.getFinanceBalanceSheet },
      { key: "finance-cash-flow", label: "Cash Flow", fn: financeService.getFinanceCashFlow },
    ],
  },
]

function formatVal(val: any): string {
  if (val === null || val === undefined) return "—"
  if (typeof val === "number") {
    return new Intl.NumberFormat(undefined, { maximumFractionDigits: 12 }).format(val)
  }
  if (typeof val === "boolean") return val ? "Yes" : "No"
  if (typeof val === "string") return val
  return JSON.stringify(val)
}

function DataTable({ data }: { data: any }) {
  if (!data) return null

  // Handle array of objects
  if (Array.isArray(data) && data.length > 0 && typeof data[0] === "object") {
    const headers = Object.keys(data[0])
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-700">
              {headers.map((h) => (
                <th key={h} className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                  {h.replace(/_/g, " ")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50 dark:divide-slate-700">
            {data.map((row: any, i: number) => (
              <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-700/30">
                {headers.map((h) => {
                  const v = row[h]
                  const isNum = typeof v === "number"
                  const isNeg = isNum && v < 0
                  const isLowStock = h === "is_low_stock" && v

                  return (
                    <td
                      key={h}
                      className={`px-4 py-3 ${
                        isLowStock ? "text-red-600 font-medium" :
                        isNum ? (isNeg ? "text-red-600" : "text-slate-900 dark:text-white font-medium") :
                        "text-slate-600 dark:text-slate-300"
                      }`}
                    >
                      {isLowStock ? "⚠️ LOW" : formatVal(v)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
        {data.length === 0 && (
          <p className="text-center py-8 text-slate-400 text-sm">No data available</p>
        )}
      </div>
    )
  }

  // Handle object (nested)
  if (typeof data === "object" && !Array.isArray(data)) {
    return (
      <div className="space-y-4">
        {Object.entries(data).map(([key, val]) => (
          <div key={key}>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
              {key.replace(/_/g, " ")}
            </h4>
            <DataTable data={val} />
          </div>
        ))}
      </div>
    )
  }

  if (Array.isArray(data) && data.length === 0) {
    return <p className="text-center py-8 text-slate-400 text-sm">No data available</p>
  }

  return <pre className="text-xs text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-700 p-3 rounded-lg overflow-auto">{JSON.stringify(data, null, 2)}</pre>
}

function ReportCard({ section }: { section: ReportSection }) {
  const [activeEndpoint, setActiveEndpoint] = useState(section.endpoints[0].key)
  const endpoint = section.endpoints.find((e) => e.key === activeEndpoint)!

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["report", activeEndpoint],
    queryFn: endpoint.fn,
    retry: 1,
  })

  const Icon = section.icon

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
      {/* Card header */}
      <div className={`bg-gradient-to-r ${section.color} p-4 rounded-t-2xl flex items-center justify-between`}>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-white/20 rounded-lg">
            <Icon className="w-4 h-4 text-white" />
          </div>
          <h3 className="font-semibold text-white">{section.label} Report</h3>
        </div>
        <button
          id={`refresh-${section.id}`}
          onClick={() => refetch()}
          className="p-1.5 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-white ${isLoading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Sub-report tabs */}
      {section.endpoints.length > 1 && (
        <div className="flex gap-1 p-3 bg-slate-50 dark:bg-slate-700/50 border-b border-slate-100 dark:border-slate-700">
          {section.endpoints.map((ep) => (
            <button
              key={ep.key}
              id={`report-tab-${ep.key}`}
              onClick={() => setActiveEndpoint(ep.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeEndpoint === ep.key
                  ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm"
                  : "text-slate-500 dark:text-slate-400 hover:text-slate-700"
              }`}
            >
              {ep.label}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      <div className="p-4">
        {isLoading ? (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-8 bg-slate-100 dark:bg-slate-700 rounded animate-pulse" />
            ))}
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 text-amber-600 bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 text-sm">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>Report unavailable. Check access or retry later.</span>
          </div>
        ) : (
          <DataTable data={data} />
        )}
      </div>
    </div>
  )
}

export default function ReportsPage() {
  const [searchParams] = useSearchParams()
  const { hasPermission } = usePermissions()
  const permissions: Record<string, string> = {
    inventory: "inventory:read", production: "manufacturing:read", sales: "sales:read",
    procurement: "procurement:read", quality: "quality:read", finance: "report.view_financial",
  }
  const [search, setSearch] = useState("")
  const [showCost, setShowCost] = useState(searchParams.get("module") == null)
  const matches = (label: string) => label.toLowerCase().includes(search.trim().toLowerCase())
  const sections = REPORT_SECTIONS.filter(section => hasPermission(permissions[section.id]) &&
    (matches(section.label) || section.endpoints.some(endpoint => matches(endpoint.label))))
  const showBom = hasPermission("manufacturing:read") && matches("Manufacturing BOM Cost Analysis")
  const defaultModules = useMemo(() => {
    const requestedModule = searchParams.get("module")
    const sectionIds = new Set(REPORT_SECTIONS.map((section) => section.id))

    if (requestedModule && sectionIds.has(requestedModule)) {
      return new Set([requestedModule])
    }

    return new Set(["finance", "sales", "inventory", "production", "procurement"])
  }, [searchParams])
  const [selectedModules, setSelectedModules] = useState<Set<string>>(defaultModules)

  const toggleModule = (id: string) => {
    setSelectedModules((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header */}
      <div className="bg-white dark:bg-slate-800 border-b border-slate-100 dark:border-slate-700 px-4 py-6 md:px-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <div className="p-2 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl">
                <BarChart3 className="w-5 h-5 text-white" />
              </div>
              Reports & Analytics
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Explore manufacturing, inventory, procurement, sales and finance reports.
            </p>
          </div>
        </div>

        <Input aria-label="Search reports" placeholder="Search reports" className="mt-4 max-w-sm" value={search} onChange={event => setSearch(event.target.value)} />
        {/* Module filter toggles */}
        <div className="flex flex-wrap gap-2 mt-5">
          {showBom && <button type="button" aria-pressed={showCost} className="rounded-full border px-3 py-1.5 text-xs font-semibold aria-pressed:bg-primary aria-pressed:text-primary-foreground" onClick={() => setShowCost(!showCost)}>BOM Cost Analysis</button>}
          {sections.map((s) => {
            const Icon = s.icon
            const active = selectedModules.has(s.id)
            return (
              <button
                key={s.id}
                id={`toggle-${s.id}`}
                onClick={() => toggleModule(s.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                  active
                    ? `bg-gradient-to-r ${s.color} text-white border-transparent shadow-sm`
                    : "border-slate-200 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:border-slate-300"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {s.label}
              </button>
            )
          })}
        </div>
      </div>

      {showBom && showCost && <div className="border-b bg-background p-4 md:p-8"><BOMCostAnalysisReport /></div>}
      {!showBom && sections.length === 0 && <p className="p-8 text-muted-foreground">No reports match your search.</p>}
      {/* Report Cards */}
      <div className="px-4 py-6 md:px-8 grid grid-cols-1 xl:grid-cols-2 gap-6">
        {sections.filter((s) => selectedModules.has(s.id)).map((section) => (
          <ReportCard key={section.id} section={section} />
        ))}
        {selectedModules.size === 0 && !(showBom && showCost) && (
          <div className="col-span-2 text-center py-16">
            <BarChart3 className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
            <p className="text-slate-500 dark:text-slate-400">Select modules above to view reports</p>
          </div>
        )}
      </div>
    </div>
  )
}
