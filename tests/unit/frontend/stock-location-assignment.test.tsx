import React from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AssignExistingStock } from '@/modules/inventory/components/AssignExistingStock'

const mocks = vi.hoisted(() => ({ stock: vi.fn(), assign: vi.fn(), receive: vi.fn(), allowed: true }))
vi.mock('@/services/material.service', () => ({ materialService: {
  getMaterials: vi.fn().mockResolvedValue({ items: [{ id: 'plank', code: 'RM-PLA', name: 'Plank' }] }),
  getLocations: vi.fn().mockResolvedValue([
    { id: 'wh', name: 'Warehouse', type: 'warehouse', is_active: true },
    { id: 'vendor', name: 'Vendor', type: 'subcontractor', is_active: true },
  ]),
  getMaterialStockByLocation: mocks.stock,
  assignExistingStock: mocks.assign,
  createTransaction: mocks.receive,
} }))
vi.mock('@/hooks/usePermissions', () => ({ usePermissions: () => ({ canInventoryWrite: () => mocks.allowed }) }))

const unlocated = { material_id: 'plank', material_code: 'RM-PLA', material_name: 'Plank',
  total_stock: 2000, located_stock: 0, unlocated_stock: 2000, locations: [] }

function show() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(<QueryClientProvider client={client}><AssignExistingStock initialMaterialId="plank" /></QueryClientProvider>)
}

beforeEach(() => {
  mocks.stock.mockReset()
  mocks.assign.mockReset()
  mocks.receive.mockReset()
  mocks.allowed = true
  HTMLElement.prototype.scrollIntoView ??= vi.fn()
})
afterEach(cleanup)

it('assigns existing quantity to storage and refreshes the unchanged total', async () => {
  mocks.stock.mockResolvedValue(unlocated)
  mocks.assign.mockImplementation(async () => {
    mocks.stock.mockResolvedValue({ ...unlocated, located_stock: 2000, unlocated_stock: 0 })
    return { assigned_quantity: '2000' }
  })
  show()
  const location = await screen.findByRole('combobox', { name: 'Physical storage location' })
  fireEvent.keyDown(location, { key: 'Enter' })
  expect(screen.queryByRole('option', { name: 'Vendor' })).not.toBeInTheDocument()
  fireEvent.click(await screen.findByRole('option', { name: 'Warehouse' }))
  fireEvent.click(screen.getByRole('button', { name: 'Assign 2000.00 Existing Units' }))
  await waitFor(() => expect(mocks.assign).toHaveBeenCalledWith('plank', 'wh', 'Opening stock location reconciliation'))
  expect(await screen.findByText('No stock is waiting for a location assignment.')).toBeVisible()
  expect(screen.getByText('Total stock: 2000.00')).toBeVisible()
  expect(mocks.receive).not.toHaveBeenCalled()
})

it('offers no assignment when all existing stock is already located', async () => {
  mocks.stock.mockResolvedValue({ ...unlocated, located_stock: 2000, unlocated_stock: 0 })
  show()
  expect(await screen.findByText('No stock is waiting for a location assignment.')).toBeVisible()
  expect(screen.queryByRole('button', { name: /Assign.*Existing Units/ })).not.toBeInTheDocument()
})

it('disables assignment without inventory write permission', async () => {
  mocks.allowed = false
  mocks.stock.mockResolvedValue(unlocated)
  show()
  expect(await screen.findByRole('button', { name: 'Assign 2000.00 Existing Units' })).toBeDisabled()
})
