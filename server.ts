import express from "express";
import cors from "cors";
import path from "path";
import dotenv from "dotenv";
import { createServer as createViteServer } from "vite";
import { 
  User, Tenant, Material, StockAdjustment, 
  BOM, WorkOrder, Client, SalesOrder 
} from "./src/types.js";

dotenv.config();

const app = express();
const DEFAULT_PORT = Number(process.env.PORT || 3000);

function getPortCandidates(startPort: number) {
  return Array.from({ length: 10 }, (_, index) => startPort + index);
}

app.use(cors());
app.use(express.json());

// ==========================================
// IN-MEMORY DATABASE & SEED DATA
// ==========================================

const tenants: Tenant[] = [
  { id: "tenant-1", name: "Apex Pharma Ltd", currency: "USD" },
  { id: "tenant-2", name: "BioMed Manufacturing", currency: "EUR" }
];

const users: (User & { passwordHash: string; tenantId: string })[] = [
  { 
    id: "user-1", 
    email: "admin@apex.com", 
    role: "ADMIN", 
    name: "John Admin", 
    passwordHash: "password123", 
    tenantId: "tenant-1" 
  },
  { 
    id: "user-2", 
    email: "planner@apex.com", 
    role: "PLANNER", 
    name: "Sarah Planner", 
    passwordHash: "password123", 
    tenantId: "tenant-1" 
  },
  { 
    id: "user-3", 
    email: "storekeeper@apex.com", 
    role: "STOREKEEPER", 
    name: "Mike Storekeeper", 
    passwordHash: "password123", 
    tenantId: "tenant-1" 
  }
];

const materials: (Material & { tenantId: string })[] = [
  // Finished Goods
  { 
    id: "mat-1", 
    code: "FG-MED-500", 
    name: "Acetaminophen 500mg Tablets", 
    category: "Tablets", 
    baseUom: "Box", 
    type: "finished", 
    location: "Aisle A1", 
    stockLevel: 120, 
    tenantId: "tenant-1",
    currentCost: 0,
    sellingPrice: 240
  },
  { 
    id: "mat-2", 
    code: "FG-MED-250", 
    name: "Ibuprofen 250mg Capsules", 
    category: "Capsules", 
    baseUom: "Box", 
    type: "finished", 
    location: "Aisle A2", 
    stockLevel: 45, 
    tenantId: "tenant-1",
    currentCost: 0,
    sellingPrice: 180
  },
  // Raw Materials
  { 
    id: "mat-3", 
    code: "RM-ACT-API", 
    name: "Acetaminophen API Powder", 
    category: "API", 
    baseUom: "Kg", 
    type: "raw", 
    location: "Raw Cold Room", 
    stockLevel: 50, 
    tenantId: "tenant-1",
    currentCost: 250
  },
  { 
    id: "mat-4", 
    code: "RM-LAC-EXC", 
    name: "Lactose Monohydrate Binder", 
    category: "Excipients", 
    baseUom: "Kg", 
    type: "raw", 
    location: "Dry Room B", 
    stockLevel: 150, 
    tenantId: "tenant-1",
    currentCost: 15
  },
  { 
    id: "mat-5", 
    code: "RM-BLS-PKG", 
    name: "Aluminium Blister Foil", 
    category: "Packaging", 
    baseUom: "Roll", 
    type: "raw", 
    location: "Packaging Zone", 
    stockLevel: 10, 
    tenantId: "tenant-1",
    currentCost: 80
  }
];

const stockAdjustments: (StockAdjustment & { tenantId: string })[] = [
  {
    id: "adj-1",
    materialId: "mat-1",
    quantity: 120,
    type: "adjust",
    location: "Aisle A1",
    remarks: "Initial stock load",
    timestamp: new Date().toISOString(),
    tenantId: "tenant-1"
  },
  {
    id: "adj-2",
    materialId: "mat-3",
    quantity: 50,
    type: "add",
    location: "Raw Cold Room",
    remarks: "Received from GRN PO-1029",
    timestamp: new Date().toISOString(),
    tenantId: "tenant-1"
  }
];

const boms: (BOM & { tenantId: string })[] = [
  {
    id: "bom-1",
    productId: "mat-1", // Acetaminophen 500mg
    version: "1.0",
    status: "active",
    validFrom: "2026-01-01",
    validTo: "2027-12-31",
    lines: [
      { id: "line-1", materialId: "mat-3", quantity: 0.5, scrapPercentage: 2 }, // 0.5kg of API
      { id: "line-2", materialId: "mat-4", quantity: 0.3, scrapPercentage: 1 }, // 0.3kg of binder
      { id: "line-3", materialId: "mat-5", quantity: 0.1, scrapPercentage: 5 }  // 0.1 roll of foil
    ],
    operations: [
      { id: "op-1", sequence: 10, name: "Granulation & Mixing", workstation: "WS-MIX-01", setupTimeMinutes: 30, runTimeMinutes: 1.5, hourlyRate: 45 },
      { id: "op-2", sequence: 20, name: "Tablet Compression", workstation: "WS-COMP-02", setupTimeMinutes: 45, runTimeMinutes: 2.0, hourlyRate: 60 },
      { id: "op-3", sequence: 30, name: "Blister Packaging", workstation: "WS-PKG-03", setupTimeMinutes: 15, runTimeMinutes: 1.0, hourlyRate: 40 }
    ],
    tenantId: "tenant-1"
  }
];

