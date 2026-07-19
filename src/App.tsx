import React, { useState, useEffect } from "react";
import Auth from "./components/Auth.tsx";
import Sidebar from "./components/Sidebar.tsx";
import Dashboard from "./components/Dashboard.tsx";
import Inventory from "./components/Inventory.tsx";
import BOMWorkspace from "./components/BOMWorkspace.tsx";
import WorkOrders from "./components/WorkOrders.tsx";
import SalesModule from "./components/SalesModule.tsx";

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem("medtrack_token"));
  const [user, setUser] = useState<any>(null);
  const [tenant, setTenant] = useState<any>(null);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMe = async () => {
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const res = await fetch("/api/v1/auth/me", {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.ok ? await res.json() : null;
          if (data && data.user) {
            setUser(data.user);
            setTenant(data.tenant);
          } else {
            handleLogout();
          }
        } else {
          handleLogout();
        }
      } catch (err) {
        console.error("Failed to authenticate session", err);
        handleLogout();
      } finally {
        setLoading(false);
      }
    };

    fetchMe();
  }, [token]);

  const handleLoginSuccess = (usr: any, ten: any, tkn: string) => {
    localStorage.setItem("medtrack_token", tkn);
    setToken(tkn);
    setUser(usr);
    setTenant(ten);
    setActiveTab("dashboard");
  };

  const handleLogout = () => {
    localStorage.removeItem("medtrack_token");
    setToken(null);
    setUser(null);
    setTenant(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!token || !user) {
    return <Auth onLoginSuccess={handleLoginSuccess} />;
  }

  const renderActiveContent = () => {
    switch (activeTab) {
      case "dashboard":
        return <Dashboard token={token} />;
      case "inventory":
        return <Inventory token={token} />;
      case "bom":
        return <BOMWorkspace token={token} />;
      case "workorders":
        return <WorkOrders token={token} />;
      case "sales":
        return <SalesModule token={token} />;
      default:
        return <Dashboard token={token} />;
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-50 font-sans">
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        user={user} 
        tenant={tenant} 
        onLogout={handleLogout} 
      />
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        {renderActiveContent()}
      </main>
    </div>
  );
}
