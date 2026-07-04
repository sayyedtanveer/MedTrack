import { type FormEvent, useMemo, useState } from "react"
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom"
import { Bell, CreditCard, Headset, LayoutDashboard, LogOut, Menu, Package2, PlusCircle, ReceiptText, RefreshCcw, UserCircle2, X } from "lucide-react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useAuthStore } from "@/app/store/authStore"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Toaster } from "@/components/ui/toaster"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"
import { type ClientNotification, clientService } from "../services/client.service"

const navItems = [
  { label: "Dashboard", to: "/client", icon: LayoutDashboard },
  { label: "My Orders", to: "/client/orders", icon: Package2 },
  { label: "New Order", to: "/client/orders/new", icon: PlusCircle },
  { label: "Invoices", to: "/client/invoices", icon: ReceiptText },
  { label: "Reorder", to: "/client/reorder", icon: RefreshCcw },
  { label: "Credit Status", to: "/client/credit", icon: CreditCard },
  { label: "Profile", to: "/client/profile", icon: UserCircle2 },
  { label: "Support", to: "/client/support", icon: Headset },
]

const mobileNavItems = [navItems[0], navItems[1], navItems[3], navItems[6]]

export default function ClientLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [search, setSearch] = useState("")
  const { user, logout } = useAuthStore()

  const notificationsQuery = useQuery({
    queryKey: ["client-notifications"],
    queryFn: () => clientService.listNotifications({ page: 1, page_size: 8 }),
    refetchInterval: 30000,
  })

  const markNotificationRead = useMutation({
    mutationFn: (id: string) => clientService.markNotificationRead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["client-notifications"] }),
  })

  const unreadCount = notificationsQuery.data?.unread_count ?? 0

  const topBarTitle = useMemo(() => {
    const active = navItems.find((item) => location.pathname === item.to || location.pathname.startsWith(`${item.to}/`))
    return active?.label ?? "Client Portal"
  }, [location.pathname])

  const handleLogout = async () => {
    try {
      await clientService.logout()
    } catch {
      // Client-side logout should still proceed even if the API session call fails.
    }
    logout()
    navigate("/client/login", { replace: true })
  }

  const handleSearchSubmit = (event: FormEvent) => {
    event.preventDefault()
    navigate(`/client/orders${search ? `?search=${encodeURIComponent(search)}` : ""}`)
  }

  const notificationPath = (referenceType?: string | null, referenceId?: string | null) => {
    if (!referenceType || !referenceId) return "/client"
    const type = referenceType.toLowerCase()
    if (type === "sales_order") return `/client/orders/${referenceId}`
    if (type === "invoice") return "/client/invoices"
    return "/client"
  }

  const openNotification = (item: ClientNotification) => {
    if (!item.is_read) {
      markNotificationRead.mutate(item.id)
    }
    navigate(notificationPath(item.reference_type, item.reference_id))
  }

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-[1600px]">
        {isSidebarOpen && (
          <button
            type="button"
            aria-label="Close navigation"
            className="fixed inset-0 z-30 bg-slate-950/45 backdrop-blur-[1px] md:hidden"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}
        <aside
          className={cn(
            "erp-sidebar-shell fixed inset-y-0 left-0 z-40 flex w-[86vw] max-w-[320px] flex-col border-r border-slate-800/80 p-5 text-slate-100 shadow-2xl md:static md:w-72 md:max-w-none md:translate-x-0 md:p-6",
            isSidebarOpen ? "translate-x-0" : "-translate-x-full",
            "transition-transform duration-300"
          )}
        >
          <div className="mb-8 flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.25em] text-blue-300/80">MedTrack</p>
              <h1 className="text-xl font-semibold text-white">Client Portal</h1>
            </div>
            <Button variant="ghost" size="icon" className="md:hidden text-slate-300 hover:bg-slate-800 hover:text-white" onClick={() => setIsSidebarOpen(false)} aria-label="Close menu">
              <X className="h-4 w-4" />
            </Button>
          </div>

          <nav className="erp-dark-scrollbar flex-1 space-y-2 overflow-y-auto pr-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/client"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition-colors",
                    isActive ? "bg-slate-800 text-white" : "text-slate-400 hover:bg-slate-900 hover:text-white"
                  )
                }
                onClick={() => setIsSidebarOpen(false)}
              >
                <item.icon className="h-4 w-4" />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="mt-6 rounded-3xl border border-slate-800/80 bg-slate-900/72 p-5 text-white backdrop-blur-sm">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Signed In</p>
            <p className="mt-2 text-lg font-semibold">{user?.first_name} {user?.last_name}</p>
            <p className="text-sm text-slate-300">{user?.email}</p>
            <Button variant="secondary" className="mt-5 w-full rounded-full md:hidden" onClick={() => void handleLogout()}>
              <LogOut className="mr-2 h-4 w-4" />
              Log Out
            </Button>
          </div>
        </aside>

        <div className="flex min-h-screen flex-1 flex-col">
          <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 px-3 py-3 backdrop-blur sm:px-4 md:px-8 md:py-4">
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setIsSidebarOpen(true)} aria-label="Open menu">
                <Menu className="h-5 w-5" />
              </Button>
              <div className="min-w-0 flex-1">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{topBarTitle}</p>
                <h2 className="truncate text-base font-semibold sm:text-lg">Self-service order and invoice tracking</h2>
              </div>

              <form onSubmit={handleSearchSubmit} className="hidden w-full max-w-sm lg:block">
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search order number"
                  className="rounded-full border-slate-200 bg-slate-50"
                />
              </form>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="icon" className="relative rounded-full border-slate-200 bg-white" aria-label="Notifications">
                    <Bell className="h-4 w-4" />
                    {unreadCount > 0 && (
                      <Badge className="absolute -right-1 -top-1 h-5 min-w-5 rounded-full px-1 text-[10px]">{unreadCount}</Badge>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-80">
                  <DropdownMenuLabel>Notifications</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {notificationsQuery.data?.items?.length ? (
                    notificationsQuery.data.items.map((item) => (
                      <DropdownMenuItem key={item.id} className="block cursor-pointer py-3" onClick={() => openNotification(item)}>
                        <p className="font-medium">{item.title}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{item.message}</p>
                      </DropdownMenuItem>
                    ))
                  ) : (
                    <DropdownMenuItem disabled>No notifications yet</DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>

              <Button variant="outline" className="hidden rounded-full md:inline-flex" onClick={() => void handleLogout()}>
                <LogOut className="mr-2 h-4 w-4" />
                Log Out
              </Button>
            </div>
          </header>

          <main className="flex-1 px-3 py-5 pb-24 sm:px-4 sm:py-6 md:px-8 md:pb-8">
            <Outlet />
          </main>

          <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white/95 px-3 py-2 backdrop-blur md:hidden">
            <div className="grid grid-cols-4 gap-2">
              {mobileNavItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/client"}
                  className={({ isActive }) =>
                    cn(
                      "flex flex-col items-center gap-1 rounded-2xl px-2 py-2 text-[11px]",
                      isActive ? "bg-slate-900 text-white" : "text-slate-500"
                    )
                  }
                >
                  <item.icon className="h-4 w-4" />
                  <span>{item.label.replace("My ", "")}</span>
                </NavLink>
              ))}
            </div>
          </nav>
        </div>
      </div>
      <Toaster />
    </div>
  )
}