const workOrders: (WorkOrder & { tenantId: string })[] = [
  {
    id: "wo-1",
    workOrderNumber: "WO-2026-001",
    productId: "mat-1",
    bomId: "bom-1",
    plannedQuantity: 100,
    producedQuantity: 0,
    scrapQuantity: 0,
    status: "planned",
    dueDate: "2026-08-15",
    priority: "medium",
    materialsIssued: false,
    jobCards: [
      { id: "jc-1", operationName: "Granulation & Mixing", workstation: "WS-MIX-01", status: "pending", setupTime: 30, runTime: 150 },
      { id: "jc-2", operationName: "Tablet Compression", workstation: "WS-COMP-02", status: "pending", setupTime: 45, runTime: 200 },
      { id: "jc-3", operationName: "Blister Packaging", workstation: "WS-PKG-03", status: "pending", setupTime: 15, runTime: 100 }
    ],
    tenantId: "tenant-1"
  }
];

const clients: (Client & { tenantId: string })[] = [
  { id: "cli-1", code: "CLI-CARE", name: "CarePlus Distributors", email: "orders@careplus.com", creditLimit: 50000, creditUsed: 12000, defaultPriceListId: null, tenantId: "tenant-1" },
  { id: "cli-2", code: "CLI-PHAR", name: "PharmaMed Chain", email: "purchasing@pharmamed.com", creditLimit: 100000, creditUsed: 45000, defaultPriceListId: null, tenantId: "tenant-1" }
];

const priceLists: any[] = [
  {
    id: "pl-1",
    name: "Standard Wholesale List",
    isDefault: true,
    isActive: true,
    validFrom: "2026-01-01",
    validTo: "2027-12-31",
    lines: [
      { id: "pll-1", productId: "mat-1", productType: "variant", unitPrice: 240 }
    ],
    tenantId: "tenant-1"
  }
];

const salesOrders: (SalesOrder & { tenantId: string })[] = [
  {
    id: "so-1",
    orderNumber: "SO-10023",
    clientId: "cli-1",
    status: "confirmed",
    orderDate: "2026-07-10",
    deliveryDate: "2026-08-01",
    lines: [
      { id: "sol-1", productId: "mat-1", quantity: 50, unitPrice: 240 } // $12,000
    ],
    taxRate: 5,
    discountAmount: 0,
    totalAmount: 12600, // 12000 + 5% tax
    tenantId: "tenant-1"
  }
];

// ==========================================
// MIDDLEWARES
// ==========================================

// Helper to simulate request authentication via headers
function getTenantAndUser(req: express.Request) {
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    // Default fallback to first tenant/user for easier testing/development
    return { 
      tenant: tenants[0], 
      user: users[0] 
    };
  }

  const token = authHeader.replace("Bearer ", "");
  const user = users.find(u => u.id === token || u.email === token);
  if (!user) {
    return { tenant: tenants[0], user: users[0] };
  }

  const tenant = tenants.find(t => t.id === user.tenantId);
  return { tenant, user };
}

// ==========================================
// API ROUTES
// ==========================================

app.get("/api/health", (req, res) => {
  res.json({ status: "healthy", version: "0.1.0", language: "TypeScript/Node" });
});

// Auth & Tenant Registration
app.post("/api/v1/auth/register-tenant", (req, res) => {
  const { tenantName, adminEmail, adminName, adminPassword } = req.body;
  if (!tenantName || !adminEmail || !adminName || !adminPassword) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  const existingUser = users.find(u => u.email === adminEmail);
  if (existingUser) {
    return res.status(400).json({ error: "Email already registered" });
  }

  const newTenant: Tenant = {
    id: `tenant-${Date.now()}`,
    name: tenantName,
    currency: "USD"
  };

  const newUser: User & { passwordHash: string; tenantId: string } = {
    id: `user-${Date.now()}`,
    email: adminEmail,
    name: adminName,
    role: "ADMIN",
    passwordHash: adminPassword,
    tenantId: newTenant.id
  };

  tenants.push(newTenant);
  users.push(newUser);

  res.status(201).json({
    tenant: newTenant,
    user: { id: newUser.id, email: newUser.email, name: newUser.name, role: newUser.role },
    token: newUser.id
  });
});

app.post("/api/v1/auth/login", (req, res) => {
  const { email, password } = req.body;
  const user = users.find(u => u.email === email && u.passwordHash === password);
  if (!user) {
    return res.status(401).json({ error: "Invalid credentials" });
  }

  const tenant = tenants.find(t => t.id === user.tenantId);
  res.json({
    user: { id: user.id, email: user.email, name: user.name, role: user.role },
    tenant,
    token: user.id
  });
});

