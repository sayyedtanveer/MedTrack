import { Link, useLocation } from "react-router-dom"
import { ShieldCheck, Users, LayoutDashboard, Settings, Activity, Building, PanelLeftClose, PanelLeftOpen } from "lucide-react"
import { useUIStore } from "@/app/store/uiStore"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

const platformNavItems = [
  { title: "Dashboard", href: "/platform/dashboard", icon: LayoutDashboard },
  { title: "Tenant Management", href: "/platform/tenants", icon: Building },
  { title: "Audit Logs", href: "/platform/audit", icon: ShieldCheck, disabled: true },
  { title: "Billing", href: "/platform/billing", icon: Users, disabled: true },
  { title: "Analytics", href: "/platform/analytics", icon: Activity, disabled: true },
  { title: "Settings", href: "/platform/settings", icon: Settings, disabled: true },
]

export function PlatformSidebar() {
  const { isSidebarOpen, toggleSidebar, setSidebarOpen } = useUIStore()
  const location = useLocation()

  const closeOnMobile = () => {
    if (typeof window !== "undefined" && window.innerWidth < 768) {
      setSidebarOpen(false)
    }
  }

  return (
    <>
      <button
        type="button"
        aria-label="Close navigation"
        onClick={() => setSidebarOpen(false)}
        className={cn(
          "fixed inset-0 z-30 bg-slate-950/45 backdrop-blur-sm transition-opacity md:hidden",
          isSidebarOpen ? "opacity-100" : "pointer-events-none opacity-0"
        )}
      />

      <aside
        className={cn(
          "erp-sidebar-shell fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-slate-800/80 text-slate-100 shadow-2xl transition-all duration-300 md:translate-x-0 md:shadow-none bg-slate-950",
          isSidebarOpen ? "translate-x-0 md:w-72" : "-translate-x-full md:w-20"
        )}
      >
        <div className="flex h-20 items-center border-b border-slate-800 px-4">
          {isSidebarOpen ? (
            <div className="flex w-full items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-fuchsia-400">
                  Platform Admin
                </p>
                <p className="truncate pt-1 text-lg font-semibold text-white">
                  MedTrack HQ
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                className="shrink-0 rounded-xl text-slate-300 hover:bg-slate-800 hover:text-white"
              >
                <PanelLeftClose className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <div className="flex w-full justify-center">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                className="rounded-xl text-slate-300 hover:bg-slate-800 hover:text-white"
              >
                <PanelLeftOpen className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        <nav aria-label="Platform navigation" className="erp-dark-scrollbar flex-1 space-y-1.5 overflow-y-auto px-3 py-4">
          {platformNavItems.map((item) => {
            const isActive = location.pathname.startsWith(item.href)
            const iconClass = cn(
              "flex shrink-0 items-center justify-center rounded-lg transition-all duration-200 h-9 w-9",
              isActive ? "bg-gradient-to-r from-fuchsia-500 to-purple-600 text-white shadow-sm" : "bg-transparent text-slate-400 group-hover:scale-105"
            )

            if (item.disabled) {
              return (
                <div
                  key={item.href}
                  className={cn(
                    "group flex items-center rounded-2xl px-3 py-3 text-sm font-medium opacity-50 cursor-not-allowed",
                    isSidebarOpen ? "gap-3" : "justify-center px-0"
                  )}
                  title={!isSidebarOpen ? `${item.title} (Coming Soon)` : undefined}
                >
                  <span className={iconClass}>
                    <item.icon className="h-5 w-5" />
                  </span>
                  {isSidebarOpen && <span>{item.title} <span className="text-[10px] ml-2 bg-slate-800 px-1.5 py-0.5 rounded">Soon</span></span>}
                </div>
              )
            }

            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={closeOnMobile}
                className={cn(
                  "group flex items-center rounded-2xl px-3 py-3 text-sm font-medium transition-all duration-200",
                  isActive ? "bg-white/5 text-white shadow-sm" : "text-slate-400 hover:bg-white/5 hover:text-white",
                  isSidebarOpen ? "gap-3" : "justify-center px-0"
                )}
                title={!isSidebarOpen ? item.title : undefined}
              >
                <span className={iconClass}>
                  <item.icon className="h-5 w-5" />
                </span>
                {isSidebarOpen && <span className="truncate">{item.title}</span>}
              </Link>
            )
          })}
        </nav>
      </aside>
    </>
  )
}
