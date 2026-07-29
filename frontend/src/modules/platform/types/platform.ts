export type TenantStatus = "pending" | "active" | "suspended" | "rejected" | "archived";

export interface SystemTenant {
  id: string;
  name: string;
  slug: string;
  plan: string;
  status: TenantStatus;
  is_active: boolean;
  is_system_tenant: boolean;
  created_at: string;
}

export interface SystemTenantListResponse {
  tenants: SystemTenant[];
  total: number;
}

export interface TenantActionRequest {
  reason?: string;
}

export interface TenantAuditLog {
  id: string;
  tenant_id: string;
  action: string;
  reason?: string;
  acted_by: string;
  created_at: string;
  updated_at: string;
}
