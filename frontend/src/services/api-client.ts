import axios, { AxiosError } from "axios"
import { useAuthStore } from "@/app/store/authStore"

// Default to `/api/v1` when `VITE_API_URL` is not provided in development.
// This keeps calls like `/inventory/...` routed to the backend via the dev proxy.
const DEFAULT_API_BASE = import.meta.env.VITE_API_URL ?? "/api/v1"
const DEBUG_ONBOARDING_ENDPOINT = "/inventory/material-onboarding/sessions"

export const apiClient = axios.create({
  baseURL: DEFAULT_API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
})

export default apiClient

function normalizeRequestUrl(url: string | undefined): string {
  if (!url) return ""
  try {
    const parsed = new URL(url, window.location.origin)
    return parsed.pathname.replace(/^\/api\/v1/, "")
  } catch {
    return url.replace(/^\/api\/v1/, "")
  }
}



export function isSessionInvalidError(error: unknown): boolean {
  if (!axios.isAxiosError(error) || error.response?.status !== 401) {
    return false
  }

  // Treat ANY 401 Unauthorized response as a session invalidation,
  // prompting a clean logout and redirect to the login screen.
  // The response interceptor already excludes login/register endpoints from this.
  return true
}

function isAuthRequest(url: string | undefined): boolean {
  const requestPath = normalizeRequestUrl(url)
  return requestPath.startsWith("/auth/login") || requestPath.startsWith("/auth/register")
}

/**
 * Extract user-friendly error message from API response
 * Handles Pydantic validation errors, standard error responses, etc.
 */
export function extractErrorMessage(error: AxiosError<any>): string {
  if (!error.response) {
    // Network error — backend is unreachable (wrong port, not running, etc.)
    if (error.code === "ERR_NETWORK" || error.message === "Network Error") {
      return "Cannot reach the server. Please make sure the backend is running on port 8001."
    }
    return error.message || "Network error. Please check your connection."
  }

  const data = error.response.data

  if (data?.error?.message) {
    return typeof data.error.message === "string" ? data.error.message : JSON.stringify(data.error.message)
  }

  // Handle Pydantic validation errors (422 Unprocessable Entity)
  if (error.response.status === 422) {
    // Pydantic returns an array of validation errors
    if (Array.isArray(data)) {
      const messages = data
        .map((err) => {
          // Each error has: {type, loc, msg, input, ctx}
          if (err.msg) return err.msg
          if (err.detail) return err.detail
          return "Validation error"
        })
        .filter(Boolean)
      return messages.join(", ") || "Validation error"
    }
    // Some APIs return {detail: "..."}
    if (data.detail) return data.detail
    return "Validation error"
  }

  // Handle standard error responses {detail: "..."}
  if (data.detail) {
    return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)
  }

  // Handle {message: "..."}
  if (data.message) {
    return typeof data.message === "string" ? data.message : JSON.stringify(data.message)
  }

  // Handle raw string errors
  if (typeof data === "string") {
    return data
  }

  // Fallback to HTTP status text
  return error.response.statusText || "An error occurred"
}

// Request interceptor: attach token, clear Content-Type for FormData, and clean up params
apiClient.interceptors.request.use(
  (config) => {
    const { token, tenant_id } = useAuthStore.getState()

    const requestPath = normalizeRequestUrl(config.url)
    if (requestPath === DEBUG_ONBOARDING_ENDPOINT) {
      console.log("[AuthDebug][Request] onboarding sessions - pre-headers", {
        url: config.url,
        method: config.method,
        tokenPresent: Boolean(token),
        tenantPresent: Boolean(tenant_id),
        tokenPrefix: token ? token.slice(0, 12) : null,
        storeTenantId: tenant_id,
        existingAuthHeader: Boolean(
          (config.headers as any)?.Authorization || (config.headers as any)?.authorization
        ),
      })
    }

    // Ensure headers is always a mutable Axios-compatible object and attach auth/tenant data
    const existingHeaders = config.headers ?? {}
    const headers = new axios.AxiosHeaders(existingHeaders as any)

    // Add tenant ID header for multi-tenant support
    if (tenant_id) {
      headers.set("X-Tenant-ID", tenant_id)
    }

    if (config.data instanceof FormData) {
      // For FormData, remove the default JSON content-type so browser can set proper multipart boundary
      headers.delete("Content-Type")
    }

    // Always set Authorization header in final form (after FormData header adjustments)
    if (token) {
      headers.set("Authorization", `Bearer ${token}`)
    }

    // When sending FormData, remove the default Content-Type so the browser
    // sets multipart/form-data with the correct boundary automatically.
    // If Content-Type is left as "application/json" Axios will not override
    // it and the backend multipart parser will reject the body.
    if (config.data instanceof FormData) {
      headers.delete("Content-Type")
    }

    config.headers = headers

    // Remove empty/null query parameters to prevent backend validation errors
    if (config.params) {
      Object.keys(config.params).forEach((key) => {
        const value = (config.params as Record<string, unknown>)[key]
        if (value === null || value === undefined || value === "") {
          delete (config.params as Record<string, unknown>)[key]
        }
      })
    }

    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: handle errors and authentication
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle true session invalidation. Page-specific 401s should surface to
    // the screen instead of clearing the whole ERP session during navigation.
    if (isSessionInvalidError(error) && !isAuthRequest(error.config?.url)) {
      const { logout } = useAuthStore.getState()
      logout()
      const loginPath = window.location.pathname.startsWith("/client") ? "/client/login" : "/login"
      if (window.location.pathname !== loginPath) {
        window.location.href = loginPath
      }
      return Promise.reject(error)
    }

    // Extract and enhance error message for better debugging
    const errorMessage = extractErrorMessage(error)
    const tokenWasSent = Boolean(error.config?.headers?.Authorization)
    console.error("API Error:", {
      status: error.response?.status,
      message: errorMessage,
      url: error.config?.url,
      method: error.config?.method,
      tokenWasSent,
      data: error.response?.data,
    })

    // Create a new error with user-friendly message
    const enhancedError = new Error(errorMessage) as AxiosError
    Object.assign(enhancedError, error)
    enhancedError.message = errorMessage // Restore the extracted message after Object.assign overrides it
    
    return Promise.reject(enhancedError)
  }
)
