import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { mrpApi, MRPSuggestion, MRPRunResult, CreatedPO, MaterialRequest } from "../../../services/mrp.service"

// ── Exception helpers ─────────────────────────────────────────────────────── #
type ExceptionType = "overdue" | "no_supplier" | "lead_time_risk"

function getExceptions(s: MRPSuggestion): ExceptionType[] {
  const flags: ExceptionType[] = []
  const today = new Date().toISOString().slice(0, 10)
  if (s.need_by_date < today) flags.push("overdue")
  if (!s.supplier_id || s.supplier_name === "No Supplier") flags.push("no_supplier")
  const daysUntilNeed = Math.ceil(
    (new Date(s.need_by_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  )
  if (daysUntilNeed >= 0 && daysUntilNeed <= s.lead_time_days && !flags.includes("overdue")) {
    flags.push("lead_time_risk")
  }
  return flags
}

const exceptionMeta: Record<ExceptionType, { label: string; color: string; bg: string; title: string }> = {
  overdue:        { label: "Overdue",      color: "#ef4444", bg: "rgba(239,68,68,0.15)",    title: "Need-by date has passed" },
  no_supplier:    { label: "No Supplier",  color: "#f59e0b", bg: "rgba(245,158,11,0.15)",   title: "No supplier assigned — Convert to PO will use unknown supplier" },
  lead_time_risk: { label: "Lead Risk",    color: "#f97316", bg: "rgba(249,115,22,0.15)",   title: "Less time remaining than lead time — order urgently" },
}

function ExceptionBadge({ type }: { type: ExceptionType }) {
  const m = exceptionMeta[type]
  return (
    <span
      title={m.title}
      style={{
        padding: "2px 7px",
        borderRadius: 20,
        fontSize: 10,
        fontWeight: 700,
        color: m.color,
        background: m.bg,
        textTransform: "uppercase",
        letterSpacing: "0.04em",
        whiteSpace: "nowrap",
        cursor: "help",
      }}
    >
      {m.label}
    </span>
  )
}

// ── Status helpers ────────────────────────────────────────────────────────── #
const statusMeta: Record<string, { label: string; color: string; bg: string }> = {
  pending:   { label: "Pending",   color: "#94a3b8", bg: "rgba(148,163,184,0.1)"  },
  approved:  { label: "Approved",  color: "#22c55e", bg: "rgba(34,197,94,0.1)"    },
  rejected:  { label: "Rejected",  color: "#ef4444", bg: "rgba(239,68,68,0.1)"    },
  converted: { label: "Converted", color: "#818cf8", bg: "rgba(129,140,248,0.1)"  },
}

function StatusBadge({ s }: { s: string }) {
  const m = statusMeta[s] ?? statusMeta.pending
  return (
    <span
      style={{
        padding: "3px 10px",
        borderRadius: 20,
        fontSize: 11,
        fontWeight: 700,
        color: m.color,
        background: m.bg,
        textTransform: "uppercase",
        letterSpacing: "0.05em",
        whiteSpace: "nowrap",
      }}
    >
      {m.label}
    </span>
  )
}

function NetReqBar({ net, gross }: { net: number; gross: number }) {
  const pct = gross > 0 ? Math.min((net / gross) * 100, 100) : 0
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div
        style={{
          flex: 1,
          height: 6,
          background: "rgba(255,255,255,0.07)",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: pct > 80 ? "#ef4444" : pct > 50 ? "#f59e0b" : "#6366f1",
            borderRadius: 3,
            transition: "width 0.5s",
          }}
        />
      </div>
      <span style={{ fontSize: 11, color: "#6b7280", minWidth: 36 }}>{pct.toFixed(0)}%</span>
    </div>
  )
}

// ── Toast ──────────────────────────────────────────────────────────────────── #
function Toast({ msg, type, onClose }: { msg: string; type: "success" | "error"; onClose: () => void }) {
  useEffect(() => {
    const t = setTimeout(onClose, 4000)
    return () => clearTimeout(t)
  }, [onClose])
  return (
    <div
      style={{
        position: "fixed",
        bottom: 28,
        right: 28,
        zIndex: 9999,
        background: type === "success" ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
        border: `1px solid ${type === "success" ? "#22c55e44" : "#ef444444"}`,
        borderRadius: 12,
        padding: "14px 20px",
        color: type === "success" ? "#22c55e" : "#fca5a5",
        fontWeight: 600,
        fontSize: 14,
        boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
        animation: "mrp-toast-in 0.3s ease",
        maxWidth: 340,
      }}
    >
      {type === "success" ? "✓ " : "✕ "}{msg}
    </div>
  )
}

// ── Suggestion row ─────────────────────────────────────────────────────────── #
function SuggestionRow({
  s,
  selected,
  onSelect,
  onApprove,
  onReject,
}: {
  s: MRPSuggestion
  selected: boolean
  onSelect: (id: string) => void
  onApprove: (id: string) => void
  onReject: (id: string) => void
}) {
  const isActionable = s.status === "pending"
  const exceptions = s.status === "pending" ? getExceptions(s) : []
  return (
    <tr
      style={{
        borderBottom: "1px solid rgba(255,255,255,0.05)",
        background: selected
          ? "rgba(99,102,241,0.08)"
          : exceptions.includes("overdue")
          ? "rgba(239,68,68,0.04)"
          : "transparent",
        transition: "background 0.15s",
      }}
    >
      <td className="mrp-td">
        <input
          type="checkbox"
          checked={selected}
          disabled={!isActionable}
          onChange={() => onSelect(s.id)}
          style={{ accentColor: "#6366f1", cursor: isActionable ? "pointer" : "not-allowed" }}
        />
      </td>
      <td className="mrp-td">
        <div style={{ fontWeight: 600, color: "#e5e7eb", fontFamily: "monospace", fontSize: 12 }}>
          {s.material_code}
        </div>
        <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>{s.material_name}</div>
        {exceptions.length > 0 && (
          <div style={{ display: "flex", gap: 4, marginTop: 4, flexWrap: "wrap" }}>
            {exceptions.map((ex) => <ExceptionBadge key={ex} type={ex} />)}
          </div>
        )}
      </td>
      <td className="mrp-td mrp-num">{s.gross_requirement.toFixed(2)}</td>
      <td className="mrp-td mrp-num">{s.current_stock.toFixed(2)}</td>
      <td className="mrp-td mrp-num" style={{ color: "#38bdf8" }}>{s.open_po_qty.toFixed(2)}</td>
      <td className="mrp-td mrp-num" style={{ color: "#ef4444" }}>{s.reserved_stock.toFixed(2)}</td>
      <td className="mrp-td">
        <div style={{ fontWeight: 700, color: "#818cf8", fontSize: 13 }}>
          {s.net_requirement.toFixed(2)}
        </div>
        <NetReqBar net={s.net_requirement} gross={s.gross_requirement} />
      </td>
      <td className="mrp-td mrp-num" style={{ color: "#22c55e", fontWeight: 700 }}>
        {s.suggested_qty.toFixed(2)}
      </td>
      <td className="mrp-td">
        <div style={{ fontSize: 12, color: exceptions.includes("overdue") ? "#ef4444" : undefined }}>
          {s.need_by_date}
        </div>
        <div style={{ fontSize: 10, color: "#6b7280" }}>Lead: {s.lead_time_days}d</div>
      </td>
      <td className="mrp-td">
        <div style={{ fontSize: 12 }}>{s.supplier_name}</div>
        {exceptions.includes("no_supplier") && (
          <div style={{ fontSize: 10, color: "#f59e0b" }}>⚠ Assign supplier</div>
        )}
      </td>
      <td className="mrp-td">
        <StatusBadge s={s.status} />
      </td>
      <td className="mrp-td">
        {s.status === "converted" && s.po_id ? (
          <span style={{ fontSize: 11, color: "#818cf8" }}>→ PO created</span>
        ) : isActionable ? (
          <div style={{ display: "flex", gap: 6 }}>
            <button
              className="mrp-action-btn mrp-action-btn--approve"
              onClick={() => onApprove(s.id)}
            >
              ✓
            </button>
            <button
              className="mrp-action-btn mrp-action-btn--reject"
              onClick={() => onReject(s.id)}
            >
              ✕
            </button>
          </div>
        ) : null}
      </td>
    </tr>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────── #
export default function MRPDashboard() {
  const [suggestions, setSuggestions] = useState<MRPSuggestion[]>([])
  const [materialRequests, setMaterialRequests] = useState<MaterialRequest[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [runResult, setRunResult] = useState<MRPRunResult | null>(null)
  const [createdPOs, setCreatedPOs] = useState<CreatedPO[]>([])
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [activeTab, setActiveTab] = useState<"suggestions" | "requisitions">("suggestions")
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null)

  const showToast = (msg: string, type: "success" | "error" = "success") =>
    setToast({ msg, type })

  const fetchSuggestions = useCallback(async () => {
    setLoading(true)
    try {
      const data = await mrpApi.getSuggestions()
      setSuggestions(data)
    } catch {
      showToast("Failed to load suggestions", "error")
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchMaterialRequests = useCallback(async () => {
    try {
      const data = await mrpApi.getMaterialRequests()
      setMaterialRequests(data)
    } catch {
      // non-critical — don't surface error toast
    }
  }, [])

  useEffect(() => {
    fetchSuggestions()
    fetchMaterialRequests()
  }, [fetchSuggestions, fetchMaterialRequests])

  // ── Filtering ──────────────────────────────────────────────────────────
  const filtered =
    statusFilter === "all"
      ? suggestions
      : suggestions.filter((s) => s.status === statusFilter)

  // ── Exception summary counts ───────────────────────────────────────────
  const exceptionCounts = {
    overdue: suggestions.filter((s) => s.status === "pending" && getExceptions(s).includes("overdue")).length,
    no_supplier: suggestions.filter((s) => s.status === "pending" && getExceptions(s).includes("no_supplier")).length,
    lead_time_risk: suggestions.filter((s) => s.status === "pending" && getExceptions(s).includes("lead_time_risk")).length,
  }
  const totalExceptions = exceptionCounts.overdue + exceptionCounts.no_supplier + exceptionCounts.lead_time_risk

  // ── Selection ──────────────────────────────────────────────────────────
  const pendingIds = filtered.filter((s) => s.status === "pending").map((s) => s.id)
  const allSelected = pendingIds.length > 0 && pendingIds.every((id) => selected.has(id))

  const toggleAll = () => {
    if (allSelected) setSelected(new Set())
    else setSelected(new Set(pendingIds))
  }

  const toggleOne = (id: string) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelected(next)
  }

  // ── Actions ────────────────────────────────────────────────────────────
  const handleRun = async () => {
    setLoading(true)
    try {
      const r = await mrpApi.runMRP()
      setRunResult(r)
      await fetchSuggestions()
      await fetchMaterialRequests()
      showToast(`MRP run complete — ${r.suggestions_count} suggestions generated`)
    } catch {
      showToast("MRP run failed", "error")
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async (id: string) => {
    await mrpApi.approveSuggestion(id)
    await fetchSuggestions()
    showToast("Suggestion approved")
  }

  const handleReject = async (id: string) => {
    await mrpApi.rejectSuggestion(id)
    await fetchSuggestions()
    showToast("Suggestion rejected")
  }

  const handleBulkApprove = async () => {
    if (!selected.size) return
    const ids = Array.from(selected)
    const r = await mrpApi.bulkApprove(ids)
    await fetchSuggestions()
    setSelected(new Set())
    showToast(`${r.approved} suggestion(s) approved`)
  }

  const handleConvert = async (ids?: string[]) => {
    setLoading(true)
    try {
      const r = await mrpApi.convertToPO(ids)
      setCreatedPOs(r.purchase_orders)
      await fetchSuggestions()
      showToast(`${r.purchase_orders.length} PO(s) created`)
    } catch {
      showToast("Failed to convert to POs", "error")
    } finally {
      setLoading(false)
    }
  }

  // ── KPIs ───────────────────────────────────────────────────────────────
  const kpis = {
    total: suggestions.length,
    pending: suggestions.filter((s) => s.status === "pending").length,
    approved: suggestions.filter((s) => s.status === "approved").length,
    rejected: suggestions.filter((s) => s.status === "rejected").length,
    converted: suggestions.filter((s) => s.status === "converted").length,
    totalNet: suggestions.reduce((a, b) => a + b.net_requirement, 0),
  }

  return (
    <div className="mrp-page">
      <style>{CSS}</style>

      {/* ── Header ── */}
      <div className="mrp-header">
        <div>
          <nav className="mrp-breadcrumb">
            <span style={{ color: "#6b7280" }}>Capacity &amp; MRP</span>
            <span style={{ color: "#374151" }}>›</span>
            <span>MRP Dashboard</span>
          </nav>
          <h1 className="mrp-title">Material Requirements Planning</h1>
          <p className="mrp-subtitle">
            Generate purchase suggestions · Approve &amp; convert to POs
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "flex-start", flexWrap: "wrap" }}>
          <Link to="/mrp/capacity" className="mrp-btn mrp-btn--ghost">
            📊 Capacity Chart
          </Link>
          <button className="mrp-btn mrp-btn--run" onClick={handleRun} disabled={loading}>
            {loading ? "⟳ Processing…" : "▶ Run MRP"}
          </button>
        </div>
      </div>

      {/* ── Last run banner ── */}
      {runResult && (
        <div className="mrp-run-banner">
          <span>✓ MRP run completed at {new Date(runResult.run_at).toLocaleString()}</span>
          <span style={{ marginLeft: 12, fontWeight: 700, color: "#818cf8" }}>
            {runResult.suggestions_count} suggestions generated
          </span>
        </div>
      )}

      {/* ── Created POs banner ── */}
      {createdPOs.length > 0 && (
        <div className="mrp-pos-banner">
          {createdPOs.map((po) => (
            <Link
              key={po.po_id}
              to={`/procurement/purchase-orders/${po.po_id}`}
              className="mrp-po-chip"
            >
              {po.po_number} ({po.lines} lines)
            </Link>
          ))}
        </div>
      )}

      {/* ── KPI row ── */}
      <div className="mrp-kpi-row">
        {[
          { label: "Total Suggestions",   value: kpis.total,              color: "#e5e7eb"  },
          { label: "Pending",             value: kpis.pending,            color: "#94a3b8"  },
          { label: "Approved",            value: kpis.approved,           color: "#22c55e"  },
          { label: "Rejected",            value: kpis.rejected,           color: "#ef4444"  },
          { label: "Converted → PO",      value: kpis.converted,          color: "#818cf8"  },
          { label: "Total Net Req (units)",value: kpis.totalNet.toFixed(1), color: "#f59e0b" },
        ].map((k) => (
          <div key={k.label} className="mrp-kpi-card">
            <div className="mrp-kpi-value" style={{ color: k.color }}>{k.value}</div>
            <div className="mrp-kpi-label">{k.label}</div>
          </div>
        ))}
      </div>

      {/* ── Exception summary banner ── */}
      {totalExceptions > 0 && (
        <div
          style={{
            display: "flex",
            gap: 12,
            flexWrap: "wrap",
            alignItems: "center",
            background: "rgba(239,68,68,0.06)",
            border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: 10,
            padding: "10px 16px",
            marginBottom: 16,
            fontSize: 12,
          }}
        >
          <span style={{ color: "#fca5a5", fontWeight: 600 }}>⚠ {totalExceptions} exception{totalExceptions !== 1 ? "s" : ""} in pending suggestions:</span>
          {exceptionCounts.overdue > 0 && (
            <span style={{ color: "#ef4444" }}>🔴 {exceptionCounts.overdue} overdue</span>
          )}
          {exceptionCounts.no_supplier > 0 && (
            <span style={{ color: "#f59e0b" }}>⚠ {exceptionCounts.no_supplier} missing supplier</span>
          )}
          {exceptionCounts.lead_time_risk > 0 && (
            <span style={{ color: "#f97316" }}>⏱ {exceptionCounts.lead_time_risk} lead time risk</span>
          )}
        </div>
      )}

      {/* ── Tabs ── */}
      <div className="mrp-tabs">
        <button
          className={`mrp-tab${activeTab === "suggestions" ? " mrp-tab--active" : ""}`}
          onClick={() => setActiveTab("suggestions")}
        >
          📋 Suggestions ({kpis.total})
        </button>
        <button
          className={`mrp-tab${activeTab === "requisitions" ? " mrp-tab--active" : ""}`}
          onClick={() => setActiveTab("requisitions")}
        >
          📝 Material Requests ({materialRequests.length})
        </button>
      </div>

      {activeTab === "requisitions" ? (
        /* ── Requisitions panel ── */
        <div className="mrp-table-wrap">
          {materialRequests.length === 0 ? (
            <div className="mrp-empty">
              No open material requests. Requests are created automatically when a Work Order is released with a material shortage.
            </div>
          ) : (
            <table className="mrp-table">
              <thead>
                <tr>
                  <th className="mrp-th">Material</th>
                  <th className="mrp-th mrp-num">Required Qty</th>
                  <th className="mrp-th mrp-num">Fulfilled Qty</th>
                  <th className="mrp-th mrp-num">Shortage</th>
                  <th className="mrp-th">Required By</th>
                  <th className="mrp-th">Source WO</th>
                  <th className="mrp-th">Status</th>
                </tr>
              </thead>
              <tbody>
                {materialRequests.map((mr) => {
                  const isOverdue = mr.required_by && mr.required_by < new Date().toISOString().slice(0, 10)
                  return (
                    <tr
                      key={mr.id}
                      style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}
                    >
                      <td className="mrp-td">
                        <div style={{ fontWeight: 600, color: "#e5e7eb", fontFamily: "monospace", fontSize: 12 }}>
                          {mr.material_code}
                        </div>
                        <div style={{ fontSize: 11, color: "#6b7280" }}>{mr.material_name}</div>
                      </td>
                      <td className="mrp-td mrp-num">{mr.required_quantity.toFixed(2)}</td>
                      <td className="mrp-td mrp-num" style={{ color: "#22c55e" }}>{mr.fulfilled_quantity.toFixed(2)}</td>
                      <td className="mrp-td mrp-num" style={{ color: mr.shortage_quantity > 0 ? "#ef4444" : "#22c55e", fontWeight: 700 }}>
                        {mr.shortage_quantity.toFixed(2)}
                      </td>
                      <td className="mrp-td">
                        <span style={{ fontSize: 12, color: isOverdue ? "#ef4444" : undefined }}>
                          {mr.required_by ?? "—"}
                        </span>
                        {isOverdue && <span style={{ fontSize: 10, color: "#ef4444", marginLeft: 4 }}>Overdue</span>}
                      </td>
                      <td className="mrp-td">
                        {mr.source_ref_id ? (
                          <Link
                            to={`/work-orders/${mr.source_ref_id}`}
                            style={{ fontSize: 11, color: "#818cf8", textDecoration: "none" }}
                          >
                            View WO →
                          </Link>
                        ) : "—"}
                      </td>
                      <td className="mrp-td">
                        <span style={{
                          padding: "2px 8px", borderRadius: 20, fontSize: 10, fontWeight: 700,
                          textTransform: "uppercase",
                          color: mr.status === "open" ? "#f59e0b" : "#22c55e",
                          background: mr.status === "open" ? "rgba(245,158,11,0.1)" : "rgba(34,197,94,0.1)",
                        }}>
                          {mr.status}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      ) : (
        <>
      {/* ── Toolbar ── */}
      <div className="mrp-toolbar">
        {/* Status filter */}
        <div style={{ display: "flex", gap: 6 }}>
          {["all", "pending", "approved", "rejected", "converted"].map((f) => (
            <button
              key={f}
              className={`mrp-filter-btn${statusFilter === f ? " mrp-filter-btn--active" : ""}`}
              onClick={() => setStatusFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {/* Bulk actions */}
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {selected.size > 0 && (
            <span style={{ fontSize: 12, color: "#6b7280" }}>{selected.size} selected</span>
          )}
          <button
            className="mrp-btn mrp-btn--sm mrp-btn--approve"
            disabled={!kpis.pending}
            onClick={handleBulkApprove}
          >
            ✓ Bulk Approve {selected.size > 0 ? `(${selected.size})` : "Selected"}
          </button>
          <button
            className="mrp-btn mrp-btn--sm mrp-btn--convert"
            disabled={!kpis.approved}
            onClick={() => handleConvert()}
          >
            📦 Convert to PO ({kpis.approved})
          </button>
        </div>
      </div>

      {/* ── Table ── */}
      <div className="mrp-table-wrap">
        {loading && suggestions.length === 0 ? (
          <div className="mrp-empty">
            <div className="mrp-spinner" />
            Running MRP calculation…
          </div>
        ) : filtered.length === 0 ? (
          <div className="mrp-empty">
            {suggestions.length === 0
              ? "No suggestions yet. Click ▶ Run MRP to generate purchase suggestions."
              : "No suggestions match this filter."}
          </div>
        ) : (
          <table className="mrp-table">
            <thead>
              <tr>
                <th className="mrp-th">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    style={{ accentColor: "#6366f1" }}
                  />
                </th>
                <th className="mrp-th">Material</th>
                <th className="mrp-th mrp-num">Gross Req</th>
                <th className="mrp-th mrp-num">In Stock</th>
                <th className="mrp-th mrp-num">Open PO</th>
                <th className="mrp-th mrp-num">Reserved</th>
                <th className="mrp-th">Net Req</th>
                <th className="mrp-th mrp-num">Suggested Qty</th>
                <th className="mrp-th">Need By</th>
                <th className="mrp-th">Supplier</th>
                <th className="mrp-th">Status</th>
                <th className="mrp-th">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <SuggestionRow
                  key={s.id}
                  s={s}
                  selected={selected.has(s.id)}
                  onSelect={toggleOne}
                  onApprove={handleApprove}
                  onReject={handleReject}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Toast ── */}
      {toast && (
        <Toast msg={toast.msg} type={toast.type} onClose={() => setToast(null)} />
      )}
      </>
      )}
    </div>
  )
}

// ── Scoped CSS ────────────────────────────────────────────────────────────── #
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

@keyframes mrp-toast-in {
  from { transform: translateY(20px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
}
@keyframes mrp-spin {
  to { transform: rotate(360deg); }
}

.mrp-page {
  font-family: 'Inter', sans-serif;
  background: #080b14;
  min-height: 100vh;
  color: #e5e7eb;
  padding: 28px 32px;
  box-sizing: border-box;
}

.mrp-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
.mrp-breadcrumb {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 6px;
}
.mrp-title {
  font-size: 26px;
  font-weight: 800;
  background: linear-gradient(135deg, #818cf8, #34d399);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 4px;
}
.mrp-subtitle { font-size: 13px; color: #6b7280; margin: 0; }

.mrp-btn {
  padding: 9px 18px;
  border-radius: 8px;
  border: 1px solid transparent;
  font-weight: 600;
  cursor: pointer;
  font-size: 13px;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
  white-space: nowrap;
}
.mrp-btn--run {
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  border-color: #4f46e5;
  box-shadow: 0 4px 14px rgba(99,102,241,0.3);
}
.mrp-btn--run:hover:not(:disabled) { box-shadow: 0 6px 20px rgba(99,102,241,0.45); }
.mrp-btn--run:disabled { opacity: 0.6; cursor: not-allowed; }
.mrp-btn--ghost {
  background: rgba(255,255,255,0.04);
  border-color: rgba(255,255,255,0.1);
  color: #9ca3af;
}
.mrp-btn--ghost:hover { background: rgba(255,255,255,0.07); color: #e5e7eb; }
.mrp-btn--sm { padding: 7px 14px; font-size: 12px; }
.mrp-btn--approve {
  background: rgba(34,197,94,0.1);
  border-color: rgba(34,197,94,0.3);
  color: #22c55e;
}
.mrp-btn--approve:hover:not(:disabled) { background: rgba(34,197,94,0.18); }
.mrp-btn--approve:disabled { opacity: 0.4; cursor: not-allowed; }
.mrp-btn--convert {
  background: rgba(99,102,241,0.1);
  border-color: rgba(99,102,241,0.3);
  color: #818cf8;
}
.mrp-btn--convert:hover:not(:disabled) { background: rgba(99,102,241,0.18); }
.mrp-btn--convert:disabled { opacity: 0.4; cursor: not-allowed; }

.mrp-run-banner {
  background: rgba(34,197,94,0.07);
  border: 1px solid rgba(34,197,94,0.2);
  border-radius: 10px;
  padding: 12px 18px;
  font-size: 13px;
  color: #86efac;
  margin-bottom: 16px;
}
.mrp-pos-banner {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: rgba(99,102,241,0.08);
  border: 1px solid rgba(99,102,241,0.2);
  border-radius: 10px;
}
.mrp-po-chip {
  padding: 4px 12px;
  border-radius: 20px;
  background: rgba(99,102,241,0.15);
  border: 1px solid rgba(99,102,241,0.3);
  color: #818cf8;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  transition: background 0.15s;
}
.mrp-po-chip:hover { background: rgba(99,102,241,0.25); }

.mrp-kpi-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.mrp-kpi-card {
  background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 12px;
  padding: 16px 18px;
  text-align: center;
  transition: transform 0.2s;
}
.mrp-kpi-card:hover { transform: translateY(-2px); }
.mrp-kpi-value { font-size: 24px; font-weight: 800; margin-bottom: 4px; }
.mrp-kpi-label { font-size: 10px; color: #6b7280; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }

.mrp-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.mrp-filter-btn {
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.04);
  color: #9ca3af;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.mrp-filter-btn:hover { background: rgba(99,102,241,0.08); color: #818cf8; }
.mrp-filter-btn--active {
  background: rgba(99,102,241,0.15);
  border-color: #6366f1;
  color: #818cf8;
  font-weight: 600;
}

.mrp-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
}
.mrp-tab {
  padding: 9px 18px;
  border: none;
  background: transparent;
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
  margin-bottom: -1px;
}
.mrp-tab:hover { color: #9ca3af; }
.mrp-tab--active { color: #818cf8; border-bottom-color: #6366f1; font-weight: 600; }

.mrp-table-wrap {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  overflow: auto;
  min-height: 220px;
}
.mrp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.mrp-th {
  padding: 13px 14px;
  text-align: left;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #6b7280;
  font-weight: 600;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  white-space: nowrap;
  background: rgba(0,0,0,0.2);
  position: sticky;
  top: 0;
}
.mrp-td {
  padding: 12px 14px;
  vertical-align: middle;
}
.mrp-num { text-align: right; font-variant-numeric: tabular-nums; }

.mrp-action-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.mrp-action-btn--approve {
  background: rgba(34,197,94,0.1);
  border-color: rgba(34,197,94,0.3);
  color: #22c55e;
}
.mrp-action-btn--approve:hover { background: rgba(34,197,94,0.2); }
.mrp-action-btn--reject {
  background: rgba(239,68,68,0.1);
  border-color: rgba(239,68,68,0.3);
  color: #ef4444;
}
.mrp-action-btn--reject:hover { background: rgba(239,68,68,0.2); }

.mrp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 60px 20px;
  color: #6b7280;
  font-size: 14px;
  text-align: center;
}
.mrp-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(99,102,241,0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: mrp-spin 0.8s linear infinite;
}
`
