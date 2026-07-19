export interface User {
  id: string;
  email: string;
  role: string;
  name: string;
}

export interface Tenant {
  id: string;
  name: string;
  currency: string;
}

export interface AuthState {
  user: User | null;
  tenant: Tenant | null;
  token: string | null;
}

export interface Material {
  id: string;
  code: string;
  name: string;
  category: string;
  baseUom: string;
  type: "raw" | "semi-finished" | "finished";
  location: string;
  stockLevel: number;
  currentCost?: number;
  sellingPrice?: number;
}

export interface StockAdjustment {
  id: string;
  materialId: string;
  quantity: number;
  type: "add" | "remove" | "adjust" | "reserve";
  location: string;
  remarks: string;
  timestamp: string;
}

export interface BOMOperation {
  id: string;
  sequence: number;
  name: string;
  workstation: string;
  setupTimeMinutes: number;
  runTimeMinutes: number;
  hourlyRate: number;
}

export interface BOMLine {
  id: string;
  materialId: string;
  quantity: number;
  scrapPercentage: number;
}

export interface BOM {
  id: string;
  productId: string; // references variant/material ID (usually finished or semi-finished)
  version: string;
  status: "draft" | "active" | "inactive";
  validFrom: string;
  validTo: string;
  lines: BOMLine[];
  operations: BOMOperation[];
  totalCost?: number;
}

export interface JobCard {
  id: string;
  operationName: string;
  workstation: string;
  status: "pending" | "in_progress" | "completed";
  assignedTo?: string;
  setupTime: number;
  runTime: number;
}

export interface WorkOrder {
  id: string;
  workOrderNumber: string;
  productId: string; // finished variant
  bomId: string;
  plannedQuantity: number;
  producedQuantity: number;
  scrapQuantity: number;
  status: "planned" | "released" | "in_progress" | "completed" | "closed";
  dueDate: string;
  priority: "low" | "medium" | "high";
  materialsIssued: boolean;
  jobCards: JobCard[];
}

export interface Client {
  id: string;
  code: string;
  name: string;
  email: string;
  creditLimit: number;
  creditUsed: number;
  defaultPriceListId?: string | null;
}

export interface SalesOrderLine {
  id: string;
  productId: string;
  quantity: number;
  unitPrice: number;
}

export interface SalesOrder {
  id: string;
  orderNumber: string;
  clientId: string;
  status: "draft" | "confirmed" | "shipped" | "delivered" | "cancelled";
  orderDate: string;
  deliveryDate: string;
  lines: SalesOrderLine[];
  taxRate: number;
  discountAmount: number;
  totalAmount: number;
}
