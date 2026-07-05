import { useCallback } from "react"
import { toast } from "sonner"
import { AxiosError } from "axios"
import { getFriendlyErrorFromUnknown } from "@/lib/error-messages"

export interface ShowErrorOptions {
  /** Toast title (e.g. "Login failed", "Save error") */
  title?: string
  /** The main message body. */
  message?: string
  /** Label for the confirm button (not used for toasts, kept for API consistency) */
  confirmLabel?: string
  /** Callback when toast is dismissed */
  onClose?: () => void
}

/**
 * SINGLE entry point for displaying errors anywhere in the app.
 *
 * Shows ONE top-center sonner toast with auto-dismiss.
 * No duplicate popups — this is the only error surface.
 *
 * HTTP status codes are automatically translated to user-friendly messages
 * (e.g. 422 → "Invalid input", 401 → "Authentication failed").
 *
 * Usage:
 *   const showError = useShowError()
 *   showError(error)                          // AxiosError → friendly message
 *   showError(new Error("Something broke"))   // plain Error
 *   showError("Something went wrong")         // string
 *   showError({ title: "Login failed", message: "…" }) // custom
 */
export function useShowError() {
  return useCallback(
    (input: unknown | ShowErrorOptions) => {
      // Normalise input to { title, message }
      let title: string
      let message: string

      if (input instanceof AxiosError || input instanceof Error) {
        const friendly = getFriendlyErrorFromUnknown(input)
        title = friendly.title
        message = friendly.message
      } else if (typeof input === "string") {
        title = "Error"
        message = input
      } else {
        const opts = input as ShowErrorOptions
        title = opts.title ?? "Error"
        message = opts.message ?? "An unexpected error occurred."
      }

      // Show ONE top-center sonner toast (auto-dismisses)
      toast.error(title, {
        description: message,
        duration: 5000,
        closeButton: true,
      })
    },
    [],
  )
}
