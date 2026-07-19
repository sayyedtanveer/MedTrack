import React, { useState, useEffect } from "react";
import { FileSpreadsheet, Plus, Copy, CheckCircle, Calculator, Info, Cpu, ListCollapse } from "lucide-react";
import { BOM, Material } from "../types";

interface BOMWorkspaceProps {
  token: string | null;
}

export default function BOMWorkspace({ token }: BOMWorkspaceProps) {
  const [boms, setBoms] = useState<BOM[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedBOM, setSelectedBOM] = useState<BOM | null>(null);
  const [costRollup, setCostRollup] = useState<{ materialsCost: number; laborCost: number; totalCost: number } | null>(null);

  // Forms state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newVersion, setNewVersion] = useState("1.0");
  const [selectedProduct, setSelectedProduct] = useState("");

  // Copy version state
  const [showCopyModal, setShowCopyModal] = useState(false);
  const [copyVersionStr, setCopyVersionStr] = useState("1.1");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const fetchData = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [resBom, resMat] = await Promise.all([
        fetch("/api/v1/boms", { headers }),
        fetch("/api/v1/inventory/materials", { headers })
      ]);

      if (resBom.ok) {
        const bomList: BOM[] = await resBom.json();
        setBoms(bomList);
        // Default select first BOM
        if (bomList.length > 0 && !selectedBOM) {
          setSelectedBOM(bomList[0]);
        } else if (selectedBOM) {
          const updated = bomList.find(b => b.id === selectedBOM.id);
          if (updated) setSelectedBOM(updated);
        }
      }
      if (resMat.ok) setMaterials(await resMat.json());
    } catch (err) {
      console.error("Error loading BOM Workspace", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [token]);

  // Fetch costs rollup when selectedBOM changes
  useEffect(() => {
    if (selectedBOM) {
      fetchCostRollup(selectedBOM.id);
    } else {
      setCostRollup(null);
    }
  }, [selectedBOM]);

  const fetchCostRollup = async (bomId: string) => {
    try {
      const res = await fetch(`/api/v1/boms/${bomId}/costs`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCostRollup(data);
      }
    } catch (err) {
      console.error("Failed to fetch cost rollup", err);
    }
  };

  const handleCreateBOM = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!selectedProduct) {
      setError("Please select a finished/semi-finished product");
      return;
    }

    try {
      // Create a default BOM structure with components to make it functional
      const rawComponents = materials.filter(m => m.type === "raw");
      const sampleLines = rawComponents.slice(0, 3).map((rc, idx) => ({
        id: `line-new-${idx}`,
        materialId: rc.id,
        quantity: idx === 0 ? 0.4 : idx === 1 ? 0.2 : 0.05,
        scrapPercentage: 2
      }));

      const sampleOps = [
        { id: "op-new-10", sequence: 10, name: "Dispensing & Blending", workstation: "WS-MIX-01", setupTimeMinutes: 30, runTimeMinutes: 1, hourlyRate: 40 },
        { id: "op-new-20", sequence: 20, name: "Tablet Output Compression", workstation: "WS-COMP-02", setupTimeMinutes: 45, runTimeMinutes: 2, hourlyRate: 65 }
      ];

      const res = await fetch("/api/v1/boms", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          productId: selectedProduct,
          version: newVersion,
          lines: sampleLines,
          operations: sampleOps
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create BOM");

      setSuccess(`BOM Version ${newVersion} created!`);
      setShowCreateModal(false);
      setSelectedBOM(data);
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleCopyBOM = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!selectedBOM) return;

    try {
      const res = await fetch(`/api/v1/boms/${selectedBOM.id}/copy`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ newVersion: copyVersionStr })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to copy BOM");

      setSuccess(`BOM cloned to version ${copyVersionStr} as draft!`);
      setShowCopyModal(false);
      setSelectedBOM(data);
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleActivateBOM = async () => {
    if (!selectedBOM) return;
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`/api/v1/boms/${selectedBOM.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ status: "active" })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to activate BOM");

      setSuccess(`BOM version ${selectedBOM.version} activated!`);
      setSelectedBOM(data);
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const finishedProducts = materials.filter(m => m.type === "finished" || m.type === "semi-finished");

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-8 bg-gray-50 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">BOM Workspace</h1>
          <p className="text-gray-500 text-sm">Specify bill of materials, operations sequences, and total rollup manufacturing costs</p>
        </div>
        <button
          onClick={() => { setShowCreateModal(true); setError(""); setSuccess(""); }}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-all shadow-lg hover:shadow-indigo-500/15"
        >
          <Plus className="w-4 h-4" />
          Create BOM
        </button>
      </div>

      {/* Action Notifications */}
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

      {/* BOM Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Left Side: BOM Versions List */}
        <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="border-b border-gray-100 pb-3">
            <h3 className="font-bold text-gray-900">BOM Listings</h3>
            <p className="text-xs text-gray-400">Select templates to edit or analyze</p>
          </div>
          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
            {boms.map(bom => {
              const product = materials.find(m => m.id === bom.productId);
              const isSelected = selectedBOM?.id === bom.id;
              return (
                <div
                  key={bom.id}
                  onClick={() => { setSelectedBOM(bom); setError(""); setSuccess(""); }}
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    isSelected 
                      ? "border-indigo-600 bg-indigo-50/40 shadow-sm" 
                      : "border-gray-100 bg-gray-50/50 hover:bg-gray-100/50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-gray-500 font-mono">
                      v{bom.version}
                    </span>
                    <span className={`inline-flex px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wide ${
                      bom.status === "active" ? "bg-emerald-100 text-emerald-800" : "bg-gray-200 text-gray-600"
                    }`}>
                      {bom.status}
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-gray-900 mt-2 truncate">
                    {product?.name || "Unknown Product"}
                  </h4>
                  <p className="text-[11px] text-gray-400 mt-1 truncate">SKU: {product?.code}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Side: Selected BOM Workspace Details */}
        <div className="lg:col-span-2 space-y-6">
          {selectedBOM ? (
            <>
              {/* Product and Version Header Card */}
              <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <span className="text-[11px] font-bold text-indigo-600 uppercase tracking-wider block">
                    Active Product BOM details
                  </span>
                  <h2 className="text-xl font-bold text-gray-900 mt-1">
                    {materials.find(m => m.id === selectedBOM.productId)?.name || "Unknown Product"}
                  </h2>
                  <p className="text-xs text-gray-400 mt-1 flex items-center gap-1.5">
                    <span>SKU: {materials.find(m => m.id === selectedBOM.productId)?.code}</span>
                    <span>•</span>
                    <span>Version: v{selectedBOM.version}</span>
                    <span>•</span>
                    <span className="font-semibold text-gray-500 uppercase">{selectedBOM.status}</span>
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={() => { setShowCopyModal(true); setError(""); setSuccess(""); }}
                    className="flex items-center gap-1.5 px-3.5 py-2 border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 hover:bg-gray-50 transition-all"
                  >
                    <Copy className="w-4 h-4" />
                    Copy Version
                  </button>
                  {selectedBOM.status !== "active" && (
                    <button
                      onClick={handleActivateBOM}
                      className="flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition-all"
                    >
                      <CheckCircle className="w-4 h-4" />
                      Activate Draft
                    </button>
                  )}
                </div>
              </div>

              {/* Two Column Cost and Tree breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Cost Summary Box */}
                <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-4">
                  <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
                    <Calculator className="w-5 h-5 text-gray-400" />
                    <h3 className="font-bold text-gray-900">Cost rollup</h3>
                  </div>
                  {costRollup ? (
                    <div className="space-y-3.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-500">Component cost</span>
                        <span className="font-semibold text-gray-800">${costRollup.materialsCost.toFixed(2)}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-500">Labor & mixing</span>
                        <span className="font-semibold text-gray-800">${costRollup.laborCost.toFixed(2)}</span>
                      </div>
                      <div className="border-t border-gray-100 pt-3.5 flex items-center justify-between">
                        <span className="text-sm font-bold text-gray-900">Total BOM Cost</span>
                        <span className="text-lg font-extrabold text-indigo-600">${costRollup.totalCost.toFixed(2)}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-gray-400">Loading cost data...</div>
                  )}
                </div>

                {/* BOM Components and Operations tabs */}
                <div className="md:col-span-2 bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-4">
                  <div className="flex items-center justify-between border-b border-gray-100 pb-3">
                    <div className="flex items-center gap-2">
                      <ListCollapse className="w-5 h-5 text-gray-400" />
                      <h3 className="font-bold text-gray-900">Structure & Operations</h3>
                    </div>
                  </div>

                  <div className="space-y-4">
                    {/* BOM Lines */}
                    <div>
                      <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2.5">Components (BOM Lines)</h4>
                      <div className="space-y-2">
                        {selectedBOM.lines.map(line => {
                          const mat = materials.find(m => m.id === line.materialId);
                          return (
                            <div key={line.id} className="flex items-center justify-between text-xs p-2.5 bg-gray-50 rounded-xl border border-gray-100">
                              <div>
                                <span className="font-semibold text-gray-800">{mat?.name || "Unknown material"}</span>
                                <span className="text-[10px] text-gray-400 font-mono block mt-0.5">{mat?.code}</span>
                              </div>
                              <div className="text-right">
                                <span className="font-bold text-gray-800">{line.quantity} {mat?.baseUom}</span>
                                <span className="text-[10px] text-gray-400 block mt-0.5">Scrap: {line.scrapPercentage}%</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* BOM Operations */}
                    <div>
                      <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2.5">Manufacturing Steps</h4>
                      <div className="space-y-2">
                        {selectedBOM.operations.map(op => (
                          <div key={op.id} className="flex items-center justify-between text-xs p-2.5 bg-gray-50 rounded-xl border border-gray-100">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="bg-gray-200 text-gray-700 text-[10px] font-bold px-1 rounded">Seq {op.sequence}</span>
                                <span className="font-semibold text-gray-800">{op.name}</span>
                              </div>
                              <span className="text-[10px] text-gray-400 block mt-1">Station: {op.workstation}</span>
                            </div>
                            <div className="text-right">
                              <span className="font-bold text-gray-800">{(op.setupTimeMinutes + op.runTimeMinutes)}m total</span>
                              <span className="text-[10px] text-gray-400 block mt-0.5">Rate: ${op.hourlyRate}/hr</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white border border-gray-100 rounded-2xl p-12 text-center text-gray-400 flex flex-col items-center justify-center gap-2">
              <FileSpreadsheet className="w-12 h-12 text-gray-300" />
              <p className="text-sm font-semibold">No BOM Templates found</p>
              <p className="text-xs">Click 'Create BOM' to start authoring your first build recipe.</p>
            </div>
          )}
        </div>
      </div>

      {/* Create BOM Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-gray-100 space-y-6">
            <div>
              <h3 className="text-lg font-bold text-gray-900">Create Bill of Materials</h3>
              <p className="text-xs text-gray-400 mt-1">Initialize a manufacturing recipe for finished goods</p>
            </div>
            <form onSubmit={handleCreateBOM} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Target Product</label>
                <select
                  value={selectedProduct}
                  onChange={(e) => setSelectedProduct(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
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
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">BOM Version</label>
                <input
                  type="text"
                  required
                  value={newVersion}
                  onChange={(e) => setNewVersion(e.target.value)}
                  placeholder="e.g. 1.0"
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>
              <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-xl flex gap-2 text-xs text-indigo-700">
                <Info className="w-4 h-4 shrink-0 mt-0.5" />
                <p>New recipes are created in draft mode with default raw components and operations, ready to be fine-tuned or activated.</p>
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
                  Initialize Recipe
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Copy BOM Version Modal */}
      {showCopyModal && selectedBOM && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-gray-100 space-y-6">
            <div>
              <h3 className="text-lg font-bold text-gray-900">Clone BOM to New Version</h3>
              <p className="text-xs text-gray-400 mt-1">Duplicates current recipe lines and sequence</p>
            </div>
            <form onSubmit={handleCopyBOM} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">New Version Identifier</label>
                <input
                  type="text"
                  required
                  value={copyVersionStr}
                  onChange={(e) => setCopyVersionStr(e.target.value)}
                  placeholder="e.g. 1.1"
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>
              <div className="flex items-center gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCopyModal(false)}
                  className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-semibold hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold"
                >
                  Clone Recipe
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
