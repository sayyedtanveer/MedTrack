/**
 * CENTRALIZED ROLE CONFIGURATION (aligned with backend Role + JWT)
 * Use normalizeRole() + MODULE_ROLES / hasPermission() — avoid string role checks in components.
 */

import { LucideIcon, Shield, Users, Wrench, Eye } from "lucide-react"

export enum UserRole {
  ADMIN = "ADMIN",
  TENANT_ADMIN = "TENANT_ADMIN",
  MANAGER = "MANAGER",
  OPERATOR = "OPERATOR",
  VIEWER = "VIEWER",
  STOREKEEPER = "STOREKEEPER",
  QC = "QC",
  PLANNER = "PLANNER",
  SALES = "SALES",
  ACCOUNTANT = "ACCOUNTANT",
  WORKER = "WORKER",
  CLIENT = "CLIENT",
  SUPPLIER = "SUPPLIER",
}

/** Logical modules for sidebar + route guards */
export type AppModuleKey =
  | "dashboard"
  | "systemMap"
  | "products"
  | "bom"
  | "manufacturing"
  | "inventory"
  | "workOrders"
  | "procurement"
  | "quality"
  | "sales"
  | "delivery"
  | "finance"
  | "shopFloor"
  | "reports"
  | "auditLogs"
  | "users"
  | "settings"
  | "supplierPortal"

export const ROLE_MODULE_ACCESS: Record<UserRole, AppModuleKey[]> = {
  [UserRole.ADMIN]: [
    "dashboard",
    "systemMap",
    "products",
    "bom",
    "manufacturing",
    "inventory",
    "workOrders",
    "procurement",
    "quality",
    "sales",
    "delivery",
    "finance",
    "shopFloor",
    "reports",
    "auditLogs",
    "users",
    "settings",
  ],
  [UserRole.TENANT_ADMIN]: [
    "dashboard",
    "systemMap",
    "products",
    "bom",
    "manufacturing",
    "inventory",
    "workOrders",
    "procurement",
    "quality",
    "sales",
    "delivery",
    "finance",
    "shopFloor",
    "reports",
    "auditLogs",
    "users",
    "settings",
  ],
  [UserRole.PLANNER]: ["dashboard", "bom", "workOrders", "inventory", "procurement", "reports"],
  [UserRole.STOREKEEPER]: ["dashboard", "inventory", "workOrders", "procurement", "delivery"],
  [UserRole.OPERATOR]: ["dashboard", "inventory", "workOrders", "procurement", "quality", "manufacturing"],
  [UserRole.MANAGER]: [
    "dashboard",
    "products",
    "bom",
    "manufacturing",
    "inventory",
    "workOrders",
    "procurement",
    "quality",
    "sales",
    "delivery",
    "finance",
    "reports",
  ],
  [UserRole.ACCOUNTANT]: ["dashboard", "finance", "reports"],
  [UserRole.SALES]: ["dashboard", "sales", "delivery"],
  [UserRole.QC]: ["dashboard", "quality", "workOrders", "inventory"],
  [UserRole.WORKER]: ["shopFloor"],
  [UserRole.CLIENT]: ["dashboard", "sales"],
  [UserRole.SUPPLIER]: ["supplierPortal"],
  [UserRole.VIEWER]: ["dashboard", "inventory", "sales", "reports"],
}

export const ROLE_DASHBOARD_PATHS: Partial<Record<UserRole, string>> = {
  [UserRole.ADMIN]: "/",
  [UserRole.TENANT_ADMIN]: "/",
  [UserRole.PLANNER]: "/dashboard/planner",
  [UserRole.STOREKEEPER]: "/dashboard/storekeeper",
  [UserRole.SALES]: "/dashboard/sales",
  [UserRole.ACCOUNTANT]: "/finance",
  [UserRole.QC]: "/procurement/quality",
  [UserRole.WORKER]: "/shop-floor",
  [UserRole.CLIENT]: "/client",
  [UserRole.SUPPLIER]: "/supplier-portal",
  [UserRole.OPERATOR]: "/dashboard/storekeeper",
}

export const ROLE_CONFIG: Record<
  UserRole,
  {
    label: string
    description: string
    icon: LucideIcon
    color: string
    sortOrder: number
  }
> = {
  [UserRole.ADMIN]: {
    label: "Administrator",
    description: "Full access",
    icon: Shield,
    color: "text-red-600",
    sortOrder: 1,
  },
  [UserRole.TENANT_ADMIN]: {
    label: "Tenant admin",
    description: "Full access",
    icon: Shield,
    color: "text-red-500",
    sortOrder: 2,
  },
  [UserRole.MANAGER]: {
    label: "Manager",
    description: "Operations & procurement",
    icon: Users,
    color: "text-blue-600",
    sortOrder: 3,
  },
  [UserRole.PLANNER]: {
    label: "Planner",
    description: "Planning & BOM",
    icon: Users,
    color: "text-indigo-600",
    sortOrder: 4,
  },
  [UserRole.STOREKEEPER]: {
    label: "Storekeeper",
    description: "GRN & stock",
    icon: Wrench,
    color: "text-green-600",
    sortOrder: 5,
  },
  [UserRole.OPERATOR]: {
    label: "Operator",
    description: "Warehouse & production ops",
    icon: Wrench,
    color: "text-green-600",
    sortOrder: 6,
  },
  [UserRole.QC]: {
    label: "Quality",
    description: "Inspections & NCR",
    icon: Shield,
    color: "text-amber-600",
    sortOrder: 7,
  },
  [UserRole.SALES]: {
    label: "Sales",
    description: "Orders & customers",
    icon: Users,
    color: "text-cyan-600",
    sortOrder: 8,
  },
  [UserRole.ACCOUNTANT]: {
    label: "Accountant",
    description: "Finance & reports",
    icon: Users,
    color: "text-emerald-600",
    sortOrder: 9,
  },
  [UserRole.WORKER]: {
    label: "Worker",
    description: "Shop floor",
    icon: Wrench,
    color: "text-orange-600",
    sortOrder: 10,
  },
  [UserRole.CLIENT]: {
    label: "Client",
    description: "Portal",
    icon: Eye,
    color: "text-gray-600",
    sortOrder: 11,
  },
  [UserRole.SUPPLIER]: {
    label: "Supplier",
    description: "Supplier portal",
    icon: Users,
    color: "text-violet-600",
    sortOrder: 12,
  },
  [UserRole.VIEWER]: {
    label: "Viewer",
    description: "Read-only",
    icon: Eye,
    color: "text-gray-600",
    sortOrder: 13,
  },
}

