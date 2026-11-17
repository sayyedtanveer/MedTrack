import { beforeEach, describe, expect, it, vi } from 'vitest'
import { materialOnboardingService } from '../services/materialOnboardingApi'

const mocks = vi.hoisted(() => ({ get: vi.fn() }))
vi.mock('@/services/api-client', () => ({ apiClient: mocks }))

beforeEach(() => vi.clearAllMocks())

describe('onboarding template availability', () => {
  it('uses the authenticated API client', async () => {
    mocks.get.mockResolvedValue({ data: 'template' })
    expect(await materialOnboardingService.backendRoutesAvailable()).toBe(true)
    expect(mocks.get).toHaveBeenCalledWith('/inventory/material-onboarding/template?format=csv', { responseType: 'blob' })
  })

  it('reports failed authentication or template generation as unavailable', async () => {
    mocks.get.mockRejectedValue(new Error('Unauthorized'))
    expect(await materialOnboardingService.backendRoutesAvailable()).toBe(false)
  })
})