app.get("/api/v1/auth/me", (req, res) => {
  const { tenant, user } = getTenantAndUser(req);
  if (!user) return res.status(401).json({ error: "Unauthorized" });
  res.json({ user, tenant });
});

// Materials List & Creation
app.get("/api/v1/inventory/materials", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const tenantMats = materials.filter(m => m.tenantId === tenant.id);
  res.json(tenantMats);
});

app.post("/api/v1/inventory/materials", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const { code, name, category, baseUom, type, location, currentCost, current_cost, sellingPrice, selling_price } = req.body;
  if (!code || !name || !category || !baseUom || !type) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  const existingMat = materials.find(m => m.code === code && m.tenantId === tenant.id);
  if (existingMat) {
    return res.status(400).json({ error: `Material code '${code}' already exists` });
  }

  const initialCost = currentCost !== undefined ? Number(currentCost) : (current_cost !== undefined ? Number(current_cost) : 0);
  const initialSellingPrice = sellingPrice !== undefined ? Number(sellingPrice) : (selling_price !== undefined ? Number(selling_price) : 0);

  const newMaterial: Material & { tenantId: string } = {
    id: `mat-${Date.now()}`,
    code,
    name,
    category,
    baseUom,
    type,
    location: location || "General Store",
    stockLevel: 0,
    currentCost: isNaN(initialCost) ? 0 : initialCost,
    sellingPrice: isNaN(initialSellingPrice) ? 0 : initialSellingPrice,
    tenantId: tenant.id
  };

  materials.push(newMaterial);
  res.status(201).json(newMaterial);
});

app.put("/api/v1/inventory/materials/:id", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const mat = materials.find(m => m.id === req.params.id && m.tenantId === tenant.id);
  if (!mat) return res.status(404).json({ error: "Material not found" });

  const { code, name, category, baseUom, type, location, currentCost, current_cost, sellingPrice, selling_price } = req.body;
  if (code !== undefined) {
    const existing = materials.find(m => m.code === code && m.id !== mat.id && m.tenantId === tenant.id);
    if (existing) return res.status(400).json({ error: `Material code '${code}' already exists` });
    mat.code = code;
  }
  if (name !== undefined) mat.name = name;
  if (category !== undefined) mat.category = category;
  if (baseUom !== undefined) mat.baseUom = baseUom;
  if (type !== undefined) mat.type = type;
  if (location !== undefined) mat.location = location;

  const costVal = currentCost !== undefined ? currentCost : current_cost;
  if (costVal !== undefined) {
    const costNum = Number(costVal);
    if (isNaN(costNum) || costNum < 0) {
      return res.status(400).json({ error: "Standard Purchase Cost must be 0 or greater" });
    }
    if (costNum > 999999999.9999) {
      return res.status(400).json({ error: "Value exceeds maximum allowed" });
    }
    // Check precision (up to 4 decimals)
    mat.currentCost = Number(costNum.toFixed(4));
  }

  const sellVal = sellingPrice !== undefined ? sellingPrice : selling_price;
  if (sellVal !== undefined) {
    const sellNum = Number(sellVal);
    if (isNaN(sellNum) || sellNum < 0) {
      return res.status(400).json({ error: "Selling Price must be 0 or greater" });
    }
    if (sellNum > 999999999.99) {
      return res.status(400).json({ error: "Selling Price exceeds maximum allowed" });
    }
    mat.sellingPrice = Number(sellNum.toFixed(2));
  }

  res.json(mat);
});

// Stock Adjustments / Transactions
app.post("/api/v1/inventory/stock/adjust", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const { materialId, quantity, type, remarks } = req.body;
  if (!materialId || quantity === undefined || !type) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  const mat = materials.find(m => m.id === materialId && m.tenantId === tenant.id);
  if (!mat) return res.status(404).json({ error: "Material not found" });

  const qty = Number(quantity);
  let finalStock = mat.stockLevel;

  if (type === "add") {
    finalStock += qty;
  } else if (type === "remove") {
    if (finalStock < qty) {
      return res.status(400).json({ error: "Negative stock levels not allowed" });
    }
    finalStock -= qty;
  } else if (type === "adjust") {
    if (qty < 0) {
      return res.status(400).json({ error: "Cannot adjust to a negative stock level" });
    }
    finalStock = qty;
  }

  mat.stockLevel = finalStock;

  const newAdjustment: StockAdjustment & { tenantId: string } = {
    id: `adj-${Date.now()}`,
    materialId,
    quantity: qty,
    type,
    location: mat.location,
    remarks: remarks || "Manual adjustment",
    timestamp: new Date().toISOString(),
    tenantId: tenant.id
  };

  stockAdjustments.push(newAdjustment);
  res.status(201).json({ material: mat, adjustment: newAdjustment });
});

app.get("/api/v1/inventory/transactions", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const tenantAdjs = stockAdjustments.filter(a => a.tenantId === tenant.id);
  res.json(tenantAdjs);
});

// Bill of Materials (BOM)
app.get("/api/v1/boms", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const tenantBoms = boms.filter(b => b.tenantId === tenant.id);
  res.json(tenantBoms);
});