const KNOWN_ROLE_VALUES = new Set(Object.values(UserRole))

/**
 * Normalize JWT / API role string to UserRole enum (uppercase).
 */
export function normalizeRole(role: string | undefined): UserRole | undefined {
  if (!role) return undefined
  const upper = role.trim().toUpperCase()
  if (KNOWN_ROLE_VALUES.has(upper as UserRole)) {
    return upper as UserRole
  }
  console.warn(`Unknown role: ${role}`)
  return undefined
}

/** After login — role-specific home (see spec: qc → quality, worker → shop floor, …). */
export function getPostLoginPath(roleRaw: string | undefined): string {
  const r = normalizeRole(roleRaw)
  if (!r) return "/"
  return ROLE_DASHBOARD_PATHS[r] ?? "/"
}

export function hasModuleAccess(role: UserRole | string | undefined, module: AppModuleKey): boolean {
  const r = typeof role === "string" ? normalizeRole(role) : role
  if (!r) return false
  const list = ROLE_MODULE_ACCESS[r] || []
  return list.includes(module)
}

export function getRoleLabel(role: UserRole | string | undefined): string {
  const r = typeof role === "string" ? normalizeRole(role) : role
  return r ? ROLE_CONFIG[r].label : "Unknown"
}

export const AVAILABLE_ROLES = Object.entries(ROLE_CONFIG)
  .map(([role, config]) => ({
    // send lowercase role values to backend (backend expects e.g. "supplier")
    value: role.toLowerCase(),
    label: config.label,
    description: config.description,
  }))
  .sort((a, b) => ROLE_CONFIG[(a.value as string).toUpperCase() as UserRole].sortOrder - ROLE_CONFIG[(b.value as string).toUpperCase() as UserRole].sortOrder)

/** @deprecated Use MODULE_ROLES + module keys */
export const MODULE_ROLES: Record<string, UserRole[]> = {
  dashboard: [
    UserRole.ADMIN,
    UserRole.TENANT_ADMIN,
    UserRole.MANAGER,
    UserRole.PLANNER,
    UserRole.STOREKEEPER,
    UserRole.OPERATOR,
    UserRole.SALES,
    UserRole.ACCOUNTANT,
    UserRole.QC,
    UserRole.WORKER,
    UserRole.CLIENT,
    UserRole.VIEWER,
  ],
  systemMap: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER, UserRole.PLANNER],
  products: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER],
  bom: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER, UserRole.PLANNER, UserRole.OPERATOR],
  manufacturing: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER, UserRole.PLANNER],
  inventory: [
    UserRole.ADMIN,
    UserRole.TENANT_ADMIN,
    UserRole.MANAGER,
    UserRole.PLANNER,
    UserRole.STOREKEEPER,
    UserRole.OPERATOR,
    UserRole.QC,
    UserRole.VIEWER,
  ],
  delivery: [
    UserRole.ADMIN,
    UserRole.TENANT_ADMIN,
    UserRole.MANAGER,
    UserRole.SALES,
    UserRole.STOREKEEPER,
  ],
  finance: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT],
  workOrders: [
    UserRole.ADMIN,
    UserRole.TENANT_ADMIN,
    UserRole.MANAGER,
    UserRole.PLANNER,
    UserRole.STOREKEEPER,
    UserRole.OPERATOR,
    UserRole.QC,
    UserRole.WORKER,
  ],
  procurement: [
    UserRole.ADMIN,
    UserRole.TENANT_ADMIN,
    UserRole.MANAGER,
    UserRole.PLANNER,
    UserRole.STOREKEEPER,
    UserRole.OPERATOR,
  ],
  quality: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER, UserRole.OPERATOR, UserRole.QC],
  sales: [
    UserRole.ADMIN,
    UserRole.TENANT_ADMIN,
    UserRole.MANAGER,
    UserRole.SALES,
    UserRole.CLIENT,
    UserRole.VIEWER,
  ],
  shopFloor: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER, UserRole.WORKER, UserRole.OPERATOR],
  reports: [UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER, UserRole.PLANNER, UserRole.ACCOUNTANT, UserRole.VIEWER],
  auditLogs: [UserRole.ADMIN, UserRole.TENANT_ADMIN],
  users: [UserRole.ADMIN, UserRole.TENANT_ADMIN],
  settings: [UserRole.ADMIN, UserRole.TENANT_ADMIN],
  supplierPortal: [UserRole.SUPPLIER],
}

export function getRolesForModule(module: string): UserRole[] {
  return MODULE_ROLES[module] || []
}

export function canAccessModule(role: UserRole | string | undefined, module: string): boolean {
  const normalized = normalizeRole(role as string)
  if (!normalized) return false
  const allowed = MODULE_ROLES[module] || []
  return allowed.includes(normalized)
}
