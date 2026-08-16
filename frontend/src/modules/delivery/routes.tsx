/**
 * Delivery Module Routes
 */

import { lazy, Suspense } from "react"
import { RouteObject, Navigate } from "react-router-dom"

const DeliveryDashboardPage = lazy(() => import("./pages/DeliveryDashboardPage"))
const DispatchQueuePage = lazy(() => import("./pages/DispatchQueuePage"))
// NewDeliveryPage lives in the sales module but is also reachable via /deliveries/new?so_id=
const NewDeliveryPage = lazy(() =>
  import("../sales/pages/NewDeliveryPage").then((m) => ({ default: m.default }))
)

const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>

export const deliveryRoutes: RouteObject[] = [
  {
    path: "delivery",
    element: <Navigate to="dashboard" replace />,
  },
  {
    path: "delivery/dashboard",
    element: (
      <Suspense fallback={<PageLoading />}>
        <DeliveryDashboardPage />
      </Suspense>
    ),
  },
  {
    path: "delivery/dispatch-queue",
    element: (
      <Suspense fallback={<PageLoading />}>
        <DispatchQueuePage />
      </Suspense>
    ),
  },
  {
    // Reached from DispatchQueuePage "Create Delivery Note" button: /deliveries/new?so_id=...
    path: "deliveries/new",
    element: (
      <Suspense fallback={<PageLoading />}>
        <NewDeliveryPage />
      </Suspense>
    ),
  },
]
