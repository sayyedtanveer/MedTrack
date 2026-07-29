import { useEffect, useRef } from "react"
import { useAuthStore } from "@/app/store/authStore"
import { useTenantStore } from "@/app/store/tenantStore"
import { isClientSession } from "@/lib/auth-session"
import { apiClient, isSessionInvalidError } from "@/services/api-client"

/**
 * Hook to validate token on app initialization
 * Clears auth state if token is invalid or expired
 * This ensures users are logged out when backend session is lost
 */
export function useAuthInitialize() {
  const { token, logout, isAuthenticated, user, client_id, setUser, setPermissions, hasHydrated } = useAuthStore()
  const lastValidatedToken = useRef<string | null>(null)
  const { setTenantInfo } = useTenantStore()

  useEffect(() => {
    const validateToken = async () => {
      if (!hasHydrated) {
        return
      }

      // Only validate if user appears to be authenticated
      if (!isAuthenticated || !token) {
        lastValidatedToken.current = null
        return
      }
      if (lastValidatedToken.current === token) {
        return
      }

      try {
        const validationEndpoint = isClientSession({
          token,
          userRole: user?.role,
          clientId: client_id,
        })
          ? "/client/profile"
          : "/auth/me"
        const response = await apiClient.get(validationEndpoint)
        if (validationEndpoint === "/auth/me") {
          setUser(response.data.user)
          setPermissions(response.data.permissions ?? [])
          setTenantInfo(
            response.data.tenant.name,
            response.data.tenant.slug,
            response.data.tenant.plan,
            response.data.tenant.is_system_tenant
          )
        }
        lastValidatedToken.current = token
      } catch (error) {
        if (isSessionInvalidError(error)) {
          // Token is expired/invalid or the auth validation endpoint rejected it.
          logout()
          lastValidatedToken.current = null
        } else {
          // Preserve the session when backend validation is temporarily unreachable.
          console.warn("Initial auth validation was inconclusive; preserving session.", error)
        }
      }
    }

    validateToken()
  }, [hasHydrated, token, isAuthenticated, logout, user?.role, client_id, setUser, setPermissions, setTenantInfo])
}
