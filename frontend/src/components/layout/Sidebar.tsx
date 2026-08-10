import { useState } from "react"
import { Link, useLocation } from "react-router-dom"
import { ChevronRight, PanelLeftClose, PanelLeftOpen } from "lucide-react"
import { useUIStore } from "@/app/store/uiStore"
import { useTenantStore } from "@/app/store/tenantStore"
import { usePermissions } from "@/hooks/usePermissions"
import { getVisibleNavItems, type NavItem } from "@/lib/constants"
import { normalizeRole } from "@/lib/roles.config"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { useIsPlatformAdmin } from "@/hooks/useIsPlatformAdmin"

export function Sidebar() {
  const { isSidebarOpen, toggleSidebar, setSidebarOpen } = useUIStore()
  const { name: tenantName } = useTenantStore()
  const { role } = usePermissions()
  const isPlatformAdmin = useIsPlatformAdmin()
  const location = useLocation()
  const [expandedState, setExpandedState] = useState<Record<string, boolean>>({})

  const normalizedRole = normalizeRole(role)
  const visibleNavItems = getVisibleNavItems(normalizedRole)

  const isNavItemActive = (item: NavItem) => {
    if (item.href === "/") return location.pathname === "/"
    return location.pathname === item.href || location.pathname.startsWith(`${item.href}/`)
  }

  const getNavAccent = (item: NavItem) => {
    if (item.href.startsWith("/finance")) return "from-blue-500 to-indigo-600"
    if (item.href.startsWith("/reports")) return "from-violet-500 to-fuchsia-600"
    if (item.href.startsWith("/inventory")) return "from-emerald-500 to-green-600"
    return "from-blue-500 to-indigo-600"
  }

  const getIconShellClass = (item: NavItem, active: boolean, contextual = false, compact = false) =>
    cn(
      "flex shrink-0 items-center justify-center rounded-lg transition-all duration-200 group-hover:scale-105",
      compact ? "h-8 w-8" : "h-9 w-9",
      active
        ? `bg-gradient-to-r ${getNavAccent(item)} text-white shadow-sm`
        : contextual
          ? "bg-transparent text-slate-200"
          : "bg-transparent text-gray-400"
    )

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
          "erp-sidebar-shell fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-slate-800/80 text-slate-100 shadow-2xl transition-all duration-300 md:translate-x-0 md:shadow-none",
          isSidebarOpen ? "translate-x-0 md:w-72" : "-translate-x-full md:w-20"
        )}
      >
        <div className="flex h-20 items-center border-b border-slate-800 px-4">
          {isSidebarOpen ? (
            <div className="flex w-full items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-blue-300/80">
                  MedTrack ERP
                </p>
                <p className="truncate pt-1 text-lg font-semibold text-white">
                  {tenantName || "Factory Workspace"}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                aria-label="Collapse sidebar"
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
                aria-label="Expand sidebar"
                className="rounded-xl text-slate-300 hover:bg-slate-800 hover:text-white"
              >
                <PanelLeftOpen className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        <nav aria-label="Main navigation" className="erp-dark-scrollbar flex-1 space-y-1.5 overflow-y-auto px-3 py-4 pr-2">
          {visibleNavItems.map((item) => {
            const childItems = item.children ?? []
            const hasChildren = childItems.length > 0
            const activeChild = childItems.find((child) => isNavItemActive(child))
            const isActive = isNavItemActive(item) || childItems.some(isNavItemActive)
            const isDirectActive = isNavItemActive(item) && !activeChild
            const isContextActive = Boolean(activeChild) || isDirectActive

            if (hasChildren && isSidebarOpen) {
              const isExpanded = expandedState[item.title] !== undefined ? expandedState[item.title] : isContextActive

              return (
                <div key={item.href} className="space-y-1">
                  <div
                    onClick={(e) => {
                      e.preventDefault()
                      setExpandedState(prev => ({ ...prev, [item.title]: !isExpanded }))
                    }}
                    className={cn(
                      "group flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-medium transition-all duration-200 cursor-pointer",
                      isContextActive
                        ? "bg-white/5 text-white shadow-sm"
                        : "text-slate-400 hover:bg-white/5 hover:text-white",
                      "gap-3"
                    )}
                  >
                    <span className={getIconShellClass(item, isDirectActive, Boolean(activeChild))}>
                      <item.icon className="h-5 w-5" />
                    </span>
                    <span className="truncate flex-1 select-none">{item.title}</span>
                    <ChevronRight 
                      className={cn(
                        "ml-auto h-4 w-4 transition-transform duration-200", 
                        isContextActive ? "text-white/60" : "text-slate-500 group-hover:text-white/60",
                        isExpanded ? "rotate-90" : ""
                      )} 
                    />
                  </div>

                  <div 
                    className={cn(
                      "ml-6 border-l border-white/10 pl-3 transition-all duration-300 overflow-hidden",
                      isExpanded ? "max-h-[500px] opacity-100 py-1 space-y-1" : "max-h-0 opacity-0 py-0"
                    )}
                  >
                    {childItems.map((child) => {
                      const isChildActive = isNavItemActive(child)

                      return (
                        <Link
                          key={child.href}
                          to={child.href}
                          onClick={closeOnMobile}
                          aria-current={isChildActive ? "page" : undefined}
                          className={cn(
                            "group flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium transition-all duration-200",
                            isChildActive
                              ? "bg-white/5 text-white shadow-sm"
                              : "text-slate-400 hover:bg-white/5 hover:text-white"
                          )}
                        >
                          <span className={getIconShellClass(child, isChildActive, false, true)}>
                            <child.icon className="h-4 w-4" />
                          </span>
                          <span className="truncate">{child.title}</span>
                        </Link>
                      )
                    })}
                  </div>
                </div>
              )
            }

            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={closeOnMobile}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "group flex items-center rounded-2xl px-3 py-3 text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-white/5 text-white shadow-sm"
                    : "text-slate-400 hover:bg-white/5 hover:text-white",
                  isSidebarOpen ? "gap-3" : "justify-center px-0"
                )}
                title={!isSidebarOpen ? item.title : undefined}
              >
                <span className={getIconShellClass(item, isActive)}>
                  <item.icon className="h-5 w-5" />
                </span>
                {isSidebarOpen && (
                  <>
                    <span className="truncate">{item.title}</span>
                    {isActive && <ChevronRight className="ml-auto h-4 w-4 text-white/60" />}
                  </>
                )}
              </Link>
            )
          })}
        </nav>

        <div className={cn("border-t border-slate-800 px-4 py-4 space-y-4", !isSidebarOpen && "px-2")}>
          {isPlatformAdmin && (
            <Link to="/platform">
              <Button variant="outline" className={cn("w-full bg-slate-900 border-fuchsia-500/30 text-fuchsia-400 hover:bg-fuchsia-500/10 hover:text-fuchsia-300", !isSidebarOpen && "px-0")}>
                {isSidebarOpen ? "MedTrack Platform" : "M"}
              </Button>
            </Link>
          )}
          {isSidebarOpen ? (
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/70 px-4 py-3 backdrop-blur-sm">
              <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Role</p>
              <div className="mt-2 flex items-center justify-between gap-3">
                <span className="truncate text-sm font-medium text-slate-200">{role}</span>
                <span className="rounded-full border border-slate-700 px-2 py-1 text-[11px] text-slate-400">
                  v0.1.0
                </span>
              </div>
            </div>
          ) : (
            <div className="flex justify-center">
              <span className="rounded-full border border-slate-800 px-2 py-1 text-[11px] text-slate-500">
                v0.1.0
              </span>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
