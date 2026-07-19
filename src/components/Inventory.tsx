import React, { useState, useEffect } from "react";
import { Package, Plus, SlidersHorizontal, Trash2, ArrowUpDown, History, Edit3, CheckCircle2, AlertTriangle, ArrowRightLeft } from "lucide-react";
import { Material, StockAdjustment } from "../types";

interface InventoryProps {
  token: string | null;
}

export default function Inventory({ token }: InventoryProps) {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [transactions, setTransactions] = useState<StockAdjustment[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [tenantCurrency, setTenantCurrency] = useState("USD");
  
  // Modals / forms state
  const [showAddModal, setShowAddModal] = useState(false);
  const [showAdjustModal, setShowAdjustModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showGrnModal, setShowGrnModal] = useState(false);
  
  const [activeMaterial, setActiveMaterial] = useState<Material | null>(null);
  const [editingMaterial, setEditingMaterial] = useState<Material | null>(null);

  // Add material form fields
  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [newBaseUom, setNewBaseUom] = useState("");
  const [newType, setNewType] = useState<"raw" | "semi-finished" | "finished">("raw");
  const [newLocation, setNewLocation] = useState("");
  const [newCost, setNewCost] = useState("");
  const [newSellingPrice, setNewSellingPrice] = useState("");

  // Edit material form fields
  const [editName, setEditName] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editLocation, setEditLocation] = useState("");
  const [editCost, setEditCost] = useState("");
  const [editSellingPrice, setEditSellingPrice] = useState("");

  // Adjust stock form fields
  const [adjustQty, setAdjustQty] = useState("");
  const [adjustType, setAdjustType] = useState<"add" | "remove" | "adjust">("add");
  const [adjustRemarks, setAdjustRemarks] = useState("");

  // GRN simulation fields
  const [grnMaterialId, setGrnMaterialId] = useState("");
  const [grnQty, setGrnQty] = useState("");
  const [grnUnitPrice, setGrnUnitPrice] = useState("");
  const [grnRemarks, setGrnRemarks] = useState("GRN Simulation - Supplier Delivery");
  
  // Standard Cost Update prompt
  const [showCostPrompt, setShowCostPrompt] = useState(false);
  const [promptData, setPromptData] = useState<{ material: Material; newCost: number } | null>(null);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const fetchMaterials = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [resMat, resTx] = await Promise.all([
        fetch("/api/v1/inventory/materials", { headers }),
        fetch("/api/v1/inventory/transactions", { headers })
      ]);

      if (resMat.ok) setMaterials(await resMat.json());
      if (resTx.ok) setTransactions(await resTx.json());
    } catch (err) {
      console.error("Error loading inventory", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTenantInfo = async () => {
    try {
      const res = await fetch("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.tenant && data.tenant.currency) {
          setTenantCurrency(data.tenant.currency);
        }
      }
    } catch (err) {
      console.error("Error fetching tenant info", err);
    }
  };

  useEffect(() => {
    fetchMaterials();
    fetchTenantInfo();
  }, [token]);

  const handleCreateMaterial = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      const res = await fetch("/api/v1/inventory/materials", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          code: newCode,
          name: newName,
          category: newCategory,
          baseUom: newBaseUom,
          type: newType,
          location: newLocation,
          currentCost: newType === "raw" ? Number(newCost || 0) : 0,
          sellingPrice: newType === "finished" ? Number(newSellingPrice || 0) : 0
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create material");

      setSuccess(`Material '${newName}' created successfully!`);
      setShowAddModal(false);
      
      // Reset form
      setNewCode("");
      setNewName("");
      setNewCategory("");
      setNewBaseUom("");
      setNewType("raw");
      setNewLocation("");
      setNewCost("");
      setNewSellingPrice("");

      fetchMaterials();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleEditMaterial = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!editingMaterial) return;

    try {
      const res = await fetch(`/api/v1/inventory/materials/${editingMaterial.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          name: editName,
          category: editCategory,
          location: editLocation,
          currentCost: editingMaterial.type === "raw" ? Number(editCost || 0) : 0,
          sellingPrice: editingMaterial.type === "finished" ? Number(editSellingPrice || 0) : 0
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to update material");

      setSuccess(`Material '${editName}' updated successfully!`);
      setShowEditModal(false);
      setEditingMaterial(null);
      fetchMaterials();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleAdjustStock = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!activeMaterial) return;

    try {
      const res = await fetch("/api/v1/inventory/stock/adjust", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          materialId: activeMaterial.id,
          quantity: Number(adjustQty),
          type: adjustType,
          remarks: adjustRemarks
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to adjust stock");

      setSuccess(`Stock levels for '${activeMaterial.name}' updated!`);
      setShowAdjustModal(false);
      setAdjustQty("");
      setAdjustRemarks("");
      setActiveMaterial(null);

      fetchMaterials();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleSimulateGrn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!grnMaterialId || !grnQty || !grnUnitPrice) {
      setError("Please fill in all GRN simulation fields.");
      return;
    }

    const selectedMat = materials.find(m => m.id === grnMaterialId);
    if (!selectedMat) return;

    try {
      // 1. Post stock adjustment to receive the stock
      const adjustRes = await fetch("/api/v1/inventory/stock/adjust", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          materialId: grnMaterialId,
          quantity: Number(grnQty),
          type: "add",
          remarks: `${grnRemarks} (PO Recv @ ${tenantCurrency} ${Number(grnUnitPrice).toFixed(2)}/unit)`
        })
      });

      const adjustData = await adjustRes.json();
      if (!adjustRes.ok) throw new Error(adjustData.error || "Failed to post GRN stock adjustment");

      const parsedUnitPrice = Number(grnUnitPrice);
      const currentStandardCost = selectedMat.currentCost || 0;

      // 2. Check if received unit price differs from current standard cost
      if (Math.abs(parsedUnitPrice - currentStandardCost) > 0.0001) {
        // Trigger prompt dialog
        setPromptData({
          material: selectedMat,
          newCost: parsedUnitPrice
        });
        setShowCostPrompt(true);
        setShowGrnModal(false);
      } else {
        setSuccess(`GRN processed successfully! Received ${grnQty} ${selectedMat.baseUom} of ${selectedMat.name} with zero cost variance.`);
        setShowGrnModal(false);
        // Reset form
        setGrnMaterialId("");
        setGrnQty("");
        setGrnUnitPrice("");
      }

      fetchMaterials();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleApplyStandardCostUpdate = async (update: boolean) => {
    if (!promptData) return;

    if (update) {
      try {
        const res = await fetch(`/api/v1/inventory/materials/${promptData.material.id}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            currentCost: promptData.newCost
          })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to update Standard Cost");

        setSuccess(`GRN received, and Standard Cost for '${promptData.material.name}' updated to ${tenantCurrency} ${promptData.newCost.toFixed(4)}!`);
      } catch (err: any) {
        setError(`GRN stock updated but cost master save failed: ${err.message}`);
      }
    } else {
      setSuccess(`GRN processed successfully! Stock updated. Standard Cost kept at ${tenantCurrency} ${(promptData.material.currentCost || 0).toFixed(4)}.`);
    }

    // Clean up
    setShowCostPrompt(false);
    setPromptData(null);
    setGrnMaterialId("");
    setGrnQty("");
    setGrnUnitPrice("");
    fetchMaterials();
  };

  // Filter materials based on search & category
  const filteredMaterials = materials.filter(m => {
    const matchesSearch = m.name.toLowerCase().includes(search.toLowerCase()) || 
                          m.code.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = categoryFilter === "all" || m.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  // Extract unique categories for filtering
  const categories = ["all", ...new Set(materials.map(m => m.category))];

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
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Materials Inventory</h1>
          <p className="text-gray-500 text-sm">Create, edit, and adjust stock for raw components and finished goods</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => { setShowGrnModal(true); setError(""); setSuccess(""); }}
            className="flex items-center gap-2 px-4 py-2.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-sm font-semibold transition-all shadow-lg hover:shadow-amber-500/15"
          >
            <ArrowRightLeft className="w-4 h-4" />
            Simulate GRN Receipt
          </button>
          <button
            onClick={() => { setShowAddModal(true); setError(""); setSuccess(""); }}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-all shadow-lg hover:shadow-indigo-500/15"
          >
            <Plus className="w-4 h-4" />
            Add Material
          </button>
        </div>
      </div>

      {/* Action Banners */}
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

      {/* Search & Filter Toolbar */}
      <div className="flex flex-col sm:flex-row items-center gap-4 bg-white p-4 rounded-2xl shadow-sm border border-gray-100">
        <div className="w-full sm:flex-1 relative">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by code or name..."
            className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
          />
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <SlidersHorizontal className="w-4 h-4 text-gray-400" />
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          >
            {categories.map(cat => (
              <option key={cat} value={cat}>
                {cat === "all" ? "All Categories" : cat}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Materials Table Container */}
        <div className="lg:col-span-2 bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-100 text-xs text-gray-400 font-bold uppercase tracking-wider">
                <th className="py-4 px-6">Material details</th>
                <th className="py-4 px-4 text-center">Type</th>
                <th className="py-4 px-4 text-center">Costing / Catalog</th>
                <th className="py-4 px-4 text-right">Current Stock</th>
                <th className="py-4 px-6 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-sm">
              {filteredMaterials.map(m => (
                <tr key={m.id} className="hover:bg-gray-50/50 transition-colors">
                  <td className="py-4 px-6">
                    <div className="font-semibold text-gray-900">{m.name}</div>
                    <div className="text-xs text-gray-400 flex items-center gap-2 mt-1">
                      <span className="font-mono text-[11px] bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">{m.code}</span>
                      <span>•</span>
                      <span>{m.category}</span>
                    </div>
                  </td>
                  <td className="py-4 px-4 text-center">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase ${
                      m.type === "finished" ? "bg-emerald-50 text-emerald-700 border border-emerald-100" : 
                      m.type === "semi-finished" ? "bg-purple-50 text-purple-700 border border-purple-100" :
                      "bg-blue-50 text-blue-700 border border-blue-100"
                    }`}>
                      {m.type}
                    </span>
                  </td>
                  <td className="py-4 px-4 text-center text-xs text-gray-500">
                    {m.type === "raw" && (
                      <div>
                        <span className="text-[10px] text-gray-400 block uppercase">Standard Cost</span>
                        <strong className="text-gray-700">{tenantCurrency} {(m.currentCost || 0).toFixed(4)}</strong>
                      </div>
                    )}
                    {m.type === "finished" && (
                      <div>
                        <span className="text-[10px] text-gray-400 block uppercase">Catalog Price</span>
                        <strong className="text-gray-700">{tenantCurrency} {(m.sellingPrice || 0).toFixed(2)}</strong>
                      </div>
                    )}
                    {m.type === "semi-finished" && <span className="text-gray-400 font-mono">—</span>}
                  </td>
                  <td className={`py-4 px-4 text-right font-bold ${m.stockLevel <= 5 ? "text-amber-500" : "text-gray-900"}`}>
                    {m.stockLevel.toLocaleString()} <span className="text-xs text-gray-400 font-normal">{m.baseUom}</span>
                  </td>
                  <td className="py-4 px-6 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <button
                        onClick={() => {
                          setEditingMaterial(m);
                          setEditName(m.name);
                          setEditCategory(m.category);
                          setEditLocation(m.location);
                          setEditCost(String(m.currentCost || 0));
                          setEditSellingPrice(String(m.sellingPrice || 0));
                          setShowEditModal(true);
                          setError("");
                          setSuccess("");
                        }}
                        className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-gray-100 rounded-lg transition-all"
                        title="Edit Material"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => { setActiveMaterial(m); setShowAdjustModal(true); setError(""); setSuccess(""); }}
                        className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl text-xs font-semibold transition-all"
                      >
                        Adjust Stock
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Audit Log / Stock Movement History */}
        <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
            <History className="w-5 h-5 text-gray-400" />
            <h3 className="font-bold text-gray-900">Stock Movements</h3>
          </div>
          <div className="space-y-4 max-h-[450px] overflow-y-auto pr-1">
            {transactions.slice().reverse().map(tx => {
              const mat = materials.find(m => m.id === tx.materialId);
              return (
                <div key={tx.id} className="p-3 bg-gray-50 rounded-xl border border-gray-100 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-800 truncate max-w-[120px]">
                      {mat?.name || "Unknown Material"}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                      tx.type === "add" ? "bg-emerald-100 text-emerald-800" :
                      tx.type === "remove" ? "bg-red-100 text-red-800" : "bg-gray-200 text-gray-800"
                    }`}>
                      {tx.type}: {tx.quantity}
                    </span>
                  </div>
                  <p className="text-gray-500">{tx.remarks}</p>
                  <span className="text-[10px] text-gray-400 block text-right">
                    {new Date(tx.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Add Material Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-gray-100 space-y-6">
            <div>
              <h3 className="text-lg font-bold text-gray-900">Add New Material Master</h3>
              <p className="text-xs text-gray-400 mt-1">Specify full descriptors for cataloging</p>
            </div>
            <form onSubmit={handleCreateMaterial} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Code / SKU</label>
                  <input
                    type="text"
                    required
                    value={newCode}
                    onChange={(e) => setNewCode(e.target.value)}
                    placeholder="RM-VAL-101"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Base UOM</label>
                  <input
                    type="text"
                    required
                    value={newBaseUom}
                    onChange={(e) => setNewBaseUom(e.target.value)}
                    placeholder="Kg, Box, Roll"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Material Name</label>
                <input
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Magnesium Stearate excipient"
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Category</label>
                  <input
                    type="text"
                    required
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    placeholder="e.g. Excipients"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Type</label>
                  <select
                    value={newType}
                    onChange={(e) => setNewType(e.target.value as any)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  >
                    <option value="raw">Raw Component</option>
                    <option value="semi-finished">Semi-Finished</option>
                    <option value="finished">Finished Good</option>
                  </select>
                </div>
              </div>

              {/* Dynamic Financial Configuration Section */}
              {newType === "raw" && (
                <div className="p-4 bg-blue-50 border border-blue-100 rounded-2xl space-y-3">
                  <span className="text-[10px] font-bold text-blue-800 uppercase tracking-wider block">Purchasing Information</span>
                  <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Standard Purchase Cost</label>
                    <div className="relative rounded-xl shadow-sm">
                      <input
                        type="number"
                        step="0.0001"
                        min="0"
                        value={newCost}
                        onChange={(e) => setNewCost(e.target.value)}
                        placeholder="0.0000"
                        className="w-full pl-3 pr-12 py-2 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                      />
                      <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                        <span className="text-xs text-gray-400 font-mono font-semibold">{tenantCurrency}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {newType === "finished" && (
                <div className="p-4 bg-emerald-50 border border-emerald-100 rounded-2xl space-y-3">
                  <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">Sales Pricing Info</span>
                  <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Selling Price (Catalog Default)</label>
                    <div className="relative rounded-xl shadow-sm">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={newSellingPrice}
                        onChange={(e) => setNewSellingPrice(e.target.value)}
                        placeholder="0.00"
                        className="w-full pl-3 pr-12 py-2 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                      />
                      <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                        <span className="text-xs text-gray-400 font-mono font-semibold">{tenantCurrency}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Warehouse Location</label>
                <input
                  type="text"
                  value={newLocation}
                  onChange={(e) => setNewLocation(e.target.value)}
                  placeholder="e.g. Rack A-12"
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>
              <div className="flex items-center gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-semibold hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold"
                >
                  Add Material
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Material Modal */}
      {showEditModal && editingMaterial && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-gray-100 space-y-6">
            <div>
              <h3 className="text-lg font-bold text-gray-900">Edit Material Master</h3>
              <p className="text-xs text-indigo-600 mt-1">{editingMaterial.name} ({editingMaterial.code})</p>
            </div>
            <form onSubmit={handleEditMaterial} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Material Name</label>
                <input
                  type="text"
                  required
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  placeholder="Material name"
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Category</label>
                  <input
                    type="text"
                    required
                    value={editCategory}
                    onChange={(e) => setEditCategory(e.target.value)}
                    placeholder="Category"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Warehouse Location</label>
                  <input
                    type="text"
                    value={editLocation}
                    onChange={(e) => setEditLocation(e.target.value)}
                    placeholder="e.g. Rack A-12"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>
              </div>

              {/* Dynamic Financial Configuration Section */}
              {editingMaterial.type === "raw" && (
                <div className="p-4 bg-blue-50 border border-blue-100 rounded-2xl space-y-3">
                  <span className="text-[10px] font-bold text-blue-800 uppercase tracking-wider block">Purchasing Information</span>
                  <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Standard Purchase Cost</label>
                    <div className="relative rounded-xl shadow-sm">
                      <input
                        type="number"
                        step="0.0001"
                        min="0"
                        value={editCost}
                        onChange={(e) => setEditCost(e.target.value)}
                        placeholder="0.0000"
                        className="w-full pl-3 pr-12 py-2 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                      />
                      <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                        <span className="text-xs text-gray-400 font-mono font-semibold">{tenantCurrency}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {editingMaterial.type === "finished" && (
                <div className="p-4 bg-emerald-50 border border-emerald-100 rounded-2xl space-y-3">
                  <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">Sales Pricing Info</span>
                  <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Selling Price (Catalog Default)</label>
                    <div className="relative rounded-xl shadow-sm">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={editSellingPrice}
                        onChange={(e) => setEditSellingPrice(e.target.value)}
                        placeholder="0.00"
                        className="w-full pl-3 pr-12 py-2 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                      />
                      <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                        <span className="text-xs text-gray-400 font-mono font-semibold">{tenantCurrency}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowEditModal(false); setEditingMaterial(null); }}
                  className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-semibold hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Adjust Stock Modal */}
      {showAdjustModal && activeMaterial && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-gray-100 space-y-6">
            <div>
              <h3 className="text-lg font-bold text-gray-900">Adjust Stock levels</h3>
              <p className="text-xs text-indigo-600 mt-1">{activeMaterial.name} ({activeMaterial.code})</p>
            </div>
            <form onSubmit={handleAdjustStock} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Adjustment Type</label>
                  <select
                    value={adjustType}
                    onChange={(e) => setAdjustType(e.target.value as any)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  >
                    <option value="add">Add (Receipt)</option>
                    <option value="remove">Remove (Issue)</option>
                    <option value="adjust">Adjust (Set Absolute)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Quantity ({activeMaterial.baseUom})</label>
                  <input
                    type="number"
                    required
                    value={adjustQty}
                    onChange={(e) => setAdjustQty(e.target.value)}
                    placeholder="0"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Remarks / Reference</label>
                <input
                  type="text"
                  required
                  value={adjustRemarks}
                  onChange={(e) => setAdjustRemarks(e.target.value)}
                  placeholder="e.g. Audit verification count mismatch"
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>
              <div className="flex items-center gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowAdjustModal(false); setActiveMaterial(null); }}
                  className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-semibold hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold"
                >
                  Apply Change
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Simulate GRN Receipt Modal */}
      {showGrnModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-gray-100 space-y-6">
            <div>
              <h3 className="text-lg font-bold text-gray-900">Simulate Goods Receipt (GRN)</h3>
              <p className="text-xs text-gray-400 mt-1">Simulate delivery processing and inventory valuation checks</p>
            </div>
            <form onSubmit={handleSimulateGrn} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Raw Material</label>
                <select
                  required
                  value={grnMaterialId}
                  onChange={(e) => {
                    const val = e.target.value;
                    setGrnMaterialId(val);
                    const mat = materials.find(m => m.id === val);
                    if (mat && mat.currentCost) {
                      setGrnUnitPrice(String(mat.currentCost));
                    } else {
                      setGrnUnitPrice("");
                    }
                  }}
                  className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                >
                  <option value="">-- Select Purchased Component --</option>
                  {materials.filter(m => m.type === "raw").map(m => (
                    <option key={m.id} value={m.id}>{m.name} ({m.code})</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Received Quantity</label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={grnQty}
                    onChange={(e) => setGrnQty(e.target.value)}
                    placeholder="100"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Supplier Unit Price</label>
                  <div className="relative rounded-xl shadow-sm">
                    <input
                      type="number"
                      step="0.0001"
                      required
                      min="0"
                      value={grnUnitPrice}
                      onChange={(e) => setGrnUnitPrice(e.target.value)}
                      placeholder="0.0000"
                      className="w-full pl-3 pr-12 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                    />
                    <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                      <span className="text-xs text-gray-400 font-mono font-semibold">{tenantCurrency}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Remarks / Reference</label>
                <input
                  type="text"
                  required
                  value={grnRemarks}
                  onChange={(e) => setGrnRemarks(e.target.value)}
                  placeholder="GRN Simulation"
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>
              <div className="flex items-center gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowGrnModal(false)}
                  className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-semibold hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-sm font-semibold shadow-lg hover:shadow-amber-500/10"
                >
                  Post GRN Receipts
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Standard Cost Update Prompt Dialog */}
      {showCostPrompt && promptData && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-amber-200 space-y-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-amber-100 text-amber-600 rounded-2xl shrink-0">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">Standard Purchase Cost Mismatch</h3>
                <p className="text-xs text-gray-400 mt-1">A difference in procurement valuation was detected.</p>
              </div>
            </div>

            <div className="p-4 bg-gray-50 rounded-2xl border border-gray-100 text-sm space-y-3">
              <div className="text-xs text-gray-500 font-semibold uppercase">Material Details</div>
              <div className="font-bold text-gray-900">{promptData.material.name}</div>
              <div className="grid grid-cols-2 gap-4 pt-2 border-t border-gray-200/50">
                <div>
                  <span className="text-[10px] text-gray-400 block uppercase">Current Standard Cost</span>
                  <span className="font-mono font-bold text-gray-600">
                    {tenantCurrency} {(promptData.material.currentCost || 0).toFixed(4)}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-amber-600 block uppercase font-semibold">New GRN Price</span>
                  <span className="font-mono font-bold text-amber-600">
                    {tenantCurrency} {promptData.newCost.toFixed(4)}
                  </span>
                </div>
              </div>
            </div>

            <div className="text-xs text-gray-500 leading-relaxed">
              Accepting the new price will overwrite the material's Standard Cost in the Material Master catalog. This new valuation will immediately be used in future Bill of Material (BOM) rollup calculations.
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                type="button"
                onClick={() => handleApplyStandardCostUpdate(false)}
                className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-semibold text-gray-600 hover:bg-gray-50"
              >
                Keep Existing Standard Cost
              </button>
              <button
                type="button"
                onClick={() => handleApplyStandardCostUpdate(true)}
                className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold shadow-lg hover:shadow-indigo-500/10"
              >
                Update Standard Cost Master
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
