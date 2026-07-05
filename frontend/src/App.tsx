import { RouterProvider } from "react-router-dom"
import { router } from "@/app/routes"
import { QueryProvider } from "@/app/providers/QueryProvider"
import { ErrorBoundary } from "@/components/layout/ErrorBoundary"
import { RealtimeNotificationsBridge } from "@/components/notifications/RealtimeNotificationsBridge"
import { SonnerToasterProvider } from "@/components/ui/sonner"
import { useAuthInitialize } from "@/hooks/useAuthInitialize"

function AppContent() {
  // Validate token on app initialization
  useAuthInitialize()

  return (
    <>
      <RealtimeNotificationsBridge />
      <RouterProvider router={router} />
    </>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryProvider>
        {/* Mount sonner toasts at the app root so they work on every page,
            including the login page (which doesn't use DefaultLayout). */}
        <SonnerToasterProvider />
        <AppContent />
      </QueryProvider>
    </ErrorBoundary>
  )
}
