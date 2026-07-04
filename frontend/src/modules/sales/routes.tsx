/**
 * Sales Module Routes
 * Defines all routes for Sales Order, Client, and Price List management
 */

import { RouteObject } from 'react-router-dom';
import SalesDashboardPage from './pages/SalesDashboardPage';
import SalesOrdersListPage from './pages/SalesOrdersListPage';
import SalesOrderDetailPage from './pages/SalesOrderDetailPage';
import SalesOrderFormPage from './pages/SalesOrderFormPage';
import ClientsListPage from './pages/ClientsListPage';
import ClientFormPage from './pages/ClientFormPage';
import PriceListsPage from './pages/PriceListsPage';
import PriceListFormPage from './pages/PriceListFormPage';
import DeliveriesPage from './pages/DeliveriesPage';

export const salesRoutes: RouteObject[] = [
  {
    path: 'sales',
    children: [
      {
        index: true,
        element: <SalesDashboardPage />,
      },
      {
        path: 'orders',
        element: <SalesOrdersListPage />,
      },
      {
        path: 'orders/new',
        element: <SalesOrderFormPage />,
      },
      {
        path: 'orders/:id',
        element: <SalesOrderDetailPage />,
      },
      {
        path: 'orders/:id/edit',
        element: <SalesOrderFormPage />,
      },
      {
        path: 'clients',
        element: <ClientsListPage />,
      },
      {
        path: 'clients/new',
        element: <ClientFormPage />,
      },
      {
        path: 'clients/:id/edit',
        element: <ClientFormPage />,
      },
      {
        path: 'price-lists',
        element: <PriceListsPage />,
      },
      {
        path: 'price-lists/new',
        element: <PriceListFormPage />,
      },
      {
        path: 'price-lists/:id/edit',
        element: <PriceListFormPage />,
      },
      {
        path: 'deliveries',
        element: <DeliveriesPage />,
      },
    ],
  },
];

export default salesRoutes;
