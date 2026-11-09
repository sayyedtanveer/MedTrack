# MedTrack Frontend Standards

**Version:** 1.0.0  
**Last Updated:** November 9, 2026  
**Technology Stack:** React 18.3.1, TypeScript 5.6.2, Vite 6.2.0, React Query 5.95.2, Tailwind CSS 3.4.19

---

## TypeScript Strict Mode (Mandatory)

All frontend code must be fully typed with TypeScript strict mode.

**TypeScript Configuration:**
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "noImplicitThis": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "alwaysStrict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

**✅ Correct:**
```typescript
interface Material {
  id: string;
  code: string;
  name: string;
  quantity: number;
  unit: string;
}

async function fetchMaterial(id: string): Promise<Material> {
  const response = await api.get<Material>(`/materials/${id}`);
  return response.data;
}

function MaterialCard({ material }: { material: Material }) {
  return <div>{material.name}</div>;
}
```

**❌ Wrong:**
```typescript
// No type on function parameter
function fetchMaterial(id) {
  return api.get(`/materials/${id}`);
}

// Implicit any
const data = api.get("/materials/123");

// No return type
function MaterialCard({ material }) {
  return <div>{material.name}</div>;
}

// Using any
const result: any = await api.get("/materials");
```

---

## Component Architecture

### Functional Components (React 18)

All components are functional components using hooks. No class components.

**✅ Correct:**
```typescript
// Fully typed functional component
interface MaterialCardProps {
  material: Material;
  onSelect?: (material: Material) => void;
}

export const MaterialCard: React.FC<MaterialCardProps> = ({
  material,
  onSelect,
}) => {
  const handleClick = () => {
    onSelect?.(material);
  };

  return (
    <div onClick={handleClick} className="p-4 border rounded">
      <h3>{material.name}</h3>
      <p>{material.code}</p>
      <p className="text-gray-600">{material.quantity}</p>
    </div>
  );
};
```

**❌ Wrong:**
```typescript
// Class component (legacy)
class MaterialCard extends React.Component {
  render() {
    return <div>{this.props.name}</div>;
  }
}

// Untyped component
export function MaterialCard(props) {
  return <div>{props.name}</div>;
}
```

### Module Organization

Each business domain is a self-contained module.

```
modules/{domain}/
├── pages/              # Page-level components (routed)
│   ├── MaterialListPage.tsx
│   ├── MaterialDetailPage.tsx
│   └── index.ts
├── components/         # Domain-specific components
│   ├── MaterialForm.tsx
│   ├── MaterialTable.tsx
│   ├── MaterialCard.tsx
│   ├── __tests__/
│   │   ├── MaterialForm.test.tsx
│   │   └── MaterialTable.test.tsx
│   └── index.ts
├── hooks/              # Custom React hooks
│   ├── useMaterials.ts
│   ├── useMaterialForm.ts
│   └── index.ts
├── services/           # API client functions
│   ├── material.service.ts
│   └── index.ts
├── types/              # TypeScript interfaces
│   ├── index.ts
│   └── material.types.ts
└── routes.tsx          # Route definitions for this module
```

**Example Module:**
```
modules/inventory/
├── pages/
│   ├── MaterialListPage.tsx
│   ├── MaterialDetailPage.tsx
│   ├── StorekeeperDashboardPage.tsx
│   └── MaterialOnboardingPage.tsx
├── components/
│   ├── MaterialTable.tsx
│   ├── MaterialForm.tsx
│   ├── LowStockAlert.tsx
│   ├── BatchSerialPanel.tsx
│   └── __tests__/
├── hooks/
│   ├── useMaterials.ts
│   ├── useMaterialDetail.ts
│   ├── useInventoryReservations.ts
│   └── useInventoryTransactions.ts
├── services/
│   ├── material.service.ts
│   ├── inventory.service.ts
│   └── batch-serial.service.ts
├── types/
│   ├── index.ts
│   └── inventory.types.ts
└── routes.tsx
```

---

## React Hooks Pattern

### Custom Hooks

Extract reusable logic into custom hooks. Hooks manage state, effects, and side effects.

**State Management Hook:**
```typescript
// modules/inventory/hooks/useMaterials.ts
interface UseMaterialsOptions {
  skip?: number;
  limit?: number;
}

interface UseMaterialsReturn {
  materials: Material[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export const useMaterials = (options: UseMaterialsOptions = {}): UseMaterialsReturn => {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await materialApi.list({
        skip: options.skip || 0,
        limit: options.limit || 100,
      });
      
      setMaterials(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setLoading(false);
    }
  }, [options.skip, options.limit]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { materials, loading, error, refetch: fetch };
};
```

