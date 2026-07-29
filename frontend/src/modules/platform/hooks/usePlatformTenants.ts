import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { platformApi } from "../api/platformApi";
import { TenantActionRequest } from "../types/platform";
import { useShowError } from "@/hooks/useShowError";

export const platformKeys = {
  all: ["platform"] as const,
  tenants: () => [...platformKeys.all, "tenants"] as const,
  tenant: (id: string) => [...platformKeys.tenants(), id] as const,
  dashboard: () => [...platformKeys.all, "dashboard"] as const,
};

export function usePlatformTenants() {
  return useQuery({
    queryKey: platformKeys.tenants(),
    queryFn: platformApi.getTenants,
  });
}

export function useApproveTenant() {
  const queryClient = useQueryClient();
  const showError = useShowError();

  return useMutation({
    mutationFn: (tenantId: string) => platformApi.approveTenant(tenantId),
    onSuccess: () => {
      toast.success("Tenant approved successfully");
      queryClient.invalidateQueries({ queryKey: platformKeys.tenants() });
    },
    onError: (err) => {
      showError(err);
    },
  });
}

export function useRejectTenant() {
  const queryClient = useQueryClient();
  const showError = useShowError();

  return useMutation({
    mutationFn: ({ tenantId, data }: { tenantId: string; data: TenantActionRequest }) =>
      platformApi.rejectTenant(tenantId, data),
    onSuccess: () => {
      toast.success("Tenant rejected successfully");
      queryClient.invalidateQueries({ queryKey: platformKeys.tenants() });
    },
    onError: (err) => {
      showError(err);
    },
  });
}

export function useSuspendTenant() {
  const queryClient = useQueryClient();
  const showError = useShowError();

  return useMutation({
    mutationFn: ({ tenantId, data }: { tenantId: string; data: TenantActionRequest }) =>
      platformApi.suspendTenant(tenantId, data),
    onSuccess: () => {
      toast.success("Tenant suspended successfully");
      queryClient.invalidateQueries({ queryKey: platformKeys.tenants() });
    },
    onError: (err) => {
      showError(err);
    },
  });
}

export function useReactivateTenant() {
  const queryClient = useQueryClient();
  const showError = useShowError();

  return useMutation({
    mutationFn: (tenantId: string) => platformApi.reactivateTenant(tenantId),
    onSuccess: () => {
      toast.success("Tenant reactivated successfully");
      queryClient.invalidateQueries({ queryKey: platformKeys.tenants() });
    },
    onError: (err) => {
      showError(err);
    },
  });
}
