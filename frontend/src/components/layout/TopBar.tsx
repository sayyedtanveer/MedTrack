import { type FormEvent, useEffect, useMemo, useState } from "react"
import { formatDistanceToNow } from "date-fns"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import {
  Bell,
  CloudOff,
  CloudSync,
  Laptop,
  LogOut,
  Menu,
  Moon,
  Search,
  Settings,
  Sun,
  User as UserIcon,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/hooks/useAuth"
import { usePermissions } from "@/hooks/usePermissions"
import { financeService } from "@/services/finance.service"
import { useUIStore } from "@/app/store/uiStore"
import { flattenNavItems, getVisibleNavItems } from "@/lib/constants"
import { normalizeRole } from "@/lib/roles.config"

export function TopBar() {
  const { user, logout } = useAuth()
  const { role } = usePermissions()
  const navigate = useNavigate()
  const {
    toggleSidebar,
    theme,
    setTheme,
    pendingSyncCount,
    clearSyncQueue,
  } = useUIStore()
  const [isOffline, setIsOffline] = useState(!navigator.onLine)
  const [search, setSearch] = useState("")
  const qc = useQueryClient()

  const normalizedRole = normalizeRole(role)
  const visibleNavItems = useMemo(
    () => flattenNavItems(getVisibleNavItems(normalizedRole)),
    [normalizedRole]
  )

  const { data: notifData } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => financeService.getNotifications({ unread_only: false, page: 1, page_size: 10 }),
    refetchInterval: 30000,
  })

  const markReadMutation = useMutation({
    mutationFn: (id: string) => financeService.markRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  })

  const markAllReadMutation = useMutation({
    mutationFn: () => financeService.markAllRead(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  })

  const notificationHref = (referenceType?: string, referenceId?: string) => {
    if (!referenceType || !referenceId) return "/activity-log"
    const type = referenceType.toLowerCase()
    if (type === "sales_order") return `/sales/orders/${referenceId}`
    if (type === "invoice") return `/finance/invoices/${referenceId}`
    if (type === "purchase_order") return `/procurement/purchase-orders/${referenceId}`
    if (type === "work_order") return `/work-orders/${referenceId}`
    return "/activity-log"
  }

  const openNotification = (notification: NonNullable<typeof notifData>["items"][number]) => {
    if (!notification.is_read) {
      markReadMutation.mutate(notification.id)
    }
    navigate(notificationHref(notification.reference_type, notification.reference_id))
  }

  useEffect(() => {
    const handleOnline = () => {
      setIsOffline(false)
      if (pendingSyncCount > 0) {
        setTimeout(() => clearSyncQueue(), 1500)
      }
    }
    const handleOffline = () => setIsOffline(true)

    window.addEventListener("online", handleOnline)
    window.addEventListener("offline", handleOffline)

    return () => {
      window.removeEventListener("online", handleOnline)
      window.removeEventListener("offline", handleOffline)
    }
  }, [pendingSyncCount, clearSyncQueue])

  const handleSearchSubmit = (event: FormEvent) => {
    event.preventDefault()
    const query = search.trim().toLowerCase()
    if (!query) return

    const match = visibleNavItems.find((item) => item.title.toLowerCase().includes(query))
    if (match) {
      navigate(match.href)
      setSearch("")
    }
  }

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-20 w-full max-w-[1600px] items-center justify-between gap-3 px-3 sm:px-4 md:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <Button
            variant="outline"
            size="icon"
            onClick={toggleSidebar}
            className="shrink-0 rounded-xl border-slate-200 bg-white"
          >
            <Menu className="h-5 w-5" />
            <span className="sr-only">Toggle sidebar</span>
          </Button>

          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-blue-600">
              Operations Hub
            </p>
            <p className="truncate text-sm text-slate-500 sm:text-base">
              Premium ERP workspace for manufacturing, procurement, and finance
            </p>
          </div>
        </div>

        <div className="hidden flex-1 justify-center lg:flex">
          <form onSubmit={handleSearchSubmit} className="w-full max-w-md">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Jump to a module..."
                className="rounded-full border-slate-200 bg-slate-50 pl-9"
              />
            </div>
          </form>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          {isOffline ? (
            <Badge variant="destructive" className="hidden items-center gap-1 rounded-full sm:flex">
              <CloudOff className="h-3 w-3" />
              Offline
            </Badge>
          ) : pendingSyncCount > 0 ? (
            <Badge className="hidden items-center gap-1 rounded-full border-amber-200 bg-amber-50 text-amber-700 sm:flex">
              <CloudSync className="h-3 w-3 animate-spin" />
              Syncing {pendingSyncCount}
            </Badge>
          ) : null}

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon" className="relative rounded-full">
                <Bell className="h-5 w-5" />
                {notifData?.unread_count ? (
                  <>
                    <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-500" />
                    <span className="absolute -right-1 -top-1 flex min-h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] text-white">
                      {notifData.unread_count}
                    </span>
                  </>
                ) : null}
                <span className="sr-only">Notifications</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[22rem] overflow-hidden rounded-2xl border-slate-200 p-0">
              <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-4 py-3">
                <p className="text-sm font-semibold text-slate-900">Notifications</p>
                {notifData?.unread_count ? (
                  <button
                    onClick={() => markAllReadMutation.mutate()}
                    className="text-xs font-medium text-blue-600 hover:text-blue-700"
                  >
                    Mark all read
                  </button>
                ) : null}
              </div>
              <div className="max-h-[320px] overflow-y-auto">
                {!notifData?.items?.length ? (
                  <div className="p-5 text-center text-sm text-slate-500">No recent notifications</div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {notifData.items.map((n) => (
                      <div
                        key={n.id}
                        role="button"
                        tabIndex={0}
                        onClick={() => openNotification(n)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") openNotification(n)
                        }}
                        className={`cursor-pointer px-4 py-3 transition-colors hover:bg-slate-50 ${
                          !n.is_read ? "bg-blue-50/50" : ""
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`mt-1 h-2.5 w-2.5 rounded-full ${!n.is_read ? "bg-blue-500" : "bg-slate-200"}`} />
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-semibold text-slate-900">{n.title}</p>
                            <p className="mt-1 text-xs leading-5 text-slate-500">{n.message}</p>
                            <p className="mt-1 text-[11px] text-slate-400">
                              {formatDistanceToNow(new Date(n.sent_at), { addSuffix: true })}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </DropdownMenuContent>
          </DropdownMenu>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon" className="rounded-full bg-slate-50" aria-label="User menu">
                <UserIcon className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-60 rounded-2xl border-slate-200">
              <DropdownMenuLabel className="py-3">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-semibold leading-none text-slate-900">
                    {user?.first_name} {user?.last_name}
                  </p>
                  <p className="text-xs leading-none text-slate-500">{user?.email}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="py-2.5">
                <Settings className="mr-2 h-4 w-4" />
                <span>Settings</span>
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              <DropdownMenuLabel className="text-xs uppercase tracking-[0.18em] text-slate-500">
                Theme
              </DropdownMenuLabel>
              <DropdownMenuItem onClick={() => setTheme("light")} className="py-2.5">
                <Sun className="mr-2 h-4 w-4" />
                <span>Light</span>
                {theme === "light" && <span className="ml-auto text-xs text-blue-600">Active</span>}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTheme("dark")} className="py-2.5">
                <Moon className="mr-2 h-4 w-4" />
                <span>Dark</span>
                {theme === "dark" && <span className="ml-auto text-xs text-blue-600">Active</span>}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTheme("system")} className="py-2.5">
                <Laptop className="mr-2 h-4 w-4" />
                <span>System</span>
                {theme === "system" && <span className="ml-auto text-xs text-blue-600">Active</span>}
              </DropdownMenuItem>

              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout} className="py-2.5 text-red-600 focus:bg-red-50 focus:text-red-700">
                <LogOut className="mr-2 h-4 w-4" />
                <span>Log out</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