**Form Hook:**
```typescript
// modules/inventory/hooks/useMaterialForm.ts
interface UseMaterialFormReturn {
  formState: {
    code: string;
    name: string;
    unit: string;
  };
  handleChange: (field: string, value: string) => void;
  handleSubmit: (e: React.FormEvent) => Promise<void>;
  isSubmitting: boolean;
  errors: Record<string, string>;
}

export const useMaterialForm = (): UseMaterialFormReturn => {
  const [formState, setFormState] = useState({
    code: "",
    name: "",
    unit: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleChange = (field: string, value: string) => {
    setFormState(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      setIsSubmitting(true);
      setErrors({});
      
      // Validate
      const newErrors = validateMaterialForm(formState);
      if (Object.keys(newErrors).length > 0) {
        setErrors(newErrors);
        return;
      }
      
      // Submit
      await materialApi.create(formState);
      
      // Reset on success
      setFormState({ code: "", name: "", unit: "" });
    } catch (err) {
      setErrors({
        submit: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return { formState, handleChange, handleSubmit, isSubmitting, errors };
};
```

**Component Using Hooks:**
```typescript
export const MaterialListPage: React.FC = () => {
  const { materials, loading, error, refetch } = useMaterials();
  const { showError } = useShowError();

  useEffect(() => {
    if (error) {
      showError(error);
    }
  }, [error, showError]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} onRetry={refetch} />;

  return (
    <div>
      <div className="flex justify-between mb-4">
        <h1>Materials</h1>
        <Button onClick={() => navigate("/materials/new")}>New Material</Button>
      </div>
      <MaterialTable materials={materials} />
    </div>
  );
};
```

### React Query Integration

Use React Query for server state management (fetching, caching, synchronization).

```typescript
// Configuration in app/providers/QueryProvider.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"

export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000, // 5 minutes
            retry: 1,
            refetchOnWindowFocus: false,
            throwOnError: false,
            gcTime: 10 * 60 * 1000,
          },
          mutations: {
            retry: 1,
            throwOnError: false,
          },
        },
      })
  )

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

// Usage in component
export const MaterialListPage: React.FC = () => {
  const { data: materials = [], isLoading, error } = useQuery({
    queryKey: ["materials"],
    queryFn: () => materialApi.list(),
  });

  const createMutation = useMutation({
    mutationFn: (newMaterial: CreateMaterialRequest) =>
      materialApi.create(newMaterial),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["materials"] });
      toast.success("Material created");
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : "Creation failed");
    },
  });

  return (
    <div>
      <MaterialTable materials={materials} />
      <MaterialForm onSubmit={createMutation.mutate} />
    </div>
  );
};
```

---

## API Service Layer

Create typed API client functions for all backend endpoints.

### Service File Pattern

```typescript
// modules/inventory/services/material.service.ts
import { api } from "@/services/api-client"

// ── Types ────────────────────────────────────────
export interface Material {
  id: string;
  code: string;
  name: string;
  quantity: number;
  unit_id: string;
  created_at: string;
}

export interface CreateMaterialRequest {
  code: string;
  name: string;
  unit_id: string;
}

// ── Service ──────────────────────────────────────
export const materialApi = {
  async list(options?: { skip?: number; limit?: number }): Promise<Material[]> {
    const response = await api.get<Material[]>("/inventory/materials", {
      params: options,
    });
    return response.data;
  },

  async get(id: string): Promise<Material> {
    const response = await api.get<Material>(`/inventory/materials/${id}`);
    return response.data;
  },

  async create(data: CreateMaterialRequest): Promise<Material> {
    const response = await api.post<Material>("/inventory/materials", data);
    return response.data;
  },

  async update(
    id: string,
    data: Partial<CreateMaterialRequest>
  ): Promise<Material> {
    const response = await api.put<Material>(`/inventory/materials/${id}`, data);
    return response.data;
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/inventory/materials/${id}`);
  },
};
```

### Axios Configuration

```typescript
// services/api-client.ts
import axios, { AxiosInstance, AxiosError } from "axios";

export const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api/v1",
  timeout: 30000,
});

// Request interceptor: Attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: Handle errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired, redirect to login
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
```

---

## Form Handling with React Hook Form

Use React Hook Form + Zod for type-safe forms.

**Schema Definition:**
```typescript
// lib/validations/index.ts
import { z } from "zod"