app.post("/api/v1/boms", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const { productId, version, validFrom, validTo, lines, operations } = req.body;
  if (!productId || !version) {
    return res.status(400).json({ error: "Product ID and Version are required" });
  }

  const newBOM: BOM & { tenantId: string } = {
    id: `bom-${Date.now()}`,
    productId,
    version,
    status: "draft",
    validFrom: validFrom || new Date().toISOString().split('T')[0],
    validTo: validTo || "2030-12-31",
    lines: lines || [],
    operations: operations || [],
    tenantId: tenant.id
  };

  boms.push(newBOM);
  res.status(201).json(newBOM);
});

app.put("/api/v1/boms/:id", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  const bom = boms.find(b => b.id === req.params.id && b.tenantId === tenant?.id);
  if (!bom) return res.status(404).json({ error: "BOM not found" });

  const { status, lines, operations, validFrom, validTo } = req.body;
  if (status) bom.status = status;
  if (lines) bom.lines = lines;
  if (operations) bom.operations = operations;
  if (validFrom) bom.validFrom = validFrom;
  if (validTo) bom.validTo = validTo;

  res.json(bom);
});

app.get("/api/v1/boms/:id/costs", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  const bom = boms.find(b => b.id === req.params.id && b.tenantId === tenant?.id);
  if (!bom) return res.status(404).json({ error: "BOM not found" });

  // Calculate Rollup Cost
  let materialsCost = 0;
  for (const line of bom.lines) {
    const mat = materials.find(m => m.id === line.materialId && m.tenantId === tenant?.id);
    const baseCost = mat && mat.currentCost !== undefined ? mat.currentCost : 0;
    const lineQty = line.quantity * (1 + line.scrapPercentage / 100);
    materialsCost += baseCost * lineQty;
  }

  let laborCost = 0;
  for (const op of bom.operations) {
    const totalTimeHours = (op.setupTimeMinutes + op.runTimeMinutes) / 60;
    laborCost += totalTimeHours * op.hourlyRate;
  }

  const totalCost = Number((materialsCost + laborCost).toFixed(2));
  bom.totalCost = totalCost;

  res.json({
    bomId: bom.id,
    materialsCost: Number(materialsCost.toFixed(2)),
    laborCost: Number(laborCost.toFixed(2)),
    totalCost
  });
});

app.post("/api/v1/boms/:id/copy", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  const bom = boms.find(b => b.id === req.params.id && b.tenantId === tenant?.id);
  if (!bom) return res.status(404).json({ error: "BOM not found" });

  const { newVersion } = req.body;
  if (!newVersion) return res.status(400).json({ error: "New version string required" });

  const copiedBOM: BOM & { tenantId: string } = {
    ...JSON.parse(JSON.stringify(bom)),
    id: `bom-${Date.now()}`,
    version: newVersion,
    status: "draft"
  };

  boms.push(copiedBOM);
  res.status(201).json(copiedBOM);
});

// Work Orders & Manufacturing Lifecycle
app.get("/api/v1/work-orders", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const tenantWos = workOrders.filter(w => w.tenantId === tenant.id);
  res.json(tenantWos);
});

app.post("/api/v1/work-orders", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const { productId, bomId, plannedQuantity, dueDate, priority } = req.body;
  if (!productId || !bomId || !plannedQuantity) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  const bom = boms.find(b => b.id === bomId && b.tenantId === tenant.id);
  if (!bom) return res.status(404).json({ error: "Active BOM not found" });

  // Generate job cards from BOM operations
  const jobCards = bom.operations.map((op, idx) => ({
    id: `jc-${Date.now()}-${idx}`,
    operationName: op.name,
    workstation: op.workstation,
    status: "pending" as const,
    setupTime: op.setupTimeMinutes,
    runTime: op.runTimeMinutes * plannedQuantity
  }));

  const newWO: WorkOrder & { tenantId: string } = {
    id: `wo-${Date.now()}`,
    workOrderNumber: `WO-2026-${String(workOrders.length + 1).padStart(3, '0')}`,
    productId,
    bomId,
    plannedQuantity: Number(plannedQuantity),
    producedQuantity: 0,
    scrapQuantity: 0,
    status: "planned",
    dueDate: dueDate || new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    priority: priority || "medium",
    materialsIssued: false,
    jobCards,
    tenantId: tenant.id
  };

  workOrders.push(newWO);
  res.status(201).json(newWO);
});

app.post("/api/v1/work-orders/:id/release", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  const wo = workOrders.find(w => w.id === req.params.id && w.tenantId === tenant?.id);
  if (!wo) return res.status(404).json({ error: "Work order not found" });

  if (wo.status !== "planned") {
    return res.status(400).json({ error: "Work order must be in 'planned' status to release" });
  }

  wo.status = "released";
  res.json(wo);
});

