import { create } from "zustand"
import { persist } from "zustand/middleware"

interface TenantStore {
  name: string | null
  slug: string | null
  plan: string | null
  is_system_tenant: boolean
  setTenantInfo: (name: string, slug: string, plan: string, is_system_tenant?: boolean) => void
  clearTenant: () => void
}

export const useTenantStore = create<TenantStore>()(
  persist(
    (set) => ({
      name: null,
      slug: null,
      plan: null,
      is_system_tenant: false,
      setTenantInfo: (name, slug, plan, is_system_tenant = false) => set({ name, slug, plan, is_system_tenant }),
      clearTenant: () => set({ name: null, slug: null, plan: null, is_system_tenant: false }),
    }),
    {
      name: "tenant-storage",
    }
  )
)
