import React from "react";
import { 
  LayoutDashboard, 
  Package, 
  FileSpreadsheet, 
  Cpu, 
  BadgeDollarSign, 
  LogOut, 
  Building2, 
  UserCircle 
} from "lucide-react";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  user: any;
  tenant: any;
  onLogout: () => void;
}

export default function Sidebar({ activeTab, setActiveTab, user, tenant, onLogout }: SidebarProps) {
  const menuItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "inventory", label: "Materials Inventory", icon: Package },
    { id: "bom", label: "BOM Workspace", icon: FileSpreadsheet },
    { id: "workorders", label: "Work Orders Hub", icon: Cpu },
    { id: "sales", label: "Sales & Clients", icon: BadgeDollarSign },
  ];

  return (
    <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col h-screen text-gray-400 select-none shrink-0">
      {/* Brand Header */}
      <div className="p-6 border-b border-gray-800 flex items-center gap-3">
        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-indigo-600/15">
          M
        </div>
        <div>
          <h2 className="text-white font-bold tracking-tight text-sm">MedTrack ERP</h2>
          <span className="text-[10px] text-indigo-400 font-medium tracking-wider uppercase block">
            {tenant?.name || "Manufacturing"}
          </span>
        </div>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                isActive 
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/10" 
                  : "hover:bg-gray-800/60 hover:text-gray-200"
              }`}
            >
              <Icon className={`w-5 h-5 shrink-0 ${isActive ? "text-white" : "text-gray-500"}`} />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* User Info & Footer */}
      <div className="p-4 border-t border-gray-800 space-y-4">
        <div className="flex items-center gap-3 px-2">
          <div className="w-9 h-9 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center text-gray-300">
            <UserCircle className="w-5 h-5" />
          </div>
          <div className="overflow-hidden">
            <h4 className="text-white text-xs font-semibold truncate">{user?.name}</h4>
            <span className="text-[10px] text-gray-500 block truncate">{user?.role}</span>
          </div>
        </div>

        <button
          onClick={onLogout}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 border border-gray-800 hover:border-gray-700 hover:bg-gray-800 text-gray-400 hover:text-red-400 rounded-xl text-xs font-semibold transition-all"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
