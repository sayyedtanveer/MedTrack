import { apiClient } from "@/services/api-client";
import { SystemTenantListResponse, TenantActionRequest } from "../types/platform";

export const platformApi = {
  getTenants: async (): Promise<SystemTenantListResponse> => {
    const response = await apiClient.get<SystemTenantListResponse>("/system/tenants");
    return response.data;
  },

  approveTenant: async (tenantId: string): Promise<{ detail: string }> => {
    const response = await apiClient.post<{ detail: string }>(`/system/tenants/${tenantId}/approve`);
    return response.data;
  },

  rejectTenant: async (tenantId: string, data: TenantActionRequest): Promise<{ detail: string }> => {
    const response = await apiClient.post<{ detail: string }>(`/system/tenants/${tenantId}/reject`, data);
    return response.data;
  },

  suspendTenant: async (tenantId: string, data: TenantActionRequest): Promise<{ detail: string }> => {
    const response = await apiClient.post<{ detail: string }>(`/system/tenants/${tenantId}/suspend`, data);
    return response.data;
  },

  reactivateTenant: async (tenantId: string): Promise<{ detail: string }> => {
    const response = await apiClient.post<{ detail: string }>(`/system/tenants/${tenantId}/reactivate`);
    return response.data;
  },
};
