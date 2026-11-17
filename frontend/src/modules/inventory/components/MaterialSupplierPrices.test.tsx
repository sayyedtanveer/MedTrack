import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MaterialFormDrawer } from './MaterialFormDrawer'
import { normalizeSupplierAgreement } from '@/modules/procurement/services/supplierPriceAgreementApi'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('@/services/api', () => ({ apiClient: mocks }))
vi.mock('@/components/shared/Drawer', () => ({ Drawer: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }))
vi.mock('./MaterialTraceabilityTab', () => ({ MaterialTraceabilityTab: () => null }))
vi.mock('./MaterialStockByLocation', () => ({ MaterialStockByLocation: () => null }))
vi.mock('@/services/material.service', () => ({ materialService: {
  getMaterial: vi.fn().mockResolvedValue({ id: 'material-1', name: 'Brass rod', code: 'RM-BRASS', material_type: 'raw', current_cost: 400, current_stock: 0, latest_purchase_price: null, purchase_count: 0 }),
  getCategories: vi.fn().mockResolvedValue([]),
  getLocations: vi.fn().mockResolvedValue([]),
  getUnits: vi.fn().mockResolvedValue([{ id: 'kg', name: 'Kilogram', code: 'KG' }]),
} }))
vi.mock('@/services/tenant.service', () => ({ tenantService: { getProfile: vi.fn().mockResolvedValue({ currency_code: 'INR' }) } }))
vi.mock('@/services/supply-chain.service', () => ({ supplyChainApi: {
  listInspectionTemplates: vi.fn().mockResolvedValue({ data: [] }),
  listSuppliers: vi.fn().mockResolvedValue({ data: [{ id: 'supplier-1', name: 'Test Supplier', code: 'SUP-001' }] }),
} }))

const quote = {
  id: 'quote-1', supplier_id: 'supplier-1', material_id: 'material-1', status: 'DRAFT' as const,
  base_price: '500.000000', currency_code: 'INR', purchase_uom_id: 'kg', minimum_order_quantity: '10.000000',
  effective_from: '2026-11-01T00:00:00Z', effective_to: null, quantity_tiers: null, notes: null,
  created_at: '2026-11-01T00:00:00Z', updated_at: '2026-11-01T00:00:00Z',
}

beforeEach(() => {
  mocks.get.mockImplementation(async (url: string) => ({ data: url.includes('supplier-price-agreements')
    ? { items: [quote], total: 1, page: 1, page_size: 100 }
    : { cost_status: 'CONFIGURED' } }))
  mocks.post.mockResolvedValue({ data: { new_cost: '450.0000' } })
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

async function openBuy() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(<QueryClientProvider client={client}><MaterialFormDrawer materialId="material-1" open onClose={() => undefined} /></QueryClientProvider>)
  const tab = await screen.findByRole('tab', { name: 'Buy' })
  fireEvent.mouseDown(tab, { button: 0, ctrlKey: false })
  return client
}

describe('Material drawer Buy tab', () => {
  it('shows normalized DRAFT supplier quotes independently of GRN history', async () => {
    await openBuy()
    expect(await screen.findByText('Test Supplier')).toBeInTheDocument()
    expect(screen.getByText('SUP-001')).toBeInTheDocument()
    expect(screen.getByText('INR 500')).toBeInTheDocument()
    expect(screen.getByText('KG')).toBeInTheDocument()
    expect(screen.getByText('DRAFT')).toBeInTheDocument()
    expect(screen.getByText('No purchase history yet')).toBeInTheDocument()
    expect(screen.getByText(/DRAFT quotes are not active purchasing agreements/)).toBeInTheDocument()
    expect(mocks.get).toHaveBeenCalledWith('/procurement/pricing/supplier-price-agreements', {
      params: { material_id: 'material-1', page_size: 100 },
    })
  })

  it('keeps the existing direct standard-cost action and expected-cost token', async () => {
    await openBuy()
    const reason = await screen.findByLabelText(/Reason for change/)
    fireEvent.change(reason, { target: { value: 'Annual review' } })
    fireEvent.change(screen.getByLabelText('Standard Cost'), { target: { value: '450' } })
    fireEvent.click(screen.getByRole('button', { name: 'Update Standard Cost' }))
    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith('/inventory/materials/material-1/set-standard-cost', {
      new_cost: 450, reason: 'Annual review', expected_current_cost: 400,
    }))
  })

  it('updates the untouched input from approved cost after bulk upload and preserves edits', async () => {
    const client = await openBuy()
    const input = await screen.findByLabelText('Standard Cost')
    await waitFor(() => expect(input).toHaveValue(400))
    client.setQueryData(['material-cost-status', 'material-1'], {
      cost_status: 'CONFIGURED', approved_cost: '500.1250', current_cost: '500.1250',
    })
    await waitFor(() => expect(input).toHaveValue(500.125))
    fireEvent.change(input, { target: { value: '550' } })
    client.setQueryData(['material-cost-status', 'material-1'], {
      cost_status: 'CONFIGURED', approved_cost: '510', current_cost: '510',
    })
    await waitFor(() => expect(screen.getByText(/^INR 510(?:\.0+)?$/)).toBeInTheDocument())
    expect(input).toHaveValue(550)
  })

  it('reports unavailable quote data instead of hiding it as no history', async () => {
    mocks.get.mockRejectedValue(new Error('Forbidden'))
    await openBuy()
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load supplier prices')
    expect(screen.getByText('No purchase history yet')).toBeInTheDocument()
  })

  it('normalizes Decimal-string prices and rejects invalid numeric data', () => {
    expect(normalizeSupplierAgreement(quote)).toMatchObject({ base_price: 500, minimum_order_quantity: 10 })
    expect(() => normalizeSupplierAgreement({ ...quote, base_price: 'NaN' })).toThrow('invalid price')
  })
})
