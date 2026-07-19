import React, { useState, useEffect } from "react";
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  AreaChart, Area, CartesianGrid 
} from "recharts";
import { 
  Package, Cpu, BadgeDollarSign, FileSpreadsheet, 
  Activity, ArrowUpRight, TrendingUp 
} from "lucide-react";
import { Material, WorkOrder, SalesOrder, BOM } from "../types";

interface DashboardProps {
  token: string | null;
}

export default function Dashboard({ token }: DashboardProps) {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [salesOrders, setSalesOrders] = useState<SalesOrder[]>([]);
  const [boms, setBoms] = useState<BOM[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const [resMat, resWo, resSo, resBom] = await Promise.all([
          fetch("/api/v1/inventory/materials", { headers }),
          fetch("/api/v1/work-orders", { headers }),
          fetch("/api/v1/sales/orders", { headers }),
          fetch("/api/v1/boms", { headers })
        ]);

        if (resMat.ok) setMaterials(await resMat.json());
        if (resWo.ok) setWorkOrders(await resWo.json());
        if (resSo.ok) setSalesOrders(await resSo.json());
        if (resBom.ok) setBoms(await resBom.json());
      } catch (err) {
        console.error("Error loading dashboard data", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [token]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  // Calculate stats
  const totalStockItems = materials.reduce((acc, m) => acc + m.stockLevel, 0);
  const pendingWorkOrders = workOrders.filter(w => w.status !== "completed" && w.status !== "closed").length;
  const activeBomsCount = boms.filter(b => b.status === "active").length;
  
  const totalSalesRevenue = salesOrders
    .filter(so => so.status !== "cancelled")
    .reduce((acc, so) => acc + so.totalAmount, 0);

  // Prepare chart data for stock levels
  const stockChartData = materials.map(m => ({
    name: m.code,
    Stock: m.stockLevel,
    Category: m.category
  }));

  // Prepare area chart data for Work Order quantities
  const woChartData = workOrders.map(w => ({
    name: w.workOrderNumber,
    Planned: w.plannedQuantity,
    Produced: w.producedQuantity
  }));

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-8 bg-gray-50">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Enterprise Overview</h1>
          <p className="text-gray-500 text-sm">Real-time indicators and operational performance</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-xl shadow-sm border border-gray-100 text-xs text-gray-500 font-semibold">
          <Activity className="w-4 h-4 text-emerald-500 animate-pulse" />
          System Online
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Total Stock */}
        <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-50 rounded-full translate-x-12 -translate-y-12 transition-transform group-hover:scale-110 duration-500"></div>
          <div className="relative z-10 flex items-start justify-between">
            <div>
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block">Total Stock Level</span>
              <h3 className="text-3xl font-bold text-gray-900 mt-2">{totalStockItems.toLocaleString()}</h3>
              <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                <TrendingUp className="w-3 h-3 text-indigo-500" />
                Across {materials.length} Materials
              </p>
            </div>
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl">
              <Package className="w-6 h-6" />
            </div>
          </div>
        </div>

        {/* Active BOMs */}
        <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-sky-50 rounded-full translate-x-12 -translate-y-12 transition-transform group-hover:scale-110 duration-500"></div>
          <div className="relative z-10 flex items-start justify-between">
            <div>
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block">Active BOM Templates</span>
              <h3 className="text-3xl font-bold text-gray-900 mt-2">{activeBomsCount}</h3>
              <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                <ArrowUpRight className="w-3 h-3 text-sky-500" />
                Of {boms.length} Total Versions
              </p>
            </div>
            <div className="p-3 bg-sky-50 text-sky-600 rounded-xl">
              <FileSpreadsheet className="w-6 h-6" />
            </div>
          </div>
        </div>

        {/* Pending Production */}
        <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-purple-50 rounded-full translate-x-12 -translate-y-12 transition-transform group-hover:scale-110 duration-500"></div>
          <div className="relative z-10 flex items-start justify-between">
            <div>
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block">Active Work Orders</span>
              <h3 className="text-3xl font-bold text-gray-900 mt-2">{pendingWorkOrders}</h3>
              <p className="text-xs text-gray-500 mt-1">Scheduled or In Progress</p>
            </div>
            <div className="p-3 bg-purple-50 text-purple-600 rounded-xl">
              <Cpu className="w-6 h-6" />
            </div>
          </div>
        </div>

        {/* Revenue */}
        <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-50 rounded-full translate-x-12 -translate-y-12 transition-transform group-hover:scale-110 duration-500"></div>
          <div className="relative z-10 flex items-start justify-between">
            <div>
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block">Order Revenue Booked</span>
              <h3 className="text-3xl font-bold text-gray-900 mt-2">${totalSalesRevenue.toLocaleString()}</h3>
              <p className="text-xs text-gray-500 mt-1">Confirmed client bookings</p>
            </div>
            <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl">
              <BadgeDollarSign className="w-6 h-6" />
            </div>
          </div>
        </div>
      </div>

      {/* Visual Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Material Stock Levels */}
        <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-4">
          <div>
            <h3 className="text-base font-bold text-gray-900">Material Stock Balances</h3>
            <p className="text-xs text-gray-500">Current quantities registered in master inventory</p>
          </div>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stockChartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                <XAxis dataKey="name" fontSize={11} stroke="#9ca3af" />
                <YAxis fontSize={11} stroke="#9ca3af" />
                <Tooltip 
                  contentStyle={{ background: "#1f2937", border: "none", borderRadius: "12px", color: "#f3f4f6" }}
                  itemStyle={{ color: "#a5b4fc" }}
                />
                <Bar dataKey="Stock" fill="#4f46e5" radius={[6, 6, 0, 0]} maxBarSize={45} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Work Order Execution */}
        <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm space-y-4">
          <div>
            <h3 className="text-base font-bold text-gray-900">Work Order Quantities</h3>
            <p className="text-xs text-gray-500">Planned vs produced quantities by active run</p>
          </div>
          <div className="h-72 w-full">
            {woChartData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-gray-400">
                No active production lines recorded.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={woChartData}>
                  <defs>
                    <linearGradient id="colorPlanned" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorProduced" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                  <XAxis dataKey="name" fontSize={11} stroke="#9ca3af" />
                  <YAxis fontSize={11} stroke="#9ca3af" />
                  <Tooltip 
                    contentStyle={{ background: "#1f2937", border: "none", borderRadius: "12px", color: "#f3f4f6" }}
                  />
                  <Area type="monotone" dataKey="Planned" stroke="#4f46e5" strokeWidth={2} fillOpacity={1} fill="url(#colorPlanned)" />
                  <Area type="monotone" dataKey="Produced" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorProduced)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