// Material Issuance (Deducts components from stock)
app.post("/api/v1/work-orders/:id/materials/issue", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  const wo = workOrders.find(w => w.id === req.params.id && w.tenantId === tenant?.id);
  if (!wo) return res.status(404).json({ error: "Work order not found" });

  if (wo.status !== "released") {
    return res.status(400).json({ error: "Work order must be 'released' to issue materials" });
  }

  const bom = boms.find(b => b.id === wo.bomId && b.tenantId === tenant?.id);
  if (!bom) return res.status(404).json({ error: "BOM not found" });

  // Verify and deduct components
  const deductions: { material: Material; qty: number }[] = [];
  for (const line of bom.lines) {
    const mat = materials.find(m => m.id === line.materialId && m.tenantId === tenant?.id);
    if (!mat) return res.status(404).json({ error: `Material ${line.materialId} not found` });

    const neededQty = line.quantity * wo.plannedQuantity * (1 + line.scrapPercentage / 100);
    if (mat.stockLevel < neededQty) {
      return res.status(400).json({ 
        error: `Insufficient stock for component '${mat.name}'. Available: ${mat.stockLevel} ${mat.baseUom}, Required: ${neededQty.toFixed(2)}` 
      });
    }
    deductions.push({ material: mat, qty: neededQty });
  }

  // Commit stock deductions
  for (const d of deductions) {
    d.material.stockLevel = Number((d.material.stockLevel - d.qty).toFixed(3));
    stockAdjustments.push({
      id: `adj-${Date.now()}-${d.material.id}`,
      materialId: d.material.id,
      quantity: d.qty,
      type: "remove",
      location: d.material.location,
      remarks: `Issued to Work Order ${wo.workOrderNumber}`,
      timestamp: new Date().toISOString(),
      tenantId: tenant!.id
    });
  }

  wo.materialsIssued = true;
  wo.status = "in_progress";
  res.json(wo);
});

// Job Card start/complete
app.post("/api/v1/work-orders/:id/job-cards/:jcId/start", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  const wo = workOrders.find(w => w.id === req.params.id && w.tenantId === tenant?.id);
  if (!wo) return res.status(404).json({ error: "Work order not found" });

  const jc = wo.jobCards.find(j => j.id === req.params.jcId);
  if (!jc) return res.status(404).json({ error: "Job card not found" });

  jc.status = "in_progress";
  res.json(wo);
});

app.post("/api/v1/work-orders/:id/job-cards/:jcId/complete", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  const wo = workOrders.find(w => w.id === req.params.id && w.tenantId === tenant?.id);
  if (!wo) return res.status(404).json({ error: "Work order not found" });

  const jc = wo.jobCards.find(j => j.id === req.params.jcId);
  if (!jc) return res.status(404).json({ error: "Job card not found" });

  jc.status = "completed";
  res.json(wo);
});

// Production posting (Adds finished goods to stock)
app.post("/api/v1/work-orders/:id/production", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  const wo = workOrders.find(w => w.id === req.params.id && w.tenantId === tenant?.id);
  if (!wo) return res.status(404).json({ error: "Work order not found" });

  const { producedQuantity, scrapQuantity } = req.body;
  if (producedQuantity === undefined) {
    return res.status(400).json({ error: "Produced quantity is required" });
  }

  const pQty = Number(producedQuantity);
  const sQty = Number(scrapQuantity || 0);

  wo.producedQuantity += pQty;
  wo.scrapQuantity += sQty;

  // Add produced finished goods to inventory
  const fgMat = materials.find(m => m.id === wo.productId && m.tenantId === tenant?.id);
  if (fgMat) {
    fgMat.stockLevel = Number((fgMat.stockLevel + pQty).toFixed(3));
    stockAdjustments.push({
      id: `adj-${Date.now()}-prod-${fgMat.id}`,
      materialId: fgMat.id,
      quantity: pQty,
      type: "add",
      location: fgMat.location,
      remarks: `Produced from Work Order ${wo.workOrderNumber}`,
      timestamp: new Date().toISOString(),
      tenantId: tenant!.id
    });
  }

  // If we produced at least the planned qty, we auto-complete the WO
  if (wo.producedQuantity >= wo.plannedQuantity) {
    wo.status = "completed";
  }

  res.json(wo);
});

app.post("/api/v1/work-orders/:id/close", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  const wo = workOrders.find(w => w.id === req.params.id && w.tenantId === tenant?.id);
  if (!wo) return res.status(404).json({ error: "Work order not found" });

  wo.status = "closed";
  res.json(wo);
});

// Sales Clients & Sales Orders
app.get("/api/v1/sales/clients", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const tenantClients = clients.filter(c => c.tenantId === tenant.id);
  res.json(tenantClients);
});

app.post("/api/v1/sales/clients", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const { name, email, creditLimit, defaultPriceListId } = req.body;
  if (!name || !email) return res.status(400).json({ error: "Name and Email are required" });

  const newClient: Client & { tenantId: string } = {
    id: `cli-${Date.now()}`,
    code: `CLI-${name.substring(0, 4).toUpperCase()}`,
    name,
    email,
    creditLimit: Number(creditLimit || 50000),
    creditUsed: 0,
    defaultPriceListId: defaultPriceListId || null,
    tenantId: tenant.id
  };

  clients.push(newClient);
  res.status(201).json(newClient);
});