export const createMaterialSchema = z.object({
  code: z.string()
    .min(1, "Code required")
    .max(50, "Code too long")
    .regex(/^[A-Z0-9-]+$/, "Code must contain only uppercase letters, numbers, and hyphens"),
  name: z.string()
    .min(1, "Name required")
    .max(255, "Name too long"),
  unit_id: z.string()
    .uuid("Invalid unit ID"),
})

export type CreateMaterialInput = z.infer<typeof createMaterialSchema>

export const loginSchema = z.object({
  email: z.string().email("Invalid email"),
  password: z.string().min(6, "Password too short"),
})

export type LoginFormValues = z.infer<typeof loginSchema>
```

**Form Component:**
```typescript
// modules/inventory/components/MaterialForm.tsx
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { createMaterialSchema, CreateMaterialInput } from "@/lib/validations"

interface MaterialFormProps {
  onSubmit: (data: CreateMaterialInput) => Promise<void>;
  isSubmitting?: boolean;
}

export const MaterialForm: React.FC<MaterialFormProps> = ({
  onSubmit,
  isSubmitting = false,
}) => {
  const form = useForm<CreateMaterialInput>({
    resolver: zodResolver(createMaterialSchema),
    defaultValues: {
      code: "",
      name: "",
      unit_id: "",
    },
  })

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <Label htmlFor="code">Code</Label>
        <Input
          id="code"
          placeholder="MAT-001"
          disabled={isSubmitting}
          {...form.register("code")}
        />
        {form.formState.errors.code && (
          <p className="text-red-600 text-sm">
            {form.formState.errors.code.message}
          </p>
        )}
      </div>

      <div>
        <Label htmlFor="name">Name</Label>
        <Input
          id="name"
          placeholder="Steel Sheet"
          disabled={isSubmitting}
          {...form.register("name")}
        />
        {form.formState.errors.name && (
          <p className="text-red-600 text-sm">
            {form.formState.errors.name.message}
          </p>
        )}
      </div>

      <div>
        <Label htmlFor="unit_id">Unit</Label>
        <Select value={form.watch("unit_id")} onValueChange={(value) => form.setValue("unit_id", value)}>
          <SelectTrigger>
            <SelectValue placeholder="Select unit" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="kg">Kilogram</SelectItem>
            <SelectItem value="pcs">Piece</SelectItem>
            <SelectItem value="m">Meter</SelectItem>
          </SelectContent>
        </Select>
        {form.formState.errors.unit_id && (
          <p className="text-red-600 text-sm">
            {form.formState.errors.unit_id.message}
          </p>
        )}
      </div>

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Creating..." : "Create Material"}
      </Button>
    </form>
  )
}
```

---

## Routing

Module-based routing with lazy loading.

**Route Definition:**
```typescript
// modules/inventory/routes.tsx
import { lazy } from "react"
import { ProtectedRoute } from "@/app/routes/ProtectedRoute"

const MaterialListPage = lazy(() => import("./pages/MaterialListPage"))
const MaterialDetailPage = lazy(() => import("./pages/MaterialDetailPage"))

export const inventoryRoutes = [
  {
    path: "/inventory",
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <Suspense fallback={<LoadingSpinner />}><MaterialListPage /></Suspense>,
      },
      {
        path: ":id",
        element: <Suspense fallback={<LoadingSpinner />}><MaterialDetailPage /></Suspense>,
      },
    ],
  },
]
```

**Main Router:**
```typescript
// app/routes/index.tsx
import { createBrowserRouter, Suspense } from "react-router-dom"
import { inventoryRoutes } from "@/modules/inventory/routes"
import { manufacturingRoutes } from "@/modules/manufacturing/routes"
import { salesRoutes } from "@/modules/sales/routes"
// ... other module routes

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <AuthLayout />,
    children: [
      { index: true, element: <LoginPage /> },
    ],
  },
  {
    path: "/",
    element: <DefaultLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      ...inventoryRoutes,
      ...manufacturingRoutes,
      ...salesRoutes,
      // ... other routes
    ],
  },
])
```

---

## State Management

Use React hooks for component state and Context API for global state.

### Authentication Context

```typescript
// app/store/authContext.tsx
import { createContext, useContext, useState, useCallback } from "react"

interface User {
  id: string;
  email: string;
  tenant_id: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(false)

