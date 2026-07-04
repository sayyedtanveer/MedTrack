/**
 * Delivery Module Routes
 */

import { lazy, Suspense } from "react"
import { RouteObject } from "react-router-dom"

const DeliveryDashboardPage = lazy(() => import("./pages/DeliveryDashboardPage"))
const DispatchQueuePage = lazy(() => import("./pages/DispatchQueuePage"))

const PageLoading = () => <div className="p-8 flex items-center justify-center">Loading...</div>

export const deliveryRoutes: RouteObject[] = [
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
]
