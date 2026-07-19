import React, { useState, useEffect } from "react";
import { BadgeDollarSign, Plus, CheckCircle, Truck, UserCheck, Percent, Layers, Landmark, Edit3, Settings, Calendar, Info, Search, Trash2, ArrowLeft, ToggleLeft, ToggleRight, AlertCircle, ShoppingCart } from "lucide-react";
import { Client, SalesOrder, Material } from "../types";

interface SalesModuleProps {
  token: string | null;
}

export default function SalesModule({ token }: SalesModuleProps) {
  // Navigation
  const [subTab, setSubTab] = useState<"dashboard" | "pricelists">("dashboard");

  const [clients, setClients] = useState<Client[]>([]);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [priceLists, setPriceLists] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState<SalesOrder | null>(null);

  // Forms state
  const [showOrderModal, setShowOrderModal] = useState(false);
  const [showClientModal, setShowClientModal] = useState(false);
  const [editingClient, setEditingClient] = useState<Client | null>(null);

  // Price lists state
  const [showPLModal, setShowPLModal] = useState(false);
  const [editingPL, setEditingPL] = useState<any | null>(null);
  const [selectedPL, setSelectedPL] = useState<any | null>(null);
  const [showLineModal, setShowLineModal] = useState(false);
  const [plSearch, setPlSearch] = useState("");

  // New/Edit Client fields
  const [clientName, setClientName] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [creditLimit, setCreditLimit] = useState("50000");
  const [clientDefaultPL, setClientDefaultPL] = useState("");

  // New Order fields
  const [orderClient, setOrderClient] = useState("");
  const [orderProduct, setOrderProduct] = useState("");
  const [orderQty, setOrderQty] = useState("");
  const [orderPrice, setOrderPrice] = useState("");
  const [taxRate, setTaxRate] = useState("5");
  const [discount, setDiscount] = useState("0");
  const [deliveryDate, setDeliveryDate] = useState("");

  // New Price List fields
  const [plName, setPlName] = useState("");
  const [plValidFrom, setPlValidFrom] = useState("");
  const [plValidTo, setPlValidTo] = useState("");
  const [plIsDefault, setPlIsDefault] = useState(false);
  const [plIsActive, setPlIsActive] = useState(true);

  // New Price List Line fields
  const [lineProductId, setLineProductId] = useState("");
  const [lineUnitPrice, setLineUnitPrice] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const fetchData = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [resCli, resSo, resMat, resPl] = await Promise.all([
        fetch("/api/v1/sales/clients", { headers }),
        fetch("/api/v1/sales/orders", { headers }),
        fetch("/api/v1/inventory/materials", { headers }),
        fetch("/api/v1/sales/price-lists", { headers })
      ]);

      if (resCli.ok) setClients(await resCli.json());
      if (resMat.ok) setMaterials(await resMat.json());
      if (resPl.ok) {
        const plList = await resPl.json();
        setPriceLists(plList);
        if (selectedPL) {
          const updatedPL = plList.find((p: any) => p.id === selectedPL.id);
          if (updatedPL) setSelectedPL(updatedPL);
        }
      }
      if (resSo.ok) {
        const orderList = await resSo.json();
        setOrders(orderList);
        if (orderList.length > 0 && !selectedOrder) {
          setSelectedOrder(orderList[0]);
        } else if (selectedOrder) {
          const updated = orderList.find((o: any) => o.id === selectedOrder.id);
          if (updated) setSelectedOrder(updated);
        }
      }
    } catch (err) {
      console.error("Error loading Sales module", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [token]);

  // Price resolution effect during Sales Order creation
  useEffect(() => {
    const triggerPriceResolution = async () => {
      if (orderClient && orderProduct) {
        try {
          const dateStr = new Date().toISOString().split("T")[0];
          const res = await fetch(
            `/api/v1/sales/resolve-price?clientId=${orderClient}&productId=${orderProduct}&orderDate=${dateStr}`,
            {
              headers: { Authorization: `Bearer ${token}` }
            }
          );
          if (res.ok) {
            const data = await res.json();
            setOrderPrice(String(data.price));
            setError("");
          } else {
            const data = await res.json();
            setOrderPrice("");
            setError(`Pricing warning: ${data.error || "No resolved price found. Please enter a manual override."}`);
          }
        } catch (err) {
          console.error("Price resolution error", err);
        }
      } else {
        setOrderPrice("");
      }
    };
    triggerPriceResolution();
  }, [orderClient, orderProduct]);

  const handleCreateOrUpdateClient = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      const isEdit = !!editingClient;
      const url = isEdit 
        ? `/api/v1/sales/clients/${editingClient.id}` 
        : "/api/v1/sales/clients";
      const method = isEdit ? "PATCH" : "POST";

      const res = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          name: clientName,
          email: clientEmail,
          creditLimit: Number(creditLimit),
          defaultPriceListId: clientDefaultPL === "" || clientDefaultPL === "__none__" ? null : clientDefaultPL
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to save client");

      setSuccess(`Client '${clientName}' successfully ${isEdit ? "updated" : "onboarded"}!`);
      setShowClientModal(false);
      setEditingClient(null);
      
      // Reset
      setClientName("");
      setClientEmail("");
      setCreditLimit("50000");
      setClientDefaultPL("");
      
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleCreateOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!orderClient || !orderProduct || !orderQty || !orderPrice) {
      setError("Please fill out all order parameters");
      return;
    }

    try {
      const lines = [{
        id: `sol-${Date.now()}`,
        productId: orderProduct,
        quantity: Number(orderQty),
        unitPrice: Number(orderPrice)
      }];

      const res = await fetch("/api/v1/sales/orders", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          clientId: orderClient,
          lines,
          taxRate: Number(taxRate),
          discountAmount: Number(discount),
          deliveryDate
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create order");

      setSuccess(`Sales Order ${data.orderNumber} successfully drafted!`);
      setShowOrderModal(false);
      
      // Reset forms
      setOrderClient("");
      setOrderProduct("");
      setOrderQty("");
      setOrderPrice("");
      setDeliveryDate("");
      setSelectedOrder(data);
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleConfirmOrder = async () => {
    if (!selectedOrder) return;
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`/api/v1/sales/orders/${selectedOrder.id}/confirm`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to confirm order");

      setSuccess(`Order ${selectedOrder.orderNumber} confirmed! Customer credit allocation locked.`);
      setSelectedOrder(data);
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleShipOrder = async () => {
    if (!selectedOrder) return;
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`/api/v1/sales/orders/${selectedOrder.id}/ship`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to dispatch/ship order");

      setSuccess(`Order ${selectedOrder.orderNumber} dispatched! Finished goods deducted from inventory.`);
      setSelectedOrder(data);
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  // Price List Management Logic
  const handleCreateOrUpdatePL = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      const isEdit = !!editingPL;
      const url = isEdit 
        ? `/api/v1/sales/price-lists/${editingPL.id}` 
        : "/api/v1/sales/price-lists";
      const method = isEdit ? "PATCH" : "POST";

      const res = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          name: plName,
          validFrom: plValidFrom,
          validTo: plValidTo === "" ? null : plValidTo,
          isDefault: plIsDefault,
          isActive: plIsActive
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to save price list");

      setSuccess(`Price List '${plName}' saved successfully.`);
      setShowPLModal(false);
      setEditingPL(null);

      // Reset
      setPlName("");
      setPlValidFrom("");
      setPlValidTo("");
      setPlIsDefault(false);
      setPlIsActive(true);

      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleAddPLLine = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!selectedPL) return;

    try {
      const res = await fetch(`/api/v1/sales/price-lists/${selectedPL.id}/lines`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          productId: lineProductId,
          productType: "variant",
          unitPrice: Number(lineUnitPrice)
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to add price line");

      setSuccess("Price list line added successfully!");
      setShowLineModal(false);
      setLineProductId("");
      setLineUnitPrice("");
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleUpdatePLLinePrice = async (productId: string, newPrice: string) => {
    if (!selectedPL) return;
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`/api/v1/sales/price-lists/${selectedPL.id}/lines`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          productId,
          unitPrice: Number(newPrice)
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to update line price");

      setSuccess("Price line updated.");
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDeletePLLine = async (productId: string) => {
    if (!selectedPL) return;
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`/api/v1/sales/price-lists/${selectedPL.id}/lines/${productId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to delete line");
      }

      setSuccess("Price list line deleted.");
      fetchData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      draft: "bg-gray-100 text-gray-700 border-gray-200",
      confirmed: "bg-blue-50 text-blue-700 border-blue-100",
      shipped: "bg-emerald-50 text-emerald-700 border-emerald-100",
      delivered: "bg-indigo-50 text-indigo-700 border-indigo-100",
      cancelled: "bg-red-50 text-red-700 border-red-100"
    };
    return (
      <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-bold border uppercase tracking-wider ${styles[status] || ""}`}>
        {status}
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

  const finishedProducts = materials.filter(m => m.type === "finished");
  
  // Filtering Price Lists on Search Input
  const filteredPriceLists = priceLists.filter(pl => 
    pl.name.toLowerCase().includes(plSearch.toLowerCase())
  );

  return (
    <div className="flex-1 overflow-y-auto p-8 bg-gray-50 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Sales & Pricing Center</h1>
          <p className="text-gray-500 text-sm">Configure multi-tier price lists, manage credit allocations, and monitor agreements</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => { 
              setEditingClient(null);
              setClientName("");
              setClientEmail("");
              setCreditLimit("50000");
              setClientDefaultPL("");
              setShowClientModal(true); 
              setError(""); 
              setSuccess(""); 
            }}
            className="flex items-center gap-2 px-3.5 py-2.5 border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 rounded-xl text-sm font-semibold transition-all shadow-sm"
          >
            <UserCheck className="w-4 h-4 text-gray-500" />
            Onboard Client
          </button>
          <button
            onClick={() => { setShowOrderModal(true); setError(""); setSuccess(""); }}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-all shadow-lg hover:shadow-indigo-500/15"
          >
            <Plus className="w-4 h-4" />
            New Sales Order
          </button>
        </div>
      </div>

      {/* Navigation SubTabs */}
      <div className="flex border-b border-gray-200 gap-4">
        <button
          onClick={() => { setSubTab("dashboard"); setError(""); setSuccess(""); }}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${subTab === "dashboard" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          <Landmark className="w-4 h-4" />
          Contracts & Credit Dashboard
        </button>
        <button
          onClick={() => { setSubTab("pricelists"); setError(""); setSuccess(""); }}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${subTab === "pricelists" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          <Percent className="w-4 h-4" />
          Price Lists Management
        </button>
      </div>

      {/* Action Notifications */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-start gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div><strong>Attention Required: </strong>{error}</div>
        </div>
      )}
      {success && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl">
          <strong>Success: </strong>{success}
        </div>
      )}

      {/* TAB 1: DASHBOARD VIEW */}
      {subTab === "dashboard" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          {/* Left Side: Client Accounts Board */}
          <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <div className="flex items-center gap-2">
                <Landmark className="w-5 h-5 text-gray-400" />
                <h3 className="font-bold text-gray-900">Credit Allocations</h3>
              </div>
            </div>
            <div className="space-y-4">
              {clients.map(cli => {
                const percent = Math.min(100, Math.round((cli.creditUsed / cli.creditLimit) * 100));
                const pl = priceLists.find(p => p.id === cli.defaultPriceListId);
                return (
                  <div key={cli.id} className="p-4 bg-gray-50 hover:bg-gray-100/50 rounded-2xl border border-gray-100 transition-all space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="text-sm font-bold text-gray-900">{cli.name}</h4>
                        <span className="text-[10px] text-gray-400 font-mono">{cli.code}</span>
                      </div>
                      <button
                        onClick={() => {
                          setEditingClient(cli);
                          setClientName(cli.name);
                          setClientEmail(cli.email);
                          setCreditLimit(String(cli.creditLimit));
                          setClientDefaultPL(cli.defaultPriceListId || "");
                          setShowClientModal(true);
                          setError("");
                          setSuccess("");
                        }}
                        className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-white rounded-lg transition-all border border-transparent hover:border-gray-100 shrink-0"
                        title="Edit client configuration"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    {/* Default Price List Indicator */}
                    <div className="text-[11px] text-gray-500 bg-white px-2 py-1.5 rounded-lg border border-gray-100 flex items-center justify-between gap-1">
                      <span className="text-gray-400">Default Price List:</span>
                      {pl ? (
                        <span className="font-semibold text-indigo-600 truncate">{pl.name}</span>
                      ) : (
                        <span className="text-gray-400 italic">None (Catalog Price Fallback)</span>
                      )}
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs font-semibold text-gray-700">
                        <span>${cli.creditUsed.toLocaleString()} Used</span>
                        <span>Max ${cli.creditLimit.toLocaleString()}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                        <div 
                          className={`h-full rounded-full transition-all duration-500 ${percent > 85 ? "bg-red-500" : percent > 50 ? "bg-amber-500" : "bg-indigo-600"}`} 
                          style={{ width: `${percent}%` }}
                        ></div>
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-gray-400">
                        <span>Risk utilization</span>
                        <span>{percent}% allocated</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Middle Column: Sales Contracts Queue */}
          <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="border-b border-gray-100 pb-3">
              <h3 className="font-bold text-gray-900">Sales Contracts</h3>
              <p className="text-xs text-gray-400">Fulfillment pipeline and contract logs</p>
            </div>
            <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
              {orders.map(so => {
                const client = clients.find(c => c.id === so.clientId);
                const isSelected = selectedOrder?.id === so.id;
                return (
                  <div
                    key={so.id}
                    onClick={() => { setSelectedOrder(so); setError(""); setSuccess(""); }}
                    className={`p-4 rounded-xl border transition-all cursor-pointer ${
                      isSelected 
                        ? "border-indigo-600 bg-indigo-50/40 shadow-sm" 
                        : "border-gray-100 bg-gray-50/50 hover:bg-gray-100/50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-gray-600">{so.orderNumber}</span>
                      {getStatusBadge(so.status)}
                    </div>
                    <h4 className="text-sm font-bold text-gray-900 mt-2 truncate">
                      {client?.name || "Unknown Client"}
                    </h4>
                    <p className="text-[11px] text-indigo-600 font-bold mt-1">Total value: ${so.totalAmount.toLocaleString()}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Active Order Details workspace */}
          <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-6">
            {selectedOrder ? (
              <>
                <div className="border-b border-gray-100 pb-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm font-extrabold text-gray-500">{selectedOrder.orderNumber}</span>
                    {getStatusBadge(selectedOrder.status)}
                  </div>
                  <h3 className="text-lg font-bold text-gray-900">
                    {clients.find(c => c.id === selectedOrder.clientId)?.name || "Unknown Client"}
                  </h3>
                  <p className="text-xs text-gray-400">
                    Expected Dispatch: {selectedOrder.deliveryDate} • Date Booked: {selectedOrder.orderDate}
                  </p>
                </div>

                {/* Order Lines summary */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Order items</h4>
                  {selectedOrder.lines.map(line => {
                    const prod = materials.find(m => m.id === line.productId);
                    return (
                      <div key={line.id} className="p-3 bg-gray-50 rounded-xl border border-gray-100 flex items-center justify-between text-xs">
                        <div>
                          <span className="font-semibold text-gray-800">{prod?.name || "Unknown Product"}</span>
                          <span className="text-[10px] text-gray-400 block mt-0.5">SKU: {prod?.code} • Available: {prod?.stockLevel}</span>
                        </div>
                        <div className="text-right">
                          <span className="font-bold text-gray-800">{line.quantity} Box</span>
                          <span className="text-[10px] text-indigo-600 font-semibold block mt-0.5">@ ${line.unitPrice}/box</span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Financial Rollup */}
                <div className="p-4 bg-indigo-50/50 border border-indigo-100/60 rounded-xl space-y-2 text-xs">
                  <div className="flex justify-between text-gray-500">
                    <span>Sales Subtotal</span>
                    <span>${(selectedOrder.totalAmount / (1 + selectedOrder.taxRate / 100)).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-gray-500">
                    <span>Sales Tax ({selectedOrder.taxRate}%)</span>
                    <span>${(selectedOrder.totalAmount - (selectedOrder.totalAmount / (1 + selectedOrder.taxRate / 100))).toFixed(2)}</span>
                  </div>
                  <div className="border-t border-indigo-100 pt-2.5 flex justify-between font-bold text-indigo-700 text-sm">
                    <span>Contract Value</span>
                    <span>${selectedOrder.totalAmount.toLocaleString()}</span>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="space-y-2.5">
                  {selectedOrder.status === "draft" && (
                    <button
                      onClick={handleConfirmOrder}
                      className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl flex items-center justify-center gap-2 transition-all shadow-md"
                    >
                      <CheckCircle className="w-4 h-4" />
                      Approve Sales Contract
                    </button>
                  )}

                  {selectedOrder.status === "confirmed" && (
                    <button
                      onClick={handleShipOrder}
                      className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl flex items-center justify-center gap-2 transition-all shadow-md"
                    >
                      <Truck className="w-4 h-4" />
                      Ship & Fulfill Order
                    </button>
                  )}
                </div>
              </>
            ) : (
              <div className="text-center text-gray-400 p-8 flex flex-col items-center justify-center gap-2">
                <BadgeDollarSign className="w-12 h-12 text-gray-200" />
                <p className="text-xs font-semibold">No Sales Order selected</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: PRICE LISTS MANAGEMENT VIEW */}
      {subTab === "pricelists" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          
          {/* Left / Middle: Price Lists Hierarchy */}
          <div className="lg:col-span-2 bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="font-bold text-gray-900">Registered Price Lists</h3>
                <p className="text-xs text-gray-400">Manage contractual wholesale price brackets</p>
              </div>
              <button
                onClick={() => {
                  setEditingPL(null);
                  setPlName("");
                  setPlValidFrom(new Date().toISOString().split("T")[0]);
                  setPlValidTo("");
                  setPlIsDefault(false);
                  setPlIsActive(true);
                  setShowPLModal(true);
                  setError("");
                  setSuccess("");
                }}
                className="flex items-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition-all self-start"
              >
                <Plus className="w-3.5 h-3.5" />
                Create Price List
              </button>
            </div>

            {/* Search filter bar */}
            <div className="relative">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
              <input
                type="text"
                value={plSearch}
                onChange={(e) => setPlSearch(e.target.value)}
                placeholder="Search Price Lists by name..."
                className="w-full pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              />
            </div>

            {/* Price Lists Table */}
            <div className="overflow-x-auto border border-gray-100 rounded-xl">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100 text-[10px] text-gray-400 font-bold uppercase tracking-wider">
                    <th className="py-3 px-4">Price List Name</th>
                    <th className="py-3 px-4 text-center">Validity Range</th>
                    <th className="py-3 px-4 text-center">Default Status</th>
                    <th className="py-3 px-4 text-center">Active Status</th>
                    <th className="py-3 px-4 text-center">Assigned Items</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50 text-xs">
                  {filteredPriceLists.map(pl => {
                    const isSelected = selectedPL?.id === pl.id;
                    return (
                      <tr 
                        key={pl.id} 
                        className={`hover:bg-gray-50/80 transition-colors cursor-pointer ${isSelected ? "bg-indigo-50/20" : ""}`}
                        onClick={() => { setSelectedPL(pl); setError(""); setSuccess(""); }}
                      >
                        <td className="py-3 px-4 font-semibold text-gray-900">
                          {pl.name}
                        </td>
                        <td className="py-3 px-4 text-center text-gray-500">
                          <span className="font-mono">{pl.validFrom}</span>
                          <span className="mx-1 text-gray-300">→</span>
                          <span className="font-mono">{pl.validTo || "Open-ended"}</span>
                        </td>
                        <td className="py-3 px-4 text-center">
                          {pl.isDefault ? (
                            <span className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100">
                              Tenant Default
                            </span>
                          ) : (
                            <span className="text-gray-400 text-[10px]">—</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                            pl.isActive ? "bg-blue-50 text-blue-700 border border-blue-100" : "bg-red-50 text-red-700 border border-red-100"
                          }`}>
                            {pl.isActive ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-center font-bold text-gray-700">
                          {pl.lines ? pl.lines.length : 0} items
                        </td>
                        <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => {
                              setEditingPL(pl);
                              setPlName(pl.name);
                              setPlValidFrom(pl.validFrom);
                              setPlValidTo(pl.validTo || "");
                              setPlIsDefault(pl.isDefault);
                              setPlIsActive(pl.isActive);
                              setShowPLModal(true);
                              setError("");
                              setSuccess("");
                            }}
                            className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-gray-100 rounded-lg transition-all"
                            title="Edit Header Configurations"
                          >
                            <Settings className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                  {filteredPriceLists.length === 0 && (
                    <tr>
                      <td colSpan={6} className="text-center p-8 text-gray-400 italic">No price lists matching search criteria.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Column: Price List Detail Page (Lines management) */}
          <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-6">
            {selectedPL ? (
              <>
                <div className="border-b border-gray-100 pb-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                      selectedPL.isActive ? "bg-blue-50 text-blue-700 border" : "bg-red-50 text-red-700 border"
                    }`}>
                      {selectedPL.isActive ? "Active Structure" : "Deactivated Structure"}
                    </span>
                    {selectedPL.isDefault && (
                      <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">Default fallback</span>
                    )}
                  </div>
                  <h3 className="text-base font-extrabold text-gray-900">{selectedPL.name}</h3>
                  <div className="flex items-center gap-1 text-[11px] text-gray-400 font-medium">
                    <Calendar className="w-3 h-3" />
                    <span>Valid: {selectedPL.validFrom} to {selectedPL.validTo || "Open-ended"}</span>
                  </div>
                </div>

                {/* Price Lines Section */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Product Pricing Lines</h4>
                    <button
                      onClick={() => {
                        setLineProductId("");
                        setLineUnitPrice("");
                        setShowLineModal(true);
                        setError("");
                        setSuccess("");
                      }}
                      className="flex items-center gap-1 text-xs font-bold text-indigo-600 hover:text-indigo-500 transition-colors"
                    >
                      <Plus className="w-3 h-3" /> Add Product
                    </button>
                  </div>

                  <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                    {selectedPL.lines && selectedPL.lines.map((line: any) => {
                      const prod = materials.find(m => m.id === line.productId);
                      return (
                        <div key={line.id} className="p-3 bg-gray-50 rounded-xl border border-gray-100 flex items-center justify-between gap-4">
                          <div className="min-w-0">
                            <span className="font-semibold text-gray-800 text-xs truncate block">{prod?.name || "Unknown variant"}</span>
                            <span className="text-[9px] text-gray-400 block mt-0.5">SKU: {prod?.code} • Cat: {prod?.category}</span>
                          </div>
                          
                          <div className="flex items-center gap-2 shrink-0">
                            <div className="relative rounded-lg shadow-sm w-24">
                              <div className="absolute inset-y-0 left-0 pl-1.5 flex items-center pointer-events-none">
                                <span className="text-[10px] text-gray-400">$</span>
                              </div>
                              <input
                                type="number"
                                value={line.unitPrice}
                                onChange={(e) => handleUpdatePLLinePrice(line.productId, e.target.value)}
                                className="w-full pl-4 pr-1 py-1 text-xs bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-indigo-500 font-bold text-gray-800"
                              />
                            </div>
                            
                            <button
                              onClick={() => handleDeletePLLine(line.productId)}
                              className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
                              title="Delete price entry"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                    {(!selectedPL.lines || selectedPL.lines.length === 0) && (
                      <div className="text-center p-6 bg-gray-50 rounded-xl border border-dashed border-gray-200 text-gray-400 text-xs">
                        No product lines mapped. Click "Add Product" to configure.
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center text-gray-400 p-8 flex flex-col items-center justify-center gap-2">
                <Info className="w-12 h-12 text-gray-200" />
                <p className="text-xs font-semibold">Select a Price List from the table to manage price lines</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODALS SECTION */}

      {/* Onboard / Edit Client Modal */}
      {showClientModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-gray-100 space-y-6">
            <div>
              <h3 className="text-lg font-bold text-gray-900">{editingClient ? "Modify Client Account" : "Onboard Sales Client"}</h3>
              <p className="text-xs text-gray-400 mt-1">Specify risk exposure limits and pricing agreements</p>
            </div>
            <form onSubmit={handleCreateOrUpdateClient} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Client Company Name</label>
                <input
                  type="text"
                  required
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  placeholder="e.g. CarePlus Distributors"
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Corporate Email</label>
                <input
                  type="email"
                  required
                  value={clientEmail}
                  onChange={(e) => setClientEmail(e.target.value)}
                  placeholder="orders@careplus.com"
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Credit Line Limit ($)</label>
                  <input
                    type="number"
                    required
                    value={creditLimit}
                    onChange={(e) => setCreditLimit(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Default Price List</label>
                  <select
                    value={clientDefaultPL}
                    onChange={(e) => setClientDefaultPL(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  >
                    <option value="__none__">-- Catalog Fallback --</option>
                    {priceLists.filter(p => p.isActive).map(pl => (
                      <option key={pl.id} value={pl.id}>{pl.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowClientModal(false); setEditingClient(null); }}
                  className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-semibold hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold"
                >
                  {editingClient ? "Save Updates" : "Onboard Customer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* New Sales Order Modal */}
      {showOrderModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-gray-100 space-y-6">
            <div>
              <h3 className="text-lg font-bold text-gray-900">Draft New Sales Contract</h3>
              <p className="text-xs text-gray-400 mt-1">Automatic multi-tier price structures will resolve upon parameter selection</p>
            </div>
            <form onSubmit={handleCreateOrder} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Ordering Client</label>
                <select
                  value={orderClient}
                  onChange={(e) => setOrderClient(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                >
                  <option value="">Select account...</option>
                  {clients.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.name} (Avail: ${(c.creditLimit - c.creditUsed).toLocaleString()})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Finished SKU Variant</label>
                <select
                  value={orderProduct}
                  onChange={(e) => setOrderProduct(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                >
                  <option value="">Select variant...</option>
                  {finishedProducts.map(fp => (
                    <option key={fp.id} value={fp.id}>
                      {fp.name} ({fp.code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Order Quantity (Box)</label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={orderQty}
                    onChange={(e) => setOrderQty(e.target.value)}
                    placeholder="0"
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Unit Contract Price ($)</label>
                  <div className="relative rounded-xl shadow-sm">
                    <input
                      type="number"
                      required
                      min="0"
                      value={orderPrice}
                      onChange={(e) => setOrderPrice(e.target.value)}
                      placeholder="Pricing Engine"
                      className="w-full px-3 py-2 bg-indigo-50 font-bold text-indigo-700 border border-indigo-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                    />
                    {orderPrice && (
                      <span className="absolute right-3 top-2 text-[9px] bg-indigo-200 text-indigo-800 font-bold uppercase px-1 rounded-sm">Resolved</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Sales Tax (%)</label>
                  <input
                    type="number"
                    required
                    value={taxRate}
                    onChange={(e) => setTaxRate(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Discount ($)</label>
                  <input
                    type="number"
                    required
                    value={discount}
                    onChange={(e) => setDiscount(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Target Dispatch Date</label>
                <input
                  type="date"
                  required
                  value={deliveryDate}
                  onChange={(e) => setDeliveryDate(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              <div className="flex items-center gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowOrderModal(false)}
                  className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-semibold hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold"
                >
                  Draft Contract
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create / Edit Price List Modal */}
      {showPLModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-gray-100 space-y-6">
            <div>
              <h3 className="text-lg font-bold text-gray-900">{editingPL ? "Edit Price List Header" : "Create Price List Structure"}</h3>
              <p className="text-xs text-gray-400 mt-1">Specify pricing period validity and default assignments</p>
            </div>
            <form onSubmit={handleCreateOrUpdatePL} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Price List Name</label>
                <input
                  type="text"
                  required
                  value={plName}
                  onChange={(e) => setPlName(e.target.value)}
                  placeholder="e.g. Q3 Healthcare Wholesale Bracket"
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Valid From</label>
                  <input
                    type="date"
                    required
                    value={plValidFrom}
                    onChange={(e) => setPlValidFrom(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Valid To (Optional)</label>
                  <input
                    type="date"
                    value={plValidTo}
                    onChange={(e) => setPlValidTo(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>
              </div>

              {/* Toggles */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-xl border border-gray-100">
                  <div>
                    <span className="text-xs font-bold text-gray-800 block">Default Tenant List</span>
                    <span className="text-[10px] text-gray-400">Acts as a fallback across all standard clients</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setPlIsDefault(!plIsDefault)}
                    className="text-indigo-600"
                  >
                    {plIsDefault ? <ToggleRight className="w-8 h-8" /> : <ToggleLeft className="w-8 h-8 text-gray-300" />}
                  </button>
                </div>

                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-xl border border-gray-100">
                  <div>
                    <span className="text-xs font-bold text-gray-800 block">Structure Status</span>
                    <span className="text-[10px] text-gray-400">Can resolve prices only when set active</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setPlIsActive(!plIsActive)}
                    className="text-indigo-600"
                  >
                    {plIsActive ? <ToggleRight className="w-8 h-8" /> : <ToggleLeft className="w-8 h-8 text-gray-300" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowPLModal(false); setEditingPL(null); }}
                  className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-semibold hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold"
                >
                  Save Price List
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Price Line Item Modal */}
      {showLineModal && selectedPL && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-gray-100 space-y-6">
            <div>
              <h3 className="text-lg font-bold text-gray-900">Map Product Pricing</h3>
              <p className="text-xs text-gray-400 mt-1">Configure pricing entry inside '{selectedPL.name}'</p>
            </div>
            <form onSubmit={handleAddPLLine} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Finished Good Product</label>
                <select
                  required
                  value={lineProductId}
                  onChange={(e) => {
                    const val = e.target.value;
                    setLineProductId(val);
                    const prod = finishedProducts.find(m => m.id === val);
                    if (prod && prod.sellingPrice) {
                      setLineUnitPrice(String(prod.sellingPrice));
                    } else {
                      setLineUnitPrice("");
                    }
                  }}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                >
                  <option value="">Select product variant...</option>
                  {finishedProducts.map(fp => (
                    <option key={fp.id} value={fp.id}>{fp.name} ({fp.code})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Wholesale Selling Price ($)</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  min="0"
                  value={lineUnitPrice}
                  onChange={(e) => setLineUnitPrice(e.target.value)}
                  placeholder="0.00"
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              <div className="flex items-center gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowLineModal(false)}
                  className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-semibold hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold"
                >
                  Attach to Price List
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