  const login = useCallback(async (credentials: LoginCredentials) => {
    setLoading(true)
    try {
      const response = await authApi.login(credentials)
      localStorage.setItem("token", response.access_token)
      setUser(response.user)
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem("token")
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider")
  }
  return context
}
```

---

## Shared Components Library

Reusable UI components in `components/shared/` and `components/ui/`.

**UI Components (Radix + Tailwind):**
```
components/ui/
├── button.tsx          # Button component
├── input.tsx           # Input field
├── label.tsx           # Form label
├── card.tsx            # Card wrapper
├── modal.tsx           # Modal dialog
├── select.tsx          # Select dropdown
├── table.tsx           # Data table
└── ... (20+ components)
```

**Shared Components:**
```
components/shared/
├── LoadingSpinner.tsx  # Loading indicator
├── ErrorMessage.tsx    # Error display
├── Sidebar.tsx         # Navigation sidebar
├── Header.tsx          # Page header
├── Pagination.tsx      # Table pagination
└── ... (domain-agnostic components)
```

**Layout Components:**
```
components/layout/
├── DefaultLayout.tsx   # Main app layout with sidebar + header
├── AuthLayout.tsx      # Login/register layout
├── PageLayout.tsx      # Standard page container
├── ErrorBoundary.tsx   # React error boundary
└── ErrorPages.tsx      # 404, 403 error pages
```

**Example Component:**
```typescript
// components/shared/LoadingSpinner.tsx
interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = "md",
  label = "Loading...",
}) => {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-8 h-8",
    lg: "w-12 h-12",
  }

  return (
    <div className="flex flex-col items-center justify-center gap-2">
      <div className={`${sizeClasses[size]} animate-spin`}>
        <Loader2 className="w-full h-full" />
      </div>
      {label && <p className="text-sm text-gray-600">{label}</p>}
    </div>
  )
}
```

---

## Error Handling

### Error Boundary

```typescript
// components/layout/ErrorBoundary.tsx
import { ReactNode } from "react"

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("Error caught by boundary:", error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="p-8 text-center">
            <h2 className="text-lg font-semibold text-red-600">Something went wrong</h2>
            <p className="text-gray-600 mt-2">{this.state.error?.message}</p>
            <Button onClick={() => window.location.reload()} className="mt-4">
              Reload Page
            </Button>
          </div>
        )
      )
    }

    return this.props.children
  }
}
```

### useShowError Hook

```typescript
// hooks/useShowError.ts
import { useCallback } from "react"
import { useToast } from "@/components/ui/use-toast"

interface ShowErrorOptions {
  title?: string;
  duration?: number;
}

export function useShowError() {
  const { toast } = useToast()

  const showError = useCallback(
    (error: Error | string, options: ShowErrorOptions = {}) => {
      const message =
        typeof error === "string" ? error : error.message || "An error occurred"

      toast({
        title: options.title || "Error",
        description: message,
        variant: "destructive",
        duration: options.duration || 5000,
      })
    },
    [toast]
  )

  return { showError }
}
```

---

## Styling with Tailwind CSS

Use Tailwind CSS utility classes for styling. Avoid custom CSS when possible.

```typescript
// ✅ Correct: Tailwind utilities
export const MaterialCard: React.FC<MaterialCardProps> = ({ material }) => {
  return (
    <div className="p-4 rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
      <h3 className="text-lg font-semibold text-gray-900">{material.name}</h3>
      <p className="text-sm text-gray-600 mt-1">{material.code}</p>
      <div className="mt-4 flex justify-between items-center">
        <span className="text-gray-700">{material.quantity}</span>
        <Badge variant="secondary">{material.unit}</Badge>
      </div>
    </div>
  )
}

// ❌ Wrong: Custom CSS
export const MaterialCard: React.FC<MaterialCardProps> = ({ material }) => {
  return (
    <div style={{ padding: "16px", borderRadius: "8px", border: "1px solid #e5e7eb" }}>
      <h3 style={{ fontSize: "18px", fontWeight: "600" }}>{material.name}</h3>
      <p style={{ fontSize: "12px", color: "#666" }}>{material.code}</p>
    </div>
  )
}
```

---

## Testing

### Component Tests

```typescript
// modules/inventory/components/__tests__/MaterialForm.test.tsx
import { render, screen, userEvent } from "@testing-library/react"
import { MaterialForm } from "../MaterialForm"

