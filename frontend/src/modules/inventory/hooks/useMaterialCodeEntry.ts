import { useQuery } from "@tanstack/react-query"
import { usePermissions } from "@/hooks/usePermissions"
import { useAuthStore } from "@/app/store/authStore"
import { numberSeriesService } from "@/services/number-series.service"

export function useMaterialCodeEntry(enabled: boolean) {
  const { isAdmin } = usePermissions()
  const tenantId = useAuthStore((state) => state.tenant_id)
  const { data, isLoading } = useQuery({
    queryKey: ["number-series", tenantId, "material", "code-entry"],
    queryFn: numberSeriesService.getMaterialCodeEntryPolicy,
    enabled,
  })
  return {
    canEnterCode: enabled && data !== undefined && (data.manual_override === "always"
      || (data.manual_override === "admin_only" && isAdmin())),
    generationDisabled: enabled && data?.auto_generate === false,
    isLoading,
  }
}
