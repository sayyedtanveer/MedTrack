---
applyTo: |
  frontend/**/*.tsx
  frontend/**/*.ts
---

# Frontend Development Instructions

**File:** `.github/instructions/frontend.instructions.md`  
**Scope:** React components and TypeScript in `frontend/src/` directory  
**Reference:** [AGENTS.md](../../AGENTS.md) § 10 (Frontend Implementation Rules)  
**Updated:** November 9, 2026

---

## Quick Rules

1. **Full TypeScript types** — No `any`, all props/returns typed
2. **Functional components only** — No class components
3. **Async/await for I/O** — Never use synchronous calls
4. **React hooks for logic** — Extract state/side-effects into custom hooks
5. **Error boundaries** — Wrap error-prone components
6. **Vite + Tailwind** — Use existing build/style tools
7. **Testing with Vitest** — Mock API responses, test hooks/components

---

## TypeScript Strict Mode (Mandatory)

**All code must have full type hints:**

```typescript
// ✅ CORRECT: Fully typed
interface MaterialListProps {
  tenantId: string;
  onSelect?: (id: string) => void;
  loading?: boolean;
}

export const MaterialList: React.FC<MaterialListProps> = ({
  tenantId,
  onSelect,
  loading = false
}) => {
  return <div>{/* JSX */}</div>;
};

// ❌ WRONG: No types or 'any'
export const MaterialList = ({ tenantId, onSelect, loading }: any) => {
  return <div>{/* JSX */}</div>;
};
```

**Rule:** Never suggest code with `any` type. Always include `React.FC<Props>` signature.

---

## Functional Components Only

**Use only functional components; no class components:**

```typescript
// ✅ CORRECT: Functional component
export const WorkOrderForm: React.FC<WorkOrderFormProps> = (props) => {
  const [formData, setFormData] = React.useState<FormData>({});
  return <form>{/* JSX */}</form>;
};

// ❌ WRONG: Class component
class WorkOrderForm extends React.Component<WorkOrderFormProps> {
  render() {
    return <form>{/* JSX */}</form>;
  }
}
```

---

## React Hooks Pattern

**Extract logic into custom hooks for reusability:**

```typescript
// ✅ CORRECT: Custom hook for data fetching
interface UseMaterialsReturn {
  materials: Material[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export const useMaterials = (tenantId: string): UseMaterialsReturn => {
  const [materials, setMaterials] = React.useState<Material[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<Error | null>(null);
  
  React.useEffect(() => {
    const fetch = async () => {
      try {
        const data = await api.materials.list(tenantId);
        setMaterials(data);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Unknown error'));
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [tenantId]);
  
  const refetch = async () => {
    setLoading(true);
    try {
      const data = await api.materials.list(tenantId);
      setMaterials(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setLoading(false);
    }
  };
  
  return { materials, loading, error, refetch };
};

// Use in component
export const MaterialList: React.FC = () => {
  const { materials, loading, error, refetch } = useMaterials('tenant-id');
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  return <MaterialTable materials={materials} />;
};
```

---

## API Client Pattern

**Type-safe API clients in `services/`:**

```typescript
// ✅ CORRECT: Type-safe API client
interface Material {
  id: string;
  code: string;
  name: string;
  quantity: number;
  unitId: string;
}

export const materialApi = {
  async list(tenantId: string): Promise<Material[]> {
    const response = await api.get<Material[]>('/materials', {
      params: { tenantId }
    });
    return response.data;
  },
  
  async get(id: string): Promise<Material> {
    const response = await api.get<Material>(`/materials/${id}`);
    return response.data;
  },
  
  async create(data: CreateMaterialRequest): Promise<Material> {
    const response = await api.post<Material>('/materials', data);
    return response.data;
  }
};

// Usage in component
const material = await materialApi.get(materialId);
```

**Rule:** Always define request/response interfaces. Never suggest untyped API calls.

---

