import { useAuthStore } from "@/app/store/authStore"
import { UserRole, normalizeRole } from "@/lib/roles.config"
import { hasPermission as checkPermission, Permission } from "@/lib/permissions.config"

/**
 * Permission checks mirror backend domain/shared/permissions.py — use hasPermission(), not raw role strings.
 */
export function usePermissions() {
  const { user, permissions } = useAuthStore()
  const roleRaw = user?.role
  const dynamicPermissions = permissions ?? []

  const hasRole = (roles: (UserRole | string)[]): boolean => {
    if (!user) return false
    const normalized = normalizeRole(user.role)
    return roles.some((r) => normalizeRole(r as string) === normalized)
  }

  const hasPermission = (permission: string): boolean => {
    if (dynamicPermissions.length > 0) {
      return dynamicPermissions.includes(Permission.ALL) || dynamicPermissions.includes(permission)
    }
    return checkPermission(roleRaw, permission)
  }

  const isAdmin = (): boolean => hasPermission(Permission.ALL) || hasRole([UserRole.ADMIN, UserRole.TENANT_ADMIN])
  const isManager = (): boolean => hasRole([UserRole.MANAGER])
  const isOperator = (): boolean => hasRole([UserRole.OPERATOR, UserRole.STOREKEEPER, UserRole.WORKER])
  const isViewer = (): boolean => hasRole([UserRole.VIEWER])
  const isQc = (): boolean => hasRole([UserRole.QC])

  const canWrite = (): boolean =>
    hasPermission(Permission.INVENTORY_WRITE) || hasPermission(Permission.PROCUREMENT_WRITE)
  const canDelete = (): boolean => hasRole([UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER])
  const canEditBOM = (): boolean => hasRole([UserRole.ADMIN, UserRole.TENANT_ADMIN, UserRole.MANAGER])
  const canViewBOM = (): boolean => !!user

  /** Subcontract receive / GRN / PO write (storekeeper + admin). */
  const canProcurementWrite = (): boolean => hasPermission(Permission.PROCUREMENT_WRITE)
  /** Manage inspection templates & record inspections. */
  const canQualityWrite = (): boolean => hasPermission(Permission.QUALITY_WRITE)
  /** Manage master locations (quarantine bins). */
  const canInventoryWrite = (): boolean => hasPermission(Permission.INVENTORY_WRITE)

  return {
    hasRole,
    hasPermission,
    isAdmin,
    isManager,
    isOperator,
    isViewer,
    isQc,
    canWrite,
    canDelete,
    canEditBOM,
    canViewBOM,
    canProcurementWrite,
    canQualityWrite,
    canInventoryWrite,
    role: roleRaw,
  }
}
