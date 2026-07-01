import {
  Banknote,
  Package,
  ShoppingCart,
  LayoutDashboard,
  Users,
  Settings,
  ClipboardList,
  Factory,
  BarChart3,
  FileText,
  Layers,
  PackageSearch,
  Network,
  ReceiptText,
  Truck,
  ShieldAlert,
  History,
  Wrench,
  LucideIcon,
} from "lucide-react"
import { UserRole, getRolesForModule } from "@/lib/roles.config"

export type NavItem = {
  title: string
  href: string
  icon: LucideIcon
  roles: UserRole[]
  children?: NavItem[]
}

const FINANCE_FULL_ACCESS_ROLES = [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]
const FINANCE_CUSTOMER_INVOICE_ROLES = [...FINANCE_FULL_ACCESS_ROLES, UserRole.SALES]

export const NAV_ITEMS: NavItem[] = [
  {
    title: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
    roles: getRolesForModule("dashboard"),
  },
  {
    title: "System Map",
    href: "/system-map",
    icon: Network,
    roles: getRolesForModule("systemMap"),
  },
  {
    title: "Products",
    href: "/products",
    icon: PackageSearch,
    roles: getRolesForModule("products"),
  },
  {
    title: "Bill of Materials",
    href: "/bom/list",
    icon: Layers,
    roles: getRolesForModule("bom"),
  },
  {
    title: "Manufacturing",
    href: "/manufacturing",
    icon: Factory,
    roles: getRolesForModule("manufacturing"),
    children: [
      {
        title: "Operations Master",
        href: "/operations",
        icon: Wrench,
        roles: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER],
      },
    ],
  },
  {
    title: "Inventory",
    href: "/inventory",
    icon: Package,
    roles: getRolesForModule("inventory"),
  },
  {
    title: "Work Orders",
    href: "/work-orders",
    icon: ClipboardList,
    roles: getRolesForModule("workOrders"),
  },
  {
    title: "Procurement",
    href: "/procurement",
    icon: Truck,
    roles: getRolesForModule("procurement"),
  },
  {
    title: "Capacity & MRP",
    href: "/mrp",
    icon: BarChart3,
    roles: [
      UserRole.ADMIN,
      UserRole.TENANT_ADMIN,
      UserRole.MANAGER,
      UserRole.PLANNER,
      UserRole.STOREKEEPER,
      UserRole.OPERATOR,
    ],
  },
  {
    title: "Quality & QC",
    href: "/procurement/quality",
    icon: ShieldAlert,
    roles: getRolesForModule("quality"),
  },
  {
    title: "Sales",
    href: "/sales",
    icon: ShoppingCart,
    roles: getRolesForModule("sales"),
  },
  {
    title: "Finance",
    href: "/finance",
    icon: Banknote,
    roles: FINANCE_FULL_ACCESS_ROLES,
    children: [
      {
        title: "Dashboard",
        href: "/finance",
        icon: LayoutDashboard,
        roles: FINANCE_FULL_ACCESS_ROLES,
      },
      {
        title: "Customer Invoices",
        href: "/finance/invoices",
        icon: ReceiptText,
        roles: FINANCE_CUSTOMER_INVOICE_ROLES,
      },
      {
        title: "Supplier Invoices",
        href: "/finance/supplier-invoices",
        icon: FileText,
        roles: FINANCE_FULL_ACCESS_ROLES,
      },
      {
        title: "Settings",
        href: "/finance/settings",
        icon: Settings,
        roles: FINANCE_FULL_ACCESS_ROLES,
      },
    ],
  },
  {
    title: "Shop floor",
    href: "/shop-floor",
    icon: Factory,
    roles: getRolesForModule("shopFloor"),
  },
  {
    title: "Reports",
    href: "/reports",
    icon: BarChart3,
    roles: getRolesForModule("reports"),
  },
  {
    title: "Activity Log",
    href: "/activity-log",
    icon: History,
    roles: getRolesForModule("auditLogs"),
  },
  {
    title: "Supplier portal",
    href: "/supplier-portal",
    icon: Truck,
    roles: getRolesForModule("supplierPortal"),
  },
  {
    title: "Users",
    href: "/users",
    icon: Users,
    roles: getRolesForModule("users"),
  },
  {
    title: "Settings",
    href: "/settings",
    icon: Settings,
    roles: getRolesForModule("settings"),
    children: [
      {
        title: "Number Series",
        href: "/settings/business-config/number-series",
        icon: Settings,
        roles: getRolesForModule("settings"),
      },
    ],
  },
]

export function getVisibleNavItems(role: UserRole | undefined): NavItem[] {
  if (!role) return []

  return NAV_ITEMS.reduce<NavItem[]>((items, item) => {
    const children = item.children?.filter((child) => child.roles.includes(role))
    const canViewItem = item.roles.includes(role)

    if (canViewItem || children?.length) {
      items.push({
        ...item,
        href: canViewItem ? item.href : children?.[0]?.href ?? item.href,
        children,
      })
    }

    return items
  }, [])
}

export function flattenNavItems(items: NavItem[]): NavItem[] {
  return items.flatMap((item) => [item, ...(item.children ? flattenNavItems(item.children) : [])])
}

export const ROLE_LABELS: Record<string, string> = {
  ADMIN: "Administrator",
  TENANT_ADMIN: "Tenant admin",
  MANAGER: "Manager",
  PLANNER: "Planner",
  STOREKEEPER: "Storekeeper",
  OPERATOR: "Operator",
  QC: "Quality",
  SALES: "Sales",
  ACCOUNTANT: "Accountant",
  WORKER: "Worker",
  CLIENT: "Client",
  SUPPLIER: "Supplier",
  VIEWER: "Viewer",
}

export const ROUTE_PATHS = {
  LOGIN: "/login",
  REGISTER: "/register",
  DASHBOARD: "/",
  PRODUCTS: "/products",
  BOM: "/bom/list",
  INVENTORY: "/inventory/materials",
  MATERIALS: "/inventory/materials",
  TRANSACTIONS: "/inventory/transactions",
  USERS: "/users",
}