app.patch("/api/v1/sales/clients/:id", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const client = clients.find(c => c.id === req.params.id && c.tenantId === tenant.id);
  if (!client) return res.status(404).json({ error: "Client not found" });

  const { name, email, creditLimit, defaultPriceListId } = req.body;
  if (name !== undefined) client.name = name;
  if (email !== undefined) client.email = email;
  if (creditLimit !== undefined) client.creditLimit = Number(creditLimit);
  if (defaultPriceListId !== undefined) {
    if (defaultPriceListId !== null && defaultPriceListId !== "__none__" && defaultPriceListId !== "") {
      const pl = priceLists.find(p => p.id === defaultPriceListId && p.tenantId === tenant.id && !p.isDeleted);
      if (!pl) return res.status(422).json({ error: "Invalid default price list" });
      client.defaultPriceListId = defaultPriceListId;
    } else {
      client.defaultPriceListId = null;
    }
  }

  res.json(client);
});

// Price Resolution Engine
const resolvePrice = (tenantId: string, productId: string, clientId: string | undefined, orderDate: string) => {
  const prodMat = materials.find(m => m.id === productId && m.tenantId === tenantId);
  const prodName = prodMat ? prodMat.name : `Product ID ${productId}`;

  // Tier 1: Client's default price list
  if (clientId) {
    const client = clients.find(c => c.id === clientId && c.tenantId === tenantId);
    if (client && client.defaultPriceListId) {
      const pl = priceLists.find(p => p.id === client.defaultPriceListId && p.tenantId === tenantId && p.isActive && !p.isDeleted);
      if (pl) {
        const validFrom = pl.validFrom;
        const validTo = pl.validTo;
        if (orderDate >= validFrom && (!validTo || orderDate <= validTo)) {
          const line = pl.lines.find((l: any) => l.productId === productId);
          if (line) {
            return line.unitPrice;
          }
        }
      }
    }
  }

  // Tier 2: Tenant's default price list
  const defaultPl = priceLists.find(p => p.tenantId === tenantId && p.isDefault && p.isActive && !p.isDeleted);
  if (defaultPl) {
    const validFrom = defaultPl.validFrom;
    const validTo = defaultPl.validTo;
    if (orderDate >= validFrom && (!validTo || orderDate <= validTo)) {
      const line = defaultPl.lines.find((l: any) => l.productId === productId);
      if (line) {
        return line.unitPrice;
      }
    }
  }

  // Tier 3: catalog selling price
  if (prodMat && prodMat.sellingPrice && prodMat.sellingPrice > 0) {
    return prodMat.sellingPrice;
  }

  throw new Error(`No price found for ${prodName} (${productId}) at ${orderDate}. Please configure a Price List or catalog Selling Price.`);
};

app.get("/api/v1/sales/resolve-price", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const { clientId, productId, orderDate } = req.query;
  if (!productId) return res.status(400).json({ error: "productId is required" });

  try {
    const dateStr = (orderDate as string) || new Date().toISOString().split('T')[0];
    const price = resolvePrice(tenant.id, productId as string, clientId as string, dateStr);
    res.json({ price });
  } catch (err: any) {
    res.status(422).json({ error: err.message });
  }
});

// Price Lists Suite
app.get("/api/v1/sales/price-lists", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const tenantLists = priceLists.filter(p => p.tenantId === tenant.id && !p.isDeleted);
  res.json(tenantLists);
});

app.get("/api/v1/sales/price-lists/:id", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const pl = priceLists.find(p => p.id === req.params.id && p.tenantId === tenant.id && !p.isDeleted);
  if (!pl) return res.status(404).json({ error: "Price list not found" });

  res.json(pl);
});

app.post("/api/v1/sales/price-lists", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const { name, validFrom, validTo, isDefault, isActive } = req.body;
  if (!name || !validFrom) {
    return res.status(422).json({ error: "Name and Valid From date are required" });
  }

  const duplicate = priceLists.find(p => p.name.toLowerCase() === name.toLowerCase() && p.tenantId === tenant.id && !p.isDeleted);
  if (duplicate) {
    return res.status(409).json({ error: `Price list with name '${name}' already exists` });
  }

  if (validTo && validTo < validFrom) {
    return res.status(422).json({ error: "Valid To date must be greater than or equal to Valid From date" });
  }

  const defaultBool = !!isDefault;
  const activeBool = isActive !== undefined ? !!isActive : true;

  if (defaultBool) {
    priceLists.forEach(p => {
      if (p.tenantId === tenant.id) p.isDefault = false;
    });
  }

  const newPL = {
    id: `pl-${Date.now()}`,
    name,
    validFrom,
    validTo: validTo || null,
    isDefault: defaultBool,
    isActive: activeBool,
    lines: [],
    tenantId: tenant.id
  };

  priceLists.push(newPL);
  res.status(201).json(newPL);
});

