import { apiClient } from "./api-client";
import { TenantProfile, UpdateTenantPayload } from "@/types/tenant.types";

export const tenantService = {
  async getProfile(): Promise<TenantProfile> {
    const { data } = await apiClient.get<TenantProfile>("/tenants/me");
    return data;
  },

  async updateProfile(fields: Partial<UpdateTenantPayload>): Promise<TenantProfile> {
    const { data } = await apiClient.put<TenantProfile>("/tenants/me", fields);
    return data;
  },

  async uploadLogo(file: File): Promise<{ url: string }> {
    const form = new FormData();
    form.append("file", file);
    const { data } = await apiClient.post<{ url: string }>("/files", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return { url: data.url };
  },
};
