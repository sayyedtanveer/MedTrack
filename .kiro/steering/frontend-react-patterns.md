---
name: "Frontend React & TypeScript Patterns"
description: "React 18 components, TypeScript strict mode, custom hooks, API clients, and state management patterns"
inclusion: fileMatch
fileMatchPattern:
  - "frontend/src/**/*.tsx"
  - "frontend/src/**/*.ts"
---

# Frontend React & TypeScript Patterns

**Canonical Reference:** [`AGENTS.md`](../../AGENTS.md) Sections 6, 10  
**Detailed Guide:** [`FRONTEND_STANDARDS.md`](../../docs/ai-guidelines/FRONTEND_STANDARDS.md)  
**File Organization:** See [`file-organization-standards.md`](./file-organization-standards.md) Section 2 for folder structure

---

## React 18 Best Practices

### Functional Components Only
```typescript
// ✅ Correct: Functional component
interface MaterialListProps {
  onSelect?: (material: Material) => void;
}

export const MaterialList: React.FC<MaterialListProps> = ({ onSelect }) => {
  const [materials, setMaterials] = useState<Material[]>([]);
  
  return <div>{/* JSX */}</div>;
};

// ❌ Wrong: Class component (deprecated pattern)
class MaterialList extends React.Component {
  render() {
    return <div>{/* JSX */}</div>;
  }
}
```

### TypeScript Strict Mode
**tsconfig.json enforces:**
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true
  }
}
```

**Rules:**
- ✅ Full type hints on props, state, returns
- ❌ No `any` types without explicit justification
- ❌ No implicit `any`
- ✅ Always type function parameters and returns

### Props and State Typing
```typescript
// ✅ Fully typed props
interface WorkOrderDetailProps {
  workOrderId: string;
  status: "draft" | "released" | "started" | "completed";
  onStatusChange?: (newStatus: string) => Promise<void>;
  children?: React.ReactNode;
}

// ✅ Fully typed state
const [materials, setMaterials] = useState<Material[]>([]);
const [loading, setLoading] = useState<boolean>(false);
const [error, setError] = useState<Error | null>(null);
```

---

## Custom Hooks Pattern

**Extract logic into reusable hooks:**
```typescript
interface UseMaterialsReturn {
  materials: Material[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export const useMaterials = (): UseMaterialsReturn => {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);
  
  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.materials.list();
      setMaterials(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Unknown error"));
    } finally {
      setLoading(false);
    }
  }, []);
  
  useEffect(() => {
    fetch();
  }, [fetch]);
  
  return { materials, loading, error, refetch: fetch };
};

// Usage in component
const Component = () => {
  const { materials, loading, error } = useMaterials();
  
  return (
    <div>
      {loading && <Spinner />}
      {error && <Error message={error.message} />}
      {materials.map(m => <Material key={m.id} data={m} />)}
    </div>
  );
};
```

---

## API Client Pattern

**Type-safe API clients in services/:**
```typescript
// services/materials.ts
interface Material {
  id: string;
  code: string;
  name: string;
  quantity: number;
  unitId: string;
}

export const materialApi = {
  async list(): Promise<Material[]> {
    const response = await api.get<Material[]>("/materials");
    return response.data;
  },
  
  async get(id: string): Promise<Material> {
    const response = await api.get<Material>(`/materials/${id}`);
    return response.data;
  },
  
  async create(data: CreateMaterialInput): Promise<Material> {
    const response = await api.post<Material>("/materials", data);
    return response.data;
  },
  
  async update(id: string, data: UpdateMaterialInput): Promise<Material> {
    const response = await api.put<Material>(`/materials/${id}`, data);
    return response.data;
  }
};

// Usage in hook
const useMaterialDetail = (id: string) => {
  const [material, setMaterial] = useState<Material | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await materialApi.get(id);
        setMaterial(data);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [id]);
  
  return { material, loading };
};
```

---

## Module Structure

**Each business domain is self-contained:**
```
frontend/src/modules/{domain}/
├── pages/              # Page-level components (routed)
│   ├── MaterialListPage.tsx
│   └── MaterialDetailPage.tsx
├── components/         # Domain-specific components
│   ├── MaterialForm.tsx
│   ├── MaterialTable.tsx
│   └── __tests__/
│       └── MaterialForm.test.tsx
├── hooks/              # Custom hooks for domain logic
│   ├── useMaterials.ts
│   └── useMaterialDetail.ts
├── services/           # API clients
│   └── materialApi.ts
├── types/              # TypeScript interfaces
│   └── material.ts
└── __tests__/          # Integration tests
    └── MaterialModule.integration.test.tsx
```

**Example: Sales Order Module**
```
frontend/src/modules/sales/
├── pages/
│   ├── SalesOrderListPage.tsx
│   ├── SalesOrderDetailPage.tsx
│   └── SalesOrderCreatePage.tsx
├── components/
│   ├── SalesOrderForm.tsx
│   ├── OrderLineTable.tsx
│   ├── OrderStatusBadge.tsx
│   └── __tests__/
│       ├── SalesOrderForm.test.tsx
│       └── OrderStatusBadge.test.tsx
├── hooks/
│   ├── useSalesOrders.ts
│   ├── useSalesOrderDetail.ts
│   └── useSalesOrderForm.ts
├── services/
│   └── salesOrderApi.ts
├── types/
│   ├── salesOrder.ts
│   └── orderLine.ts
└── __tests__/
    └── SalesOrderModule.integration.test.tsx
