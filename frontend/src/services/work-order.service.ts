import { apiClient } from './api-client';
import type { WorkOrderStatus } from '@/types/work-order-status';

export type { WorkOrderStatus };

export interface WorkOrderSummary {
  id: string;
  wo_number: string;
  product_id: string;
  bom_id: string;
  status: WorkOrderStatus;
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
  planned_quantity: number;
  produced_quantity: number;
  scrap_quantity: number;
  start_date: string;
  due_date: string;
  created_at: string;
}

export interface WorkOrderMaterial {
  id: string;
  material_id: string;
  material_code: string;
  material_name: string;
  unit_id: string;
  required_quantity: number;
  issued_quantity: number;
}

export interface JobCard {
  id: string;
  operation_id: string;
  operation_name: string;
  sequence: number;
  status: 'PENDING' | 'IN_PROGRESS' | 'DONE';
  assigned_to: string | null;
  started_at: string | null;
  completed_at: string | null;
  remarks: string | null;
}

export interface WorkOrderDetail extends WorkOrderSummary {
  notes: string | null;
  sales_order_id: string | null;
  materials: WorkOrderMaterial[];
  job_cards: JobCard[];
  hold_reason?: string | null;
  hold_started_at?: string | null;
}

export interface MaterialAvailabilityLine {
  material_id: string;
  material_code: string;
  material_name: string;
  unit_id: string | null;
  unit_code: string | null;
  unit_name: string | null;
  required_quantity: number;
  available_quantity: number;
  shortage_quantity: number;
  status: 'ok' | 'low' | 'shortage';
}

export interface MaterialAvailabilityPreview {
  product_id: string;
  bom_id: string;
  planned_quantity: number;
  has_shortage: boolean;
  shortage_count: number;
  message: string | null;
  lines: MaterialAvailabilityLine[];
}

export interface CreateWorkOrderPayload {
  product_id: string;
  bom_id: string;
  planned_quantity: number;
  start_date: string;
  due_date: string;
  priority?: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
  sales_order_id?: string;
  notes?: string;
}

export interface IssueMaterialPayload {
  material_id: string;
  quantity: number;
  unit_id: string;
}

export interface RecordProductionPayload {
  produced_quantity: number;
  scrap_quantity?: number;
  notes?: string;
}

const toNumber = (value: unknown): number => {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
};

const normalizeAvailabilityLine = (line: MaterialAvailabilityLine): MaterialAvailabilityLine => ({
  ...line,
  required_quantity: toNumber(line.required_quantity),
  available_quantity: toNumber(line.available_quantity),
  shortage_quantity: toNumber(line.shortage_quantity),
});

const normalizeAvailabilityPreview = (
  preview: MaterialAvailabilityPreview,
): MaterialAvailabilityPreview => ({
  ...preview,
  planned_quantity: toNumber(preview.planned_quantity),
  shortage_count: toNumber(preview.shortage_count),
  lines: Array.isArray(preview.lines) ? preview.lines.map(normalizeAvailabilityLine) : [],
});

const BASE = '/work-orders';

const workOrderService = {
  list: (params?: { status?: string; active?: boolean; product_id?: string }) =>
    apiClient.get<WorkOrderSummary[]>(BASE, { params }),

  /** Shop-floor active work orders (material reserved through production/rework). */
  listActive: () =>
    apiClient.get<WorkOrderSummary[]>(BASE, { params: { active: true } }),

  get: (id: string) =>
    apiClient.get<WorkOrderDetail>(`${BASE}/${id}`),

  create: (data: CreateWorkOrderPayload) =>
    apiClient.post<{ id: string }>(BASE, data),

  release: (id: string) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/release`, {}),

  start: (id: string) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/start`, {}),

  complete: (id: string) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/complete`, {}),

  close: (id: string) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/close`, {}),

  issueMaterial: (woId: string, data: IssueMaterialPayload) =>
    apiClient.post<{ message: string }>(`${BASE}/${woId}/issue-materials`, data),

  recordProduction: (woId: string, data: RecordProductionPayload) =>
    apiClient.post<{ message: string }>(`${BASE}/${woId}/record-production`, data),

  listJobCards: (woId: string) =>
    apiClient.get<JobCard[]>(`${BASE}/${woId}/job-cards`),

  startJobCard: (woId: string, jcId: string, assignedTo?: string) =>
    apiClient.patch<{ status: string }>(
      `${BASE}/${woId}/job-cards/${jcId}/start`,
      { assigned_to: assignedTo ?? null }
    ),

  completeJobCard: (woId: string, jcId: string, remarks?: string) =>
    apiClient.patch<{ status: string }>(
      `${BASE}/${woId}/job-cards/${jcId}/complete`,
      { remarks: remarks ?? null }
    ),

  generatePickList: (woId: string) =>
    apiClient.post<{
      pick_list_id: string;
      pick_list_number: string;
      work_order_id: string;
      lines: Array<{
        material_id: string;
        material_code: string;
        quantity: number;
        location: string;
        sequence: number;
      }>;
    }>(`${BASE}/${woId}/pick-list`, {}),

  checkMaterialAvailability: async (params: {
    product_id: string;
    bom_id?: string;
    quantity: number;
  }) => {
    const response = await apiClient.get<MaterialAvailabilityPreview>(`${BASE}/material-availability`, {
      params,
    });
    return {
      ...response,
      data: normalizeAvailabilityPreview(response.data),
    };
  },

  // QC Actions
  qcApprove: (id: string) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/qc-approve`, {}),

  qcReject: (id: string, data: { reason: string }) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/qc-reject`, data),

  sendToRework: (id: string) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/qc-rework`, {}),

  scrap: (id: string, data: { reason: string }) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/scrap`, data),

  // FG Receipt
  receiveFG: (id: string) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/fg-receive`, {}),

  // Production Hold and Resume
  hold: (id: string, data: { reason: string }) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/hold`, data),

  resume: (id: string) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/resume`, {}),

  // Cancellation
  cancel: (id: string, reason?: string) =>
    apiClient.post<{ status: string }>(`${BASE}/${id}/cancel`, reason ? { reason } : {}),
};

export default workOrderService;