## Error Handling

**Explicit error handling in components:**

```typescript
// ✅ CORRECT: Error handling with fallback
export const MaterialList: React.FC = () => {
  const [materials, setMaterials] = React.useState<Material[]>([]);
  const [error, setError] = React.useState<Error | null>(null);
  
  React.useEffect(() => {
    const fetch = async () => {
      try {
        const data = await api.materials.list();
        setMaterials(data);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Unknown error'));
        console.error('Failed to fetch materials:', err);
      }
    };
    fetch();
  }, []);
  
  if (error) {
    return (
      <ErrorBoundary>
        <ErrorMessage 
          error={error}
          onRetry={() => location.reload()}
        />
      </ErrorBoundary>
    );
  }
  
  return <MaterialTable materials={materials} />;
};

// ❌ WRONG: No error handling
export const MaterialList: React.FC = () => {
  const [materials, setMaterials] = React.useState<Material[]>([]);
  
  React.useEffect(() => {
    api.materials.list().then(setMaterials);  // Silent failure if error
  }, []);
  
  return <MaterialTable materials={materials} />;
};
```

---

## Error Boundaries

**Wrap error-prone components:**

```typescript
// ✅ CORRECT: Error boundary
interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  
  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }
  
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Component error:', error, errorInfo);
  }
  
  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} />;
    }
    return this.props.children;
  }
}
```

---

## Module Structure

**Each domain module is self-contained:**

```
frontend/src/modules/inventory/
├── pages/                    # Page-level components (routed)
│   ├── MaterialListPage.tsx
│   ├── MaterialDetailPage.tsx
│   └── MaterialFormPage.tsx
├── components/               # Domain-specific components
│   ├── MaterialTable.tsx
│   ├── MaterialForm.tsx
│   └── MaterialCard.tsx
├── hooks/                    # Custom React hooks
│   ├── useMaterials.ts
│   ├── useMaterialForm.ts
│   └── useMaterialDetail.ts
├── services/                 # API client functions
│   └── materialApi.ts
├── types/                    # TypeScript interfaces
│   └── material.types.ts
└── __tests__/               # Tests
    ├── MaterialTable.test.tsx
    ├── useMaterials.test.ts
    └── materialApi.test.ts
```

---

## State Management

**Use appropriate state management based on scope:**

```typescript
// useState: Simple, isolated state
const [count, setCount] = React.useState(0);

// useReducer: Complex component state
const [state, dispatch] = React.useReducer(reducer, initialState);

// Context API: Cross-component state (auth, theme)
const TenantContext = React.createContext<{ tenantId: string } | null>(null);

// Custom hooks: Shared logic patterns
export const useTenant = () => {
  const context = React.useContext(TenantContext);
  if (!context) throw new Error('useTenant must be used within TenantProvider');
  return context;
};
```

---

## Component Props Pattern

**Always define props interface:**

```typescript
// ✅ CORRECT: Props interface
interface WorkOrderTableProps {
  workOrders: WorkOrder[];
  loading: boolean;
  onSelect: (id: string) => void;
  onDelete?: (id: string) => Promise<void>;
  sortBy?: keyof WorkOrder;
}

export const WorkOrderTable: React.FC<WorkOrderTableProps> = ({
  workOrders,
  loading,
  onSelect,
  onDelete,
  sortBy = 'createdAt'
}) => {
  // Implementation
};

// Usage with type safety
<WorkOrderTable
  workOrders={orders}
  loading={isLoading}
  onSelect={handleSelect}
  onDelete={handleDelete}
  sortBy="code"  // ✅ Type-checked
/>
```

---

## Testing Pattern

**Test components, hooks, and API clients:**

