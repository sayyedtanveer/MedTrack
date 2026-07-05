/**
 * Maps HTTP status codes to user-friendly error titles and descriptions.
 *
 * Every error shown to the user should go through this so they see
 * a human-readable message instead of raw API detail.
 */

interface FriendlyError {
  /** Short title like "Invalid input" */
  title: string
  /** User-facing explanation */
  message: string
  /** Original server detail (shown in expandable section) */
  detail?: string
}

const STATUS_MESSAGES: Record<number, { title: string; message: string }> = {
  400: {
    title: "Bad request",
    message: "The server couldn't process the request. Please check your data and try again.",
  },
  401: {
    title: "Authentication failed",
    message: "Invalid email, password, or Workspace ID. Please check your credentials and try again.",
  },
  403: {
    title: "Access denied",
    message: "You don't have permission to perform this action. Contact your workspace admin.",
  },
  404: {
    title: "Not found",
    message: "The requested resource was not found. It may have been removed or you may have a broken link.",
  },
  409: {
    title: "Conflict",
    message: "This operation conflicts with the current state. The data may have been modified by another user.",
  },
  422: {
    title: "Invalid input",
    message: "One or more fields have invalid values. Please review your input and try again.",
  },
  429: {
    title: "Too many requests",
    message: "You've made too many requests. Please wait a moment before trying again.",
  },
  500: {
    title: "Server error",
    message: "Something went wrong on our end. Please try again in a moment.",
  },
  502: {
    title: "Server unavailable",
    message: "The server is temporarily unavailable. Please wait and try again.",
  },
  503: {
    title: "Service unavailable",
    message: "The service is temporarily down for maintenance. Please try again shortly.",
  },
}

/**
 * Given an HTTP status code and optional server detail, return a
 * user-friendly { title, message, detail } object.
 */
export function getFriendlyError(status: number, serverDetail?: string): FriendlyError {
  const base = STATUS_MESSAGES[status] ?? {
    title: "Error",
    message: "An unexpected error occurred. Please try again.",
  }

  return {
    title: base.title,
    message: serverDetail ? `${base.message}\n\n${serverDetail}` : base.message,
    detail: serverDetail,
  }
}

/**
 * Extract a user-friendly error from any caught value.
 * Handles Axios errors, plain Errors, strings, and unknown shapes.
 */
export function getFriendlyErrorFromUnknown(input: unknown): FriendlyError {
  if (!input) {
    return { title: "Error", message: "An unexpected error occurred." }
  }

  // Try to extract Axios info
  const axiosError = input as any
  const status = axiosError?.response?.status as number | undefined
  const serverDetail =
    axiosError?.response?.data?.detail ??
    axiosError?.response?.data?.message ??
    axiosError?.response?.data?.error?.message ??
    axiosError?.message

  if (status) {
    return getFriendlyError(status, typeof serverDetail === "string" ? serverDetail : undefined)
  }

  // Plain Error or string
  if (input instanceof Error) {
    return { title: "Error", message: input.message }
  }
  if (typeof input === "string") {
    return { title: "Error", message: input }
  }

  return { title: "Error", message: "An unexpected error occurred." }
}