app.patch("/api/v1/sales/price-lists/:id", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const pl = priceLists.find(p => p.id === req.params.id && p.tenantId === tenant.id && !p.isDeleted);
  if (!pl) return res.status(404).json({ error: "Price list not found" });

  const { name, validFrom, validTo, isDefault, isActive } = req.body;

  if (name) {
    const duplicate = priceLists.find(p => p.name.toLowerCase() === name.toLowerCase() && p.id !== pl.id && p.tenantId === tenant.id && !p.isDeleted);
    if (duplicate) {
      return res.status(409).json({ error: `Price list with name '${name}' already exists` });
    }
    pl.name = name;
  }

  const fromDate = validFrom !== undefined ? validFrom : pl.validFrom;
  const toDate = validTo !== undefined ? validTo : pl.validTo;

  if (toDate && toDate < fromDate) {
    return res.status(422).json({ error: "Valid To date must be greater than or equal to Valid From date" });
  }

  if (validFrom !== undefined) pl.validFrom = validFrom;
  if (validTo !== undefined) pl.validTo = validTo || null;

  if (isActive !== undefined) {
    const activeBool = !!isActive;
    const currentIsDefault = isDefault !== undefined ? !!isDefault : pl.isDefault;
    if (!activeBool && currentIsDefault) {
      return res.status(422).json({ error: "Cannot deactivate the default price list without designating a new default first" });
    }
    pl.isActive = activeBool;
  }

  if (isDefault !== undefined) {
    const defaultBool = !!isDefault;
    if (defaultBool) {
      priceLists.forEach(p => {
        if (p.tenantId === tenant.id) p.isDefault = false;
      });
      pl.isDefault = true;
    } else {
      if (pl.isDefault) {
        const other = priceLists.find(p => p.id !== pl.id && p.tenantId === tenant.id && p.isActive && !p.isDeleted);
        if (other) {
          other.isDefault = true;
          pl.isDefault = false;
        } else {
          return res.status(422).json({ error: "A default price list must be assigned. Create/select another default list first." });
        }
      }
    }
  }

  res.json(pl);
});

app.post("/api/v1/sales/price-lists/:id/lines", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const pl = priceLists.find(p => p.id === req.params.id && p.tenantId === tenant.id && !p.isDeleted);
  if (!pl) return res.status(404).json({ error: "Price list not found" });

  const { productId, productType, unitPrice } = req.body;
  if (!productId || !productType || unitPrice === undefined) {
    return res.status(400).json({ error: "productId, productType, and unitPrice are required" });
  }

  const priceNum = Number(unitPrice);
  if (isNaN(priceNum) || priceNum < 0) {
    return res.status(422).json({ error: "Selling Price must be 0 or greater" });
  }
  if (priceNum > 999999999.99) {
    return res.status(422).json({ error: "Price exceeds the maximum allowed" });
  }

  const duplicate = pl.lines.find((l: any) => l.productId === productId);
  if (duplicate) {
    return res.status(409).json({ error: "This product already has a price entry in this price list" });
  }

  const newLine = {
    id: `pll-${Date.now()}`,
    productId,
    productType,
    unitPrice: priceNum
  };

  pl.lines.push(newLine);
  res.status(201).json(newLine);
});

app.patch("/api/v1/sales/price-lists/:id/lines", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const pl = priceLists.find(p => p.id === req.params.id && p.tenantId === tenant.id && !p.isDeleted);
  if (!pl) return res.status(404).json({ error: "Price list not found" });

  const { productId, unitPrice } = req.body;
  if (!productId || unitPrice === undefined) {
    return res.status(400).json({ error: "productId and unitPrice are required" });
  }

  const priceNum = Number(unitPrice);
  if (isNaN(priceNum) || priceNum < 0) {
    return res.status(422).json({ error: "Selling Price must be 0 or greater" });
  }
  if (priceNum > 999999999.99) {
    return res.status(422).json({ error: "Price exceeds the maximum allowed" });
  }

  const line = pl.lines.find((l: any) => l.productId === productId);
  if (!line) return res.status(404).json({ error: "Price list line not found" });

  line.unitPrice = priceNum;
  res.json(line);
});

app.delete("/api/v1/sales/price-lists/:id/lines/:productId", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const pl = priceLists.find(p => p.id === req.params.id && p.tenantId === tenant.id && !p.isDeleted);
  if (!pl) return res.status(404).json({ error: "Price list not found" });

  const index = pl.lines.findIndex((l: any) => l.productId === req.params.productId);
  if (index === -1) return res.status(404).json({ error: "Price list line not found" });

  pl.lines.splice(index, 1);
  res.status(204).send();
});

app.get("/api/v1/sales/orders", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const tenantSos = salesOrders.filter(s => s.tenantId === tenant.id);
  res.json(tenantSos);
});