```typescript
// ✅ CORRECT: Component test
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MaterialList } from './MaterialList';

describe('MaterialList', () => {
  it('renders materials', async () => {
    vi.mocked(api.materials.list).mockResolvedValue([
      { id: '1', code: 'MAT-001', name: 'Steel', quantity: 100, unitId: '1' }
    ]);
    
    render(<MaterialList tenantId="tenant-1" />);
    
    await waitFor(() => {
      expect(screen.getByText('Steel')).toBeInTheDocument();
    });
  });
  
  it('handles error gracefully', async () => {
    vi.mocked(api.materials.list).mockRejectedValue(new Error('API Error'));
    
    render(<MaterialList tenantId="tenant-1" />);
    
    await waitFor(() => {
      expect(screen.getByText(/failed/i)).toBeInTheDocument();
    });
  });
});

// ✅ CORRECT: Hook test
import { renderHook, waitFor } from '@testing-library/react';
import { useMaterials } from './useMaterials';

describe('useMaterials', () => {
  it('fetches and returns materials', async () => {
    vi.mocked(api.materials.list).mockResolvedValue([
      { id: '1', code: 'MAT-001', name: 'Steel', quantity: 100, unitId: '1' }
    ]);
    
    const { result } = renderHook(() => useMaterials('tenant-1'));
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.materials).toHaveLength(1);
    });
  });
});
```

---

## Styling with Tailwind

**Use Tailwind utility classes:**

```typescript
// ✅ CORRECT: Tailwind classes
export const MaterialCard: React.FC<MaterialCardProps> = ({ material }) => {
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold text-gray-900">{material.name}</h3>
      <p className="text-sm text-gray-500 mt-1">{material.code}</p>
      <div className="mt-4 flex justify-between items-center">
        <span className="text-2xl font-bold text-blue-600">
          {material.quantity}
        </span>
        <button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          Edit
        </button>
      </div>
    </div>
  );
};

// ❌ WRONG: Inline styles
export const MaterialCard: React.FC<MaterialCardProps> = ({ material }) => {
  return (
    <div style={{
      backgroundColor: 'white',
      border: '1px solid #e5e7eb',
      borderRadius: '8px',
      padding: '16px'
    }}>
      {/* ... */}
    </div>
  );
};
```

---

## Accessibility Compliance

**Include ARIA labels and semantic HTML:**

```typescript
// ✅ CORRECT: Accessible component
export const Button: React.FC<ButtonProps> = ({
  onClick,
  children,
  disabled,
  ariaLabel
}) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
    >
      {children}
    </button>
  );
};

// ✅ CORRECT: Semantic form
export const MaterialForm: React.FC = () => {
  return (
    <form>
      <label htmlFor="code">Material Code</label>
      <input
        id="code"
        type="text"
        required
        aria-required="true"
      />
      
      <label htmlFor="name">Material Name</label>
      <input
        id="name"
        type="text"
        required
        aria-required="true"
      />
    </form>
  );
};
```

---

## Do's and Don'ts

| Do | Don't |
|----|-------|
| ✅ Define `React.FC<Props>` type | ❌ Use `any` type |
| ✅ Extract logic into custom hooks | ❌ Mix logic with JSX |
| ✅ Use `async/await` for API calls | ❌ Use `.then()` chains |
| ✅ Handle errors explicitly | ❌ Ignore promise rejections |
| ✅ Test component behavior | ❌ Skip testing |
| ✅ Use Tailwind for styling | ❌ Inline styles or CSS files |
| ✅ Wrap risky components | ❌ Let errors crash entire app |
| ✅ Inspect existing patterns first | ❌ Invent new patterns |

---

## Reference

- **Full Frontend Guide:** [FRONTEND_STANDARDS.md](../../docs/ai-guidelines/FRONTEND_STANDARDS.md)
- **React Patterns:** [AGENTS.md § 10](../../AGENTS.md)
- **Testing Setup:** `frontend/src/test/` and `vitest.config.ts`
- **Component Examples:** `frontend/src/modules/*/components/`

---

**Status:** Production Ready  
**Last Updated:** November 9, 2026