```

---

## State Management Patterns

### useState for Simple State
```typescript
const [count, setCount] = useState<number>(0);
const [isOpen, setIsOpen] = useState<boolean>(false);
```

### useReducer for Complex State
```typescript
interface FormState {
  values: Record<string, string>;
  errors: Record<string, string>;
  isSubmitting: boolean;
}

type FormAction = 
  | { type: "SET_VALUE"; field: string; value: string }
  | { type: "SET_ERROR"; field: string; error: string }
  | { type: "SET_SUBMITTING"; value: boolean };

const formReducer = (state: FormState, action: FormAction): FormState => {
  switch (action.type) {
    case "SET_VALUE":
      return { ...state, values: { ...state.values, [action.field]: action.value } };
    case "SET_ERROR":
      return { ...state, errors: { ...state.errors, [action.field]: action.error } };
    case "SET_SUBMITTING":
      return { ...state, isSubmitting: action.value };
    default:
      return state;
  }
};

const Form = () => {
  const [state, dispatch] = useReducer(formReducer, { values: {}, errors: {}, isSubmitting: false });
  
  const handleChange = (field: string, value: string) => {
    dispatch({ type: "SET_VALUE", field, value });
  };
  
  return <div>{/* JSX */}</div>;
};
```

### Context API for Global State
```typescript
interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  
  const login = useCallback(async (email: string, password: string) => {
    const result = await api.login(email, password);
    setUser(result.user);
  }, []);
  
  const logout = useCallback(() => {
    setUser(null);
  }, []);
  
  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
};
```

---

## Error Handling

### Error Boundaries
```typescript
interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  
  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }
  
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("Error caught:", error, info);
  }
  
  render() {
    if (this.state.hasError) {
      return <div>Something went wrong: {this.state.error?.message}</div>;
    }
    
    return this.props.children;
  }
}
```

### Try-Catch in Async Operations
```typescript
const handleSubmit = async (data: FormData) => {
  setLoading(true);
  try {
    const result = await api.create(data);
    setSuccess("Created successfully");
    // Update UI
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    setError(message);
    console.error("Submission failed:", err);
  } finally {
    setLoading(false);
  }
};
```

---

## Performance Optimization

### React.memo for Expensive Renders
```typescript
interface MaterialTableProps {
  materials: Material[];
  onSelect: (material: Material) => void;
}

// Prevent re-render if props unchanged
export const MaterialTable = React.memo<MaterialTableProps>(({ materials, onSelect }) => {
  return (
    <table>
      <tbody>
        {materials.map(m => (
          <tr key={m.id} onClick={() => onSelect(m)}>
            <td>{m.code}</td>
            <td>{m.name}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
});
```

### useCallback to Stabilize References
```typescript
const Component = () => {
  // Without useCallback: new function on every render
  const handleClick = () => { /* ... */ };
  
  // With useCallback: same reference unless dependencies change
  const handleClickMemo = useCallback(() => { /* ... */ }, [dependency]);
  
  return <ChildComponent onClick={handleClickMemo} />;
};
```

### useMemo to Prevent Expensive Computations
```typescript
const Component = () => {
  const [items, setItems] = useState<Item[]>([]);
  
  // Recomputed only when items changes
  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => a.name.localeCompare(b.name));
  }, [items]);
  
  return <List items={sortedItems} />;
};
```

---

## Testing Patterns

### Component Tests (Vitest)
```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { MaterialForm } from "./MaterialForm";

describe("MaterialForm", () => {
  it("submits form with valid data", async () => {
    const onSubmit = vi.fn();
    render(<MaterialForm onSubmit={onSubmit} />);
    
    const input = screen.getByLabelText("Code");
    fireEvent.change(input, { target: { value: "MAT-001" } });
    
    const button = screen.getByRole("button", { name: /submit/i });
    fireEvent.click(button);
    
    expect(onSubmit).toHaveBeenCalled();
  });
});
```

### Hook Tests
```typescript
import { renderHook, waitFor } from "@testing-library/react";
import { useMaterials } from "./useMaterials";

describe("useMaterials", () => {
  it("fetches materials on mount", async () => {
    const { result } = renderHook(() => useMaterials());
    
    expect(result.current.loading).toBe(true);
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    expect(result.current.materials).toHaveLength(> 0);
  });
});
```

---

## Key Checklist

When implementing frontend features:

- [ ] Components are functional, not class components
- [ ] All props and returns have type hints
- [ ] No `any` types without explicit justification
- [ ] Custom hooks extract reusable logic
- [ ] API clients are type-safe
- [ ] State management appropriate to scope (useState/useReducer/Context)
- [ ] Error boundaries wrap risky components
- [ ] Performance optimizations used sparingly (memo, useCallback, useMemo)
- [ ] Tests cover component + hook behavior
- [ ] Module structure matches domain boundaries

---

**Reference:** [`IMPLEMENTATION_WORKFLOW.md`](../../docs/ai-guidelines/IMPLEMENTATION_WORKFLOW.md)
