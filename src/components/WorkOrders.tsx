import React, { useState, useEffect } from "react";
import { Cpu, Plus, Play, CheckCircle2, ChevronRight, Ban, Warehouse, ListChecks, FileDigit } from "lucide-react";
import { WorkOrder, BOM, Material } from "../types";

interface WorkOrdersProps {
  token: string | null;
}

export default function WorkOrders({ token }: WorkOrdersProps) {
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [boms, setBoms] = useState<BOM[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWO, setSelectedWO] = useState<WorkOrder | null>(null);

  // Forms state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [selectedBOM, setSelectedBOM] = useState("");
  const [plannedQty, setPlannedQty] = useState("100");
  const [dueDate, setDueDate] = useState("");
  const [priority, setPriority] = useState<"low" | "medium" | "high">("medium");

  // Production recording state
  const [producedQty, setProducedQty] = useState("");
  const [scrapQty, setScrapQty] = useState("0");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const fetchData = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [resWo, resBom, resMat] = await Promise.all([
        fetch("/api/v1/work-orders", { headers }),
        fetch("/api/v1/boms", { headers }),
        fetch("/api/v1/inventory/materials", { headers })
      ]);

      if (resWo.ok) {
        const woList: WorkOrder[] = await resWo.json();
        setWorkOrders(woList);
        if (woList.length > 0 && !selectedWO) {
          setSelectedWO(woList[0]);
        } else if (selectedWO) {
          const updated = woList.find(w => w.id === selectedWO.id);
          if (updated) setSelectedWO(updated);
        }
      }
      if (resBom.ok) setBoms(await resBom.json());
      if (resMat.ok) setMaterials(await resMat.json());
    } catch (err) {
      console.error("Error loading Work Orders", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [token]);

  const handleCreateWO = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!selectedProduct || !selectedBOM) {
      setError("Please select both a product and a recipe BOM");
      return;
    }

    try {
      const res = await fetch("/api/v1/work-orders", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          productId: selectedProduct,
          bomId: selectedBOM,
          plannedQuantity: Number(plannedQty),
          dueDate,
          priority
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create work order");

      setSuccess(`Work Order ${data.workOrderNumber} scheduled!`);
      setShowCreateModal(false);
      setSelectedWO(data);
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRelease = async () => {
    if (!selectedWO) return;
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`/api/v1/work-orders/${selectedWO.id}/release`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to release work order");

      setSuccess(`Work Order ${selectedWO.workOrderNumber} released!`);
      setSelectedWO(data);
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleIssueMaterials = async () => {
    if (!selectedWO) return;
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`/api/v1/work-orders/${selectedWO.id}/materials/issue`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to issue materials");

      setSuccess("Raw materials successfully issued and deducted from inventory!");
      setSelectedWO(data);
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleStartJob = async (jcId: string) => {
    if (!selectedWO) return;
    try {
      const res = await fetch(`/api/v1/work-orders/${selectedWO.id}/job-cards/${jcId}/start`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        setSelectedWO(await res.json());
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCompleteJob = async (jcId: string) => {
    if (!selectedWO) return;
    try {
      const res = await fetch(`/api/v1/work-orders/${selectedWO.id}/job-cards/${jcId}/complete`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        setSelectedWO(await res.json());
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handlePostProduction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWO) return;
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`/api/v1/work-orders/${selectedWO.id}/production`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          producedQuantity: Number(producedQty),
          scrapQuantity: Number(scrapQty)
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to post production");

      setSuccess(`Production posted! Finished goods updated in inventory.`);
      setProducedQty("");
      setScrapQty("0");
      setSelectedWO(data);
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleCloseWO = async () => {
    if (!selectedWO) return;
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`/api/v1/work-orders/${selectedWO.id}/close`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to close work order");

      setSuccess(`Work Order ${selectedWO.workOrderNumber} archived as closed.`);
      setSelectedWO(data);
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      planned: "bg-blue-50 text-blue-700 border-blue-100",
      released: "bg-amber-50 text-amber-700 border-amber-100",
      in_progress: "bg-indigo-50 text-indigo-700 border-indigo-100 animate-pulse",
      completed: "bg-emerald-50 text-emerald-700 border-emerald-100",
      closed: "bg-gray-100 text-gray-600 border-gray-200"
    };
    return (
      <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-bold border uppercase tracking-wider ${styles[status] || ""}`}>
        {status.replace("_", " ")}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const activeBOMs = boms.filter(b => b.status === "active");
  const finishedProducts = materials.filter(m => m.type === "finished" || m.type === "semi-finished");

  return (
    <div className="flex-1 overflow-y-auto p-8 bg-gray-50 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Work Orders Hub</h1>
          <p className="text-gray-500 text-sm">Schedule runs, execute sequence job cards, and release finished stock</p>
        </div>
        <button
          onClick={() => { setShowCreateModal(true); setError(""); setSuccess(""); }}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-all shadow-lg hover:shadow-indigo-500/15"
        >
          <Plus className="w-4 h-4" />
          Schedule Work Order
        </button>
      </div>

      {/* Alert panels */}
      {error && (
        <div className="p-4 bg-red-100 border border-red-200 text-red-700 text-xs rounded-xl">
          <strong>Error: </strong>{error}
        </div>
      )}
      {success && (
        <div className="p-4 bg-emerald-100 border border-emerald-200 text-emerald-800 text-xs rounded-xl">
          <strong>Success: </strong>{success}
        </div>
      )}

      {/* Main Container */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Scheduled Runs Column */}
        <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="border-b border-gray-100 pb-3">
            <h3 className="font-bold text-gray-900">Scheduled runs</h3>
            <p className="text-xs text-gray-400">Production pipeline queue</p>
          </div>
          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
            {workOrders.map(wo => {
              const product = materials.find(m => m.id === wo.productId);
              const isSelected = selectedWO?.id === wo.id;
              return (
                <div
                  key={wo.id}
                  onClick={() => { setSelectedWO(wo); setError(""); setSuccess(""); }}
                  className={`p-4 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-2 ${
                    isSelected 
                      ? "border-indigo-600 bg-indigo-50/40 shadow-sm" 
                      : "border-gray-100 bg-gray-50/50 hover:bg-gray-100/50"
                  }`}
                >
                  <div className="overflow-hidden">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-gray-600">{wo.workOrderNumber}</span>
                      {getStatusBadge(wo.status)}
                    </div>
                    <h4 className="text-sm font-bold text-gray-900 mt-2 truncate">
                      {product?.name || "Unknown Product"}
                    </h4>
                    <p className="text-[11px] text-gray-400 mt-1">Planned Qty: {wo.plannedQuantity}</p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-300 shrink-0" />
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Work Order Operations Room */}
        <div className="lg:col-span-2 space-y-6">
          {selectedWO ? (
            <>
              {/* Header Details Card */}
              <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold text-gray-500">{selectedWO.workOrderNumber}</span>
                    {getStatusBadge(selectedWO.status)}
                    {selectedWO.priority === "high" && (
                      <span className="text-[9px] bg-red-100 text-red-800 font-bold px-1.5 py-0.5 rounded uppercase">Urgent</span>
                    )}
                  </div>
                  <h2 className="text-xl font-bold text-gray-900 mt-2">
                    {materials.find(m => m.id === selectedWO.productId)?.name || "Unknown Product"}
                  </h2>
                  <p className="text-xs text-gray-400 mt-1">
                    Due Date: {selectedWO.dueDate} • Target Run Size: {selectedWO.plannedQuantity} Box • Yielded: {selectedWO.producedQuantity} Box
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {selectedWO.status === "planned" && (
                    <button
                      onClick={handleRelease}
                      className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition-all"
                    >
                      <Play className="w-4 h-4" />
                      Release WO
                    </button>
                  )}

                  {selectedWO.status === "released" && (
                    <button
                      onClick={handleIssueMaterials}
                      className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition-all"
                    >
                      <Warehouse className="w-4 h-4" />
                      Issue Materials
                    </button>
                  )}

                  {selectedWO.status === "completed" && (
                    <button
                      onClick={handleCloseWO}
                      className="flex items-center gap-1.5 px-4 py-2 border border-gray-200 hover:bg-gray-50 text-gray-700 rounded-xl text-xs font-semibold transition-all"
                    >
                      <Ban className="w-4 h-4" />
                      Close Run
                    </button>
                  )}
                </div>
              </div>

              {/* Shop Floor Sequence Steps */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Left side: Job card operations sequence */}
                <div className="md:col-span-2 bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-4">
                  <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
                    <ListChecks className="w-5 h-5 text-gray-400" />
                    <h3 className="font-bold text-gray-900">Job Cards Board</h3>
                  </div>

                  <div className="space-y-4">
                    {selectedWO.jobCards.map((jc, index) => (
                      <div key={jc.id} className="p-4 bg-gray-50 rounded-xl border border-gray-100 flex items-center justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="w-5 h-5 rounded-full bg-gray-200 flex items-center justify-center text-[10px] font-bold text-gray-600">
                              {index + 1}
                            </span>
                            <span className="font-semibold text-gray-800 text-xs">{jc.operationName}</span>
                          </div>
                          <span className="text-[10px] text-gray-400 block mt-1.5">Workstation: {jc.workstation} • Runtime: {jc.runTime} mins</span>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${
                            jc.status === "completed" ? "bg-emerald-100 text-emerald-800" :
                            jc.status === "in_progress" ? "bg-indigo-100 text-indigo-800 animate-pulse" : "bg-gray-200 text-gray-600"
                          }`}>
                            {jc.status}
                          </span>

                          {selectedWO.status === "in_progress" && jc.status === "pending" && (
                            <button
                              onClick={() => handleStartJob(jc.id)}
                              className="p-1 px-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-[11px] font-semibold transition-all"
                            >
                              Start
                            </button>
                          )}

                          {selectedWO.status === "in_progress" && jc.status === "in_progress" && (
                            <button
                              onClick={() => handleCompleteJob(jc.id)}
                              className="p-1 px-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-[11px] font-semibold transition-all"
                            >
                              Complete
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Right side: Production yields */}
                <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-4">
                  <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
                    <FileDigit className="w-5 h-5 text-gray-400" />
                    <h3 className="font-bold text-gray-900">Post Production</h3>
                  </div>

                  {selectedWO.status === "in_progress" ? (
                    <form onSubmit={handlePostProduction} className="space-y-4">
                      <div>
                        <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Produced Yield (Box)</label>
                        <input
                          type="number"
                          required
                          value={producedQty}
                          onChange={(e) => setProducedQty(e.target.value)}
                          placeholder="e.g. 50"
                          className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Scrap Material Count</label>
                        <input
                          type="number"
                          value={scrapQty}
                          onChange={(e) => setScrapQty(e.target.value)}
                          placeholder="0"
                          className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                        />
                      </div>
                      <button
                        type="submit"
                        className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-xs transition-all"
                      >
                        Submit Output
                      </button>
                    </form>
                  ) : (
                    <div className="text-xs text-gray-400 leading-relaxed bg-gray-50 p-4 rounded-xl border border-dashed border-gray-200">
                      Production yields can only be posted once raw materials are issued and sequence job steps are marked as 'In Progress'.
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white border border-gray-100 rounded-2xl p-12 text-center text-gray-400 flex flex-col items-center justify-center gap-2">
              <Cpu className="w-12 h-12 text-gray-300" />
              <p className="text-sm font-semibold">No active Work Orders</p>
              <p className="text-xs">Schedule a run to start production execution processes.</p>
            </div>
          )}
        </div>
      </div>

      {/* Schedule Work Order Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-gray-100 space-y-6">
            <div>
              <h3 className="text-lg font-bold text-gray-900">Schedule Manufacturing Run</h3>
              <p className="text-xs text-gray-400 mt-1">Bind a finished good variant to its active BOM recipe</p>
            </div>
            <form onSubmit={handleCreateWO} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Target Finished Product</label>
                <select
                  value={selectedProduct}
                  onChange={(e) => setSelectedProduct(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                >
                  <option value="">Select Finished SKU...</option>
                  {finishedProducts.map(fp => (
                    <option key={fp.id} value={fp.id}>
                      {fp.name} ({fp.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">BOM Recipe Version</label>
                <select
                  value={selectedBOM}
                  onChange={(e) => setSelectedBOM(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                >
                  <option value="">Select recipe version...</option>
                  {boms.filter(b => b.productId === selectedProduct).map(b => (
                    <option key={b.id} value={b.id}>
                      v{b.version} ({b.status})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Planned Quantity (Box)</label>
                  <input
                    type="number"
                    required
                    value={plannedQty}
                    onChange={(e) => setPlannedQty(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Priority</label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value as any)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Due Date</label>
                <input
                  type="date"
                  required
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              <div className="flex items-center gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-semibold hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold"
                >
                  Schedule Run
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
