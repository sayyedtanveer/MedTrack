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
  ShieldCheck,
  History,
  Wrench,
  ArrowLeftRight,
  TrendingUp,
  Gauge,
  CalendarDays,
  Building2,
  Database,
  Ruler,
  Tag,
  MapPin,
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
const MANUFACTURING_ROLES = getRolesForModule("manufacturing")
const PROCUREMENT_ROLES = getRolesForModule("procurement")
const INVENTORY_ROLES = getRolesForModule("inventory")
const REPORTS_ROLES = getRolesForModule("reports")
const DELIVERY_ROLES = getRolesForModule("delivery")
const QUALITY_ROLES = getRolesForModule("quality")
const WORK_ORDER_ROLES = getRolesForModule("workOrders")
const SALES_ROLES = getRolesForModule("sales")
const SHOP_FLOOR_ROLES = getRolesForModule("shopFloor")

export const NAV_ITEMS: NavItem[] = [
  {
    title: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
    roles: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER],
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

  // ── Manufacturing ────────────────────────────────────────────────────
  {
    title: "Manufacturing",
    href: "/manufacturing/dashboard",
    icon: Factory,
    roles: MANUFACTURING_ROLES,
    children: [
      {
        title: "Production Dashboard",
        href: "/manufacturing/dashboard",
        icon: Gauge,
        roles: MANUFACTURING_ROLES,
      },
      {
        title: "Work Orders",
        href: "/work-orders",
        icon: ClipboardList,
        roles: WORK_ORDER_ROLES,
      },
      {
        title: "Planner Dashboard",
        href: "/work-orders/planner",
        icon: CalendarDays,
        roles: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER, UserRole.PLANNER],
      },
      {
        title: "Shop Floor",
        href: "/shop-floor",
        icon: Factory,
        roles: SHOP_FLOOR_ROLES,
      },
      {
        title: "Operations Master",
        href: "/operations",
        icon: Wrench,
        roles: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER],
      },
    ],
  },

  // ── Procurement ──────────────────────────────────────────────────────
  {
    title: "Procurement",
    href: "/procurement/dashboard",
    icon: Truck,
    roles: PROCUREMENT_ROLES,
    children: [
      {
        title: "Procurement Dashboard",
        href: "/procurement/dashboard",
        icon: LayoutDashboard,
        roles: PROCUREMENT_ROLES,
      },
      {
        title: "Purchase Orders",
        href: "/procurement/purchase-orders",
        icon: FileText,
        roles: PROCUREMENT_ROLES,
      },
      {
        title: "Suppliers",
        href: "/procurement/suppliers",
        icon: Users,
        roles: PROCUREMENT_ROLES,
      },
      {
        title: "Quality & QC",
        href: "/procurement/quality",
        icon: ShieldAlert,
        roles: QUALITY_ROLES,
      },
    ],
  },

  // ── Quality ──────────────────────────────────────────────────────────
  {
    title: "Quality",
    href: "/procurement/quality",
    icon: ShieldCheck,
    roles: QUALITY_ROLES,
    children: [
      {
        title: "QC Dashboard",
        href: "/procurement/quality",
        icon: ShieldCheck,
        roles: QUALITY_ROLES,
      },
    ],
  },

  // ── Delivery ─────────────────────────────────────────────────────────
  {
    title: "Delivery",
    href: "/delivery/dashboard",
    icon: Truck,
    roles: DELIVERY_ROLES,
    children: [
      {
        title: "Delivery Dashboard",
        href: "/delivery/dashboard",
        icon: LayoutDashboard,
        roles: DELIVERY_ROLES,
      },
      {
        title: "Dispatch Queue",
        href: "/delivery/dispatch-queue",
        icon: PackageSearch,
        roles: DELIVERY_ROLES,
      },
    ],
  },

  // ── Inventory ────────────────────────────────────────────────────────
  {
    title: "Inventory",
    href: "/inventory",
    icon: Package,
    roles: INVENTORY_ROLES,
    children: [
      {
        title: "Materials",
        href: "/inventory/materials",
        icon: Package,
        roles: INVENTORY_ROLES,
      },
      {
        title: "Transactions",
        href: "/inventory/transactions",
        icon: ArrowLeftRight,
        roles: INVENTORY_ROLES,
      },
      {
        title: "Stock Movements",
        href: "/inventory/movements",
        icon: History,
        roles: INVENTORY_ROLES,
      },
    ],
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

  // ── Sales ────────────────────────────────────────────────────────────
  {
    title: "Sales",
    href: "/sales",
    icon: ShoppingCart,
    roles: SALES_ROLES,
    children: [
      {
        title: "Sales Dashboard",
        href: "/sales",
        icon: LayoutDashboard,
        roles: SALES_ROLES,
      },
      {
        title: "Sales Orders",
        href: "/sales/orders",
        icon: ClipboardList,
        roles: SALES_ROLES,
      },
      {
        title: "Clients",
        href: "/sales/clients",
        icon: Users,
        roles: SALES_ROLES,
      },
      {
        title: "Price Lists",
        href: "/sales/price-lists",
        icon: FileText,
        roles: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER, UserRole.SALES],
      },
    ],
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
    roles: SHOP_FLOOR_ROLES,
  },

  // ── Reports ──────────────────────────────────────────────────────────
  {
    title: "Reports",
    href: "/reports",
    icon: BarChart3,
    roles: REPORTS_ROLES,
    children: [
      {
        title: "Analytics",
        href: "/reports",
        icon: TrendingUp,
        roles: REPORTS_ROLES,
      },
      {
        title: "Manufacturing KPIs",
        href: "/reports/manufacturing-kpis",
        icon: Gauge,
        roles: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER, UserRole.PLANNER],
      },
    ],
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
    href: "/settings/company-profile",
    icon: Settings,
    roles: getRolesForModule("settings"),
    children: [
      {
        title: "Company Profile",
        href: "/settings/company-profile",
        icon: Building2,
        roles: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER],
      },
      {
        title: "Business Configuration",
        href: "/settings/business-config",
        icon: Settings,
        roles: getRolesForModule("settings"),
      },
      {
        title: "Master Data",
        href: "/settings/master-data/units",
        icon: Database,
        roles: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER],
        children: [
          {
            title: "Units",
            href: "/settings/master-data/units",
            icon: Ruler,
            roles: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER],
          },
          {
            title: "Material Categories",
            href: "/settings/master-data/categories",
            icon: Tag,
            roles: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER],
          },
          {
            title: "Storage Locations",
            href: "/settings/master-data/locations",
            icon: MapPin,
            roles: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER],
          },
        ],
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
