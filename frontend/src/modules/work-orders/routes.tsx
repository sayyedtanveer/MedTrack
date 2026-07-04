import { lazy, Suspense } from 'react';
import type { RouteObject } from 'react-router-dom';

const WorkOrdersListPage = lazy(() => import('./pages/WorkOrdersListPage'));
const WorkOrderDetailPage = lazy(() => import('./pages/WorkOrderDetailPage'));
const WorkOrderCreatePage = lazy(() => import('./pages/WorkOrderCreatePage'));
const PlannerDashboardPage = lazy(() => import('./pages/PlannerDashboardPage'));

const Loading = () => (
  <div className="flex h-48 items-center justify-center text-muted-foreground text-sm">
    Loading…
  </div>
);

export const workOrderRoutes: RouteObject[] = [
  {
    path: 'work-orders',
    element: (
      <Suspense fallback={<Loading />}>
        <WorkOrdersListPage />
      </Suspense>
    ),
  },
  {
    path: 'work-orders/planner',
    element: (
      <Suspense fallback={<Loading />}>
        <PlannerDashboardPage />
      </Suspense>
    ),
  },
  {
    path: 'work-orders/new',
    element: (
      <Suspense fallback={<Loading />}>
        <WorkOrderCreatePage />
      </Suspense>
    ),
  },
  {
    path: 'work-orders/:id',
    element: (
      <Suspense fallback={<Loading />}>
        <WorkOrderDetailPage />
      </Suspense>
    ),
  },
];
