import { useAuthStore } from "@/app/store/authStore";
import { useTenantStore } from "@/app/store/tenantStore";

export function useIsPlatformAdmin(): boolean {
  const user = useAuthStore((s) => s.user);
  const isSystemTenant = useTenantStore((s) => s.is_system_tenant);

  if (!user || !user.role) return false;

  const role = user.role.toUpperCase();
  return (role === "ADMIN" || role === "TENANT_ADMIN") && isSystemTenant === true;
}
