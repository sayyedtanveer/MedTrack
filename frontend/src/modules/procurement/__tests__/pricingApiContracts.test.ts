import { beforeEach, describe, expect, it, vi } from 'vitest'
import { materialCostHistoryApi, priceOverrideApi } from '../services/pricingApi'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('@/services/api', () => ({ apiClient: api }))
beforeEach(() => vi.clearAllMocks())

describe('pricing API contract adapters', () => {
  it('loads the real history endpoint and normalizes Decimal strings before filtering/pagination', async () => {
    api.get.mockResolvedValue({ data: [
      { id: 'initial', material_id: 'm', old_cost: null, new_cost: '400.0000', change_type: 'INITIAL_SETUP', source_type: 'MANUAL', created_at: '2026-11-16' },
      { id: 'direct', material_id: 'm', old_cost: '400.0000', new_cost: '450.0000', change_type: 'DIRECT_REVISION', source_type: 'MANUAL', created_at: '2026-11-16' },
    ] })
    const result = await materialCostHistoryApi.getHistoryByChangeType('m', 'DIRECT_REVISION', 1, 20)
    expect(api.get).toHaveBeenCalledWith('/procurement/pricing/cost-history/m', { params: { limit: 10000 } })
    expect(result.total).toBe(1)
    expect(result.history[0]).toMatchObject({ id: 'direct', old_cost: 400, new_cost: 450 })
    const page = await materialCostHistoryApi.getHistory('m', 2, 1)
    expect(page.history[0].id).toBe('direct')
    expect(page.total).toBe(2)
  })

  it('surfaces failed history reads instead of presenting a fake empty audit log', async () => {
    api.get.mockRejectedValue(new Error('Forbidden'))
    await expect(materialCostHistoryApi.getHistory('m')).rejects.toThrow('Forbidden')
  })

  it('records using the existing material override endpoint and reloads its real record', async () => {
    api.post.mockResolvedValue({ data: { override_id: 'saved' } })
    api.get.mockResolvedValue({ data: [{ id: 'saved', suggested_price: '500', override_price: '450', variance_percent: '-10' }] })
    const body = { material_id: 'm', suggested_price: 500, override_price: 450, override_reason: 'OTHER' as const }
    const result = await priceOverrideApi.record(body)
    expect(api.post).toHaveBeenCalledWith('/procurement/pricing/price-overrides', body)
    expect(result).toMatchObject({ id: 'saved', suggested_price: 500, override_price: 450, variance_percent: -10 })
  })
})
