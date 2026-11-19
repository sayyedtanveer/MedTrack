import React from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { OrderProductionCompletion } from '@/modules/sales/components/OrderProductionCompletion'
import NewDeliveryPage from '@/modules/sales/pages/NewDeliveryPage'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

const mocks = vi.hoisted(() => ({ get: vi.fn(), complete: vi.fn(), order: vi.fn(), post: vi.fn(), allowed: true }))
vi.mock('@/services/sales.service', () => ({ ordersApi: { get: mocks.order } }))
vi.mock('@/services/api-client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api-client')>()
  return { ...actual, apiClient: { ...actual.apiClient, post: mocks.post } }
})
vi.mock('@/modules/sales/services/productionCompletion', () => ({
  productionCompletion: { get: mocks.get, complete: mocks.complete },
}))
vi.mock('@/hooks/usePermissions', () => ({
  usePermissions: () => ({ hasPermission: () => mocks.allowed }),
}))

const ready = { id: 'wo-a', wo_number: 'WO-A', product_id: 'a', status: 'FG_RECEIVED' }
const pending = { id: 'wo-b', wo_number: 'WO-B', product_id: 'b', status: 'QC_PENDING' }
const products = [{ product_id: 'a', product_name: 'Chair' }, { product_id: 'b', product_name: 'Table' }]

function show(onCompleted = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(<QueryClientProvider client={client}>
    <OrderProductionCompletion orderId="order" products={products} onCompleted={onCompleted} />
  </QueryClientProvider>)
}

beforeEach(() => { vi.resetAllMocks(); mocks.allowed = true })
afterEach(cleanup)

it('completes ready products together and keeps the QC-pending product visible', async () => {
  mocks.get.mockResolvedValue({ items: [ready, pending] })
  mocks.complete.mockResolvedValue({ items: [{ ...ready, status: 'COMPLETED' }, pending] })
  const done = vi.fn()
  show(done)
  fireEvent.click(await screen.findByRole('button', { name: 'Complete Ready Products' }))
  await waitFor(() => expect(done).toHaveBeenCalledOnce())
  expect(mocks.complete).toHaveBeenCalledExactlyOnceWith('order')
  expect(screen.getByText(/Table — QC PENDING/)).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Complete Ready Products' })).not.toBeInTheDocument()
})

it('offers exactly one Complete All Products action when both products are ready', async () => {
  mocks.get.mockResolvedValue({ items: [ready, { ...pending, status: 'FG_RECEIVED' }] })
  show()
  expect(await screen.findAllByRole('button', { name: 'Complete All Products' })).toHaveLength(1)
})

it('prevents users without manufacturing permission from completing products', async () => {
  mocks.allowed = false
  mocks.get.mockResolvedValue({ items: [ready] })
  show()
  expect(await screen.findByRole('button', { name: 'Complete All Products' })).toBeDisabled()
})

it('shows completion errors and does not continue to delivery', async () => {
  mocks.get.mockResolvedValue({ items: [ready] })
  mocks.complete.mockRejectedValue(new Error('Production could not be completed'))
  const done = vi.fn()
  show(done)
  fireEvent.click(await screen.findByRole('button', { name: 'Complete All Products' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Production could not be completed')
  expect(done).not.toHaveBeenCalled()
})

it('asks to complete ready products before creating a partial delivery', async () => {
  mocks.order.mockResolvedValue({ id: 'order', order_number: 'SO-TEST', grand_total: 20,
    lines: products.map((product, index) => ({ ...product, id: `line-${index}`,
      quantity: 1, allocated_qty: index === 0 ? 1 : 0, shipped_qty: 0, line_status: 'PENDING' })) })
  mocks.get.mockResolvedValue({ items: [ready, pending] })
  mocks.complete.mockResolvedValue({ items: [{ ...ready, status: 'COMPLETED' }, pending] })
  mocks.post.mockResolvedValue({ data: { delivery_number: 'DO-TEST' } })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(<QueryClientProvider client={client}>
    <MemoryRouter initialEntries={['/sales/orders/order/delivery/new']}>
      <Routes>
        <Route path="/sales/orders/:id/delivery/new" element={<NewDeliveryPage />} />
        <Route path="/delivery/dashboard" element={<p>Delivery created</p>} />
      </Routes>
    </MemoryRouter>
  </QueryClientProvider>)
  fireEvent.click(await screen.findByRole('button', { name: 'Create Delivery Note' }))
  expect(await screen.findByRole('dialog')).toBeVisible()
  expect(mocks.post).not.toHaveBeenCalled()
  fireEvent.click(await screen.findByRole('button', { name: 'Complete Ready Products' }))
  expect(await screen.findByText('Delivery created')).toBeVisible()
  expect(mocks.post).toHaveBeenCalledWith('/deliveries', expect.objectContaining({
    lines: [{ sales_order_line_id: 'line-0', quantity: 1 }],
  }))
})
