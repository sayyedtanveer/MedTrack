import { useMutation } from "@tanstack/react-query"
import { toast } from "sonner"
import { authService } from "@/services/auth.service"
import { useAuthStore } from "@/app/store/authStore"
import { useShowError } from "@/hooks/useShowError"
import { getPostLoginPath } from "@/lib/roles.config"
import { useTenantStore } from "@/app/store/tenantStore"
import { useNavigate } from "react-router-dom"

export function useAuth() {
  const {
    setAuth,
    setUser,
    setPermissions,
    setSupplierAndClient,
    logout: clearAuthStore,
    isAuthenticated,
    user,
    tenant_id,
  } = useAuthStore()
  const { clearTenant, setTenantInfo } = useTenantStore()
  const navigate = useNavigate()
  const showError = useShowError()

  // Mutation for login
  const loginMutation = useMutation({
    mutationFn: authService.login,
    onSuccess: async (data) => {
      // 1. Store token
      setAuth(data.access_token, data.tenant_id)
      
      // 2. Fetch current user profile + tenant info with the new token
      try {
        const meResult = await authService.getMe()
        setUser(meResult.user)
        setPermissions(meResult.permissions ?? [])
        setSupplierAndClient(meResult.user.supplier_id ?? null, meResult.user.client_id ?? null)
        setTenantInfo(meResult.tenant.name, meResult.tenant.slug, meResult.tenant.plan)
        
        toast.success("Welcome back!")

        const home = getPostLoginPath(meResult.user.role)
        navigate(home, { replace: true })
      } catch (err) {
        clearAuthStore()
        showError({
          title: "Session error",
          message: "Your session was created but we couldn't load your profile. Please try logging in again.",
        })
      }
    },
    onError: (error: any) => {
      // useShowError automatically maps HTTP status to friendly messages
      // (e.g. 422 → "Invalid input", 401 → "Authentication failed")
      // and shows a top-center sonner toast (single popup, no duplicates).
      showError(error)
    },
  })

  // Mutation for registration
  const registerMutation = useMutation({
    mutationFn: authService.registerTenant,
    onSuccess: async (data) => {
      setAuth(data.access_token, data.tenant_id)
      try {
        const meResult = await authService.getMe()
        setUser(meResult.user)
        setPermissions(meResult.permissions ?? [])
        setSupplierAndClient(meResult.user.supplier_id ?? null, meResult.user.client_id ?? null)
        setTenantInfo(meResult.tenant.name, meResult.tenant.slug, meResult.tenant.plan)
        
        toast.success("Tenant created successfully! Welcome.")
        navigate("/", { replace: true })
      } catch (err) {
        clearAuthStore()
        navigate("/login")
      }
    },
    onError: (error: any) => {
      showError(error)
    },
  })

  const logout = () => {
    clearAuthStore()
    clearTenant()
    // Optional: call backend to invalidate token if implemented
    navigate("/login", { replace: true })
  }

  return {
    login: loginMutation.mutate,
    isLoggingIn: loginMutation.isPending,
    register: registerMutation.mutate,
    isRegistering: registerMutation.isPending,
    logout,
    isAuthenticated,
    user,
    tenant_id,
    supplier_id: useAuthStore((s) => s.supplier_id),
    client_id: useAuthStore((s) => s.client_id),
  }
}
