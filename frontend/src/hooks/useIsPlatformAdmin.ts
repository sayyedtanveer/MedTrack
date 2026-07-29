import { useAuthStore } from "@/app/store/authStore";
import { useTenantStore } from "@/app/store/tenantStore";

export function useIsPlatformAdmin(): boolean {
  const user = useAuthStore((s) => s.user);
  const isSystemTenant = useTenantStore((s) => s.is_system_tenant);

  if (!user) return false;

  return user.role === "tenant_admin" && isSystemTenant === true;
}
