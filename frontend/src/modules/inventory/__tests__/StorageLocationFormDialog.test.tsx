import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { StorageLocationFormDialog } from '../components/StorageLocationFormDialog'

const api = vi.hoisted(() => ({ getLocations: vi.fn(), createLocation: vi.fn(), updateLocation: vi.fn() }))
vi.mock('@/services/material.service', () => ({ materialService: api }))
afterEach(() => { cleanup(); vi.clearAllMocks() })
beforeEach(() => { api.getLocations.mockResolvedValue([]); api.updateLocation.mockResolvedValue({}); api.createLocation.mockResolvedValue({}) })

it('reuses the real form and saves the backend default-location flag', async () => {
  const onClose = vi.fn()
  const location = { id: 'loc', name: 'Raw store', type: 'warehouse', location_type: 'warehouse', parent_id: null, is_active: true, is_default: true }
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <StorageLocationFormDialog open location={location} onClose={onClose} />
  </QueryClientProvider>)
  expect(await screen.findByLabelText('Set as Default Location')).toBeChecked()
  fireEvent.change(screen.getByLabelText(/Name/), { target: { value: 'Updated raw store' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))
  await waitFor(() => expect(api.updateLocation).toHaveBeenCalledWith('loc', expect.objectContaining({ name: 'Updated raw store', is_default: true })))
  expect(onClose).toHaveBeenCalled()
})