app.post("/api/v1/sales/orders", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  if (!tenant) return res.status(401).json({ error: "Unauthorized" });

  const { clientId, lines, taxRate, discountAmount, deliveryDate } = req.body;
  if (!clientId || !lines || lines.length === 0) {
    return res.status(400).json({ error: "Client and order lines are required" });
  }

  const client = clients.find(c => c.id === clientId && c.tenantId === tenant.id);
  if (!client) return res.status(404).json({ error: "Client not found" });

  // Calculate order total with automatic price resolution if unitPrice is omitted, null or 0
  let subtotal = 0;
  const orderDate = new Date().toISOString().split('T')[0];
  
  for (const line of lines) {
    let price = line.unitPrice;
    if (price === undefined || price === null || Number(price) === 0) {
      try {
        price = resolvePrice(tenant.id, line.productId, clientId, orderDate);
        line.unitPrice = price;
      } catch (err: any) {
        return res.status(422).json({ error: err.message });
      }
    }
    subtotal += line.quantity * Number(price);
  }
  const tax = subtotal * ((taxRate || 0) / 100);
  const total = subtotal + tax - (discountAmount || 0);

  // Credit limit enforcement check
  if (client.creditUsed + total > client.creditLimit) {
    return res.status(400).json({ 
      error: `Order total is ${total}. Client has only ${(client.creditLimit - client.creditUsed)} available credit (Limit: ${client.creditLimit}, Used: ${client.creditUsed})` 
    });
  }

  const newSO: SalesOrder & { tenantId: string } = {
    id: `so-${Date.now()}`,
    orderNumber: `SO-${10000 + salesOrders.length + 1}`,
    clientId,
    status: "draft",
    orderDate,
    deliveryDate: deliveryDate || new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    lines,
    taxRate: taxRate || 0,
    discountAmount: discountAmount || 0,
    totalAmount: total,
    tenantId: tenant.id
  };

  salesOrders.push(newSO);
  res.status(201).json(newSO);
});

app.post("/api/v1/sales/orders/:id/confirm", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  const so = salesOrders.find(s => s.id === req.params.id && s.tenantId === tenant?.id);
  if (!so) return res.status(404).json({ error: "Sales order not found" });

  if (so.status !== "draft") {
    return res.status(400).json({ error: "Order must be in 'draft' status to confirm" });
  }

  // Update client credit usage
  const client = clients.find(c => c.id === so.clientId && c.tenantId === tenant?.id);
  if (client) {
    client.creditUsed += so.totalAmount;
  }

  so.status = "confirmed";
  res.json(so);
});

app.post("/api/v1/sales/orders/:id/ship", (req, res) => {
  const { tenant } = getTenantAndUser(req);
  const so = salesOrders.find(s => s.id === req.params.id && s.tenantId === tenant?.id);
  if (!so) return res.status(404).json({ error: "Sales order not found" });

  if (so.status !== "confirmed") {
    return res.status(400).json({ error: "Order must be 'confirmed' to ship" });
  }

  // Verify finished goods inventory and deduct shipped goods
  for (const line of so.lines) {
    const mat = materials.find(m => m.id === line.productId && m.tenantId === tenant?.id);
    if (!mat) return res.status(404).json({ error: `Product ID ${line.productId} not found in materials` });

    if (mat.stockLevel < line.quantity) {
      return res.status(400).json({ 
        error: `Insufficient stock for product '${mat.name}'. Available: ${mat.stockLevel}, Required: ${line.quantity}` 
      });
    }
  }

  // Perform deductions
  for (const line of so.lines) {
    const mat = materials.find(m => m.id === line.productId && m.tenantId === tenant?.id)!;
    mat.stockLevel -= line.quantity;
    stockAdjustments.push({
      id: `adj-${Date.now()}-ship-${mat.id}`,
      materialId: mat.id,
      quantity: line.quantity,
      type: "remove",
      location: mat.location,
      remarks: `Shipped for Sales Order ${so.orderNumber}`,
      timestamp: new Date().toISOString(),
      tenantId: tenant!.id
    });
  }

  so.status = "shipped";
  res.json(so);
});

// ==========================================
// STATIC ASSETS & VITE INTEGRATION
// ==========================================

async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: {
        middlewareMode: true,
        hmr: false,
        host: "0.0.0.0",
        port: DEFAULT_PORT,
        strictPort: false
      },
      appType: "spa"
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  const portCandidates = getPortCandidates(DEFAULT_PORT);
  let lastError: NodeJS.ErrnoException | null = null;

  for (const port of portCandidates) {
    try {
      await new Promise<void>((resolve, reject) => {
        const server = app.listen(port, "0.0.0.0", () => {
          console.log(`[MedTrack ERP] Server is actively running on port ${port}`);
          resolve();
        });

        server.on("error", (error: NodeJS.ErrnoException) => {
          if (error.code === "EADDRINUSE") {
            reject(error);
          } else {
            reject(error);
          }
        });
      });
      return;
    } catch (error) {
      lastError = error as NodeJS.ErrnoException;
      if (lastError.code !== "EADDRINUSE") {
        throw error;
      }
    }
  }

  throw lastError || new Error(`Unable to start server on ports ${portCandidates.join(", ")}`);
}

startServer().catch((error) => {
  console.error("Failed to start server:", error);
  process.exit(1);
});