describe("MaterialForm", () => {
  it("renders form fields", () => {
    render(<MaterialForm onSubmit={jest.fn()} />)
    
    expect(screen.getByLabelText("Code")).toBeInTheDocument()
    expect(screen.getByLabelText("Name")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /create/i })).toBeInTheDocument()
  })

  it("submits form with valid data", async () => {
    const onSubmit = jest.fn()
    render(<MaterialForm onSubmit={onSubmit} />)
    
    const codeInput = screen.getByLabelText("Code") as HTMLInputElement
    const nameInput = screen.getByLabelText("Name") as HTMLInputElement
    const submitButton = screen.getByRole("button", { name: /create/i })
    
    await userEvent.type(codeInput, "MAT-001")
    await userEvent.type(nameInput, "Steel Sheet")
    await userEvent.click(submitButton)
    
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        code: "MAT-001",
        name: "Steel Sheet",
      })
    )
  })

  it("displays validation errors", async () => {
    render(<MaterialForm onSubmit={jest.fn()} />)
    
    const submitButton = screen.getByRole("button", { name: /create/i })
    await userEvent.click(submitButton)
    
    expect(screen.getByText("Code required")).toBeInTheDocument()
    expect(screen.getByText("Name required")).toBeInTheDocument()
  })
})
```

---

## Build & Development

### Vite Configuration

```typescript
// vite.config.ts
import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5000,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
    },
  },
})
```

### Development Commands

```bash
# Start dev server
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check

# Linting
npm run lint

# Format code
npm run format

# Run tests
npm run test
```

---

## Performance Optimization

### Code Splitting with React.lazy

```typescript
// app/routes/index.tsx
const MaterialListPage = lazy(() => import("@/modules/inventory/pages/MaterialListPage"))
const WorkOrderPage = lazy(() => import("@/modules/manufacturing/pages/WorkOrderPage"))

// Routes use Suspense
<Suspense fallback={<LoadingSpinner />}>
  <MaterialListPage />
</Suspense>
```

### Memoization

```typescript
// Only memoize expensive components
interface MaterialTableProps {
  materials: Material[];
  onSelect: (material: Material) => void;
}

export const MaterialTable = React.memo(
  ({ materials, onSelect }: MaterialTableProps) => {
    return (
      <table>
        {/* Table content */}
      </table>
    )
  },
  (prevProps, nextProps) => {
    // Custom comparison
    return (
      prevProps.materials === nextProps.materials &&
      prevProps.onSelect === nextProps.onSelect
    )
  }
)
```

### React Query Optimization

```typescript
// Use queryKey arrays for fine-grained cache invalidation
useQuery({
  queryKey: ["materials", { skip, limit }],
  queryFn: () => materialApi.list({ skip, limit }),
})

// Invalidate specific queries
queryClient.invalidateQueries({ queryKey: ["materials"] })
```

---

## Key Files Reference

- **Main Entry:** `frontend/src/main.tsx`
- **App Root:** `frontend/src/App.tsx`
- **Router:** `frontend/src/app/routes/index.tsx`
- **Query Provider:** `frontend/src/app/providers/QueryProvider.tsx`
- **API Client:** `frontend/src/services/api-client.ts`
- **Shared Components:** `frontend/src/components/`
- **Module Example:** `frontend/src/modules/inventory/`
- **TypeScript Config:** `tsconfig.json`
- **Vite Config:** `vite.config.ts`

---

## Summary of Patterns

| Pattern | Purpose | Example |
|---------|---------|---------|
| **Strict TypeScript** | Type safety | `interface Props { data: Material }` |
| **Functional Components** | React 18 | `const Comp: React.FC<Props> = ({ prop }) => {}` |
| **Custom Hooks** | Logic reuse | `const { data, loading } = useMaterials()` |
| **React Query** | Server state | `useQuery({ queryKey, queryFn })` |
| **API Services** | Type-safe HTTP | `materialApi.list()` → `Promise<Material[]>` |
| **React Hook Form** | Form validation | `useForm<Schema>({ resolver: zodResolver(schema) })` |
| **Lazy Loading** | Code splitting | `lazy(() => import('./Page'))` |
| **Error Boundary** | Error handling | `<ErrorBoundary><App /></ErrorBoundary>` |
| **Tailwind CSS** | Styling | `className="p-4 rounded-lg"` |
| **Module Routes** | Organization | `modules/{domain}/routes.tsx` |

---

## Common Pitfalls to Avoid

1. **❌ Don't use `any` types** — Always type variables and function parameters
2. **❌ Don't skip validation** — Use React Hook Form + Zod for all forms
3. **❌ Don't nest Context Providers** — Use a single Provider wrapper
4. **❌ Don't fetch in component render** — Use hooks or React Query
5. **❌ Don't hardcode API URLs** — Use environment variables
6. **❌ Don't ignore errors** — Show user-friendly error messages
7. **❌ Don't fetch on every render** — Use `useEffect` with dependency array
8. **❌ Don't mix inline styles** — Use Tailwind classes
9. **❌ Don't create new objects in render** — Memoize or use state
10. **❌ Don't forget error boundaries** — Wrap app and pages with `<ErrorBoundary>`
