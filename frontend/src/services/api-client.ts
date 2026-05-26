import axios, { AxiosError } from "axios"
import { useAuthStore } from "@/app/store/authStore"

// Default to `/api/v1` when `VITE_API_URL` is not provided in development.
// This keeps calls like `/inventory/...` routed to the backend via the dev proxy.
const DEFAULT_API_BASE = import.meta.env.VITE_API_URL ?? "/api/v1"

export const apiClient = axios.create({
  baseURL: DEFAULT_API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
})

export default apiClient

/**
 * Extract user-friendly error message from API response
 * Handles Pydantic validation errors, standard error responses, etc.
 */
export function extractErrorMessage(error: AxiosError<any>): string {
  if (!error.response) {
    return error.message || "Network error. Please check your connection."
  }

  const data = error.response.data

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
    const { token } = useAuthStore.getState()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // When sending FormData, remove the default Content-Type so the browser
    // sets multipart/form-data with the correct boundary automatically.
    // If Content-Type is left as "application/json" Axios will not override
    // it and the backend multipart parser will reject the body.
    if (config.data instanceof FormData) {
      delete config.headers["Content-Type"]
    }

    // Remove empty/null query parameters to prevent backend validation errors
    if (config.params) {
      Object.keys(config.params).forEach(key => {
        if (config.params[key] === null || config.params[key] === undefined || config.params[key] === '') {
          delete config.params[key]
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
    // Handle 401 Unauthorized - token expired or invalid
    if (error.response?.status === 401) {
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
    
    console.error("API Error:", {
      status: error.response?.status,
      message: errorMessage,
      data: error.response?.data,
      url: error.config?.url,
    })

    // Create a new error with user-friendly message
    const enhancedError = new Error(errorMessage) as AxiosError
    Object.assign(enhancedError, error)
    
    return Promise.reject(enhancedError)
  }
)
