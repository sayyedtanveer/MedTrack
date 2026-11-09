---
trigger: glob
globs: "frontend/src/**/*.tsx, frontend/src/**/*.ts"
description: "Frontend React/TypeScript patterns: React 18, strict TypeScript, custom hooks, functional components"
---

# Frontend React & TypeScript Patterns

**Reference:** See `docs/ai-guidelines/FRONTEND_STANDARDS.md` for comprehensive patterns

## Functional Components Only (React 18)

```typescript
// ✅ Correct: Functional component, fully typed
interface MaterialListProps {
  onSelect?: (material: Material) => void;
}

export const MaterialList: React.FC<MaterialListProps> = ({ onSelect }) => {
  const [materials, setMaterials] = useState<Material[]>([]);
  return <div>{/* JSX */}</div>;
};

// ❌ WRONG: Class component (deprecated)
class MaterialList extends React.Component {
  render() {
    return <div>{/* JSX */}</div>;
  }
}
```

## TypeScript Strict Mode (REQUIRED)

```typescript
// ✅ Full type hints
interface WorkOrderDetailProps {
  workOrderId: string;
  status: "draft" | "released" | "started" | "completed";
  onStatusChange?: (newStatus: string) => Promise<void>;
}

const [materials, setMaterials] = useState<Material[]>([]);
const [loading, setLoading] = useState<boolean>(false);

// ❌ WRONG: No `any` types
const data: any = response.data;  // Violates strict mode
```

## Custom Hooks Pattern

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
```

## Type-Safe API Clients

```typescript
// services/materials.ts
interface Material {
  id: string;
  code: string;
  name: string;
  quantity: number;
}

export const materialApi = {
  async list(): Promise<Material[]> {
    const response = await api.get<Material[]>("/materials");
    return response.data;
  },
  
  async create(data: CreateMaterialInput): Promise<Material> {
    const response = await api.post<Material>("/materials", data);
    return response.data;
  }
};
```

## Module Structure

```
frontend/src/modules/{domain}/
├── pages/              # Page-level components (routed)
├── components/         # Domain-specific components
├── hooks/              # Custom hooks for domain logic
├── services/           # API client functions
├── types/              # TypeScript interfaces
└── __tests__/          # Component and hook tests
```

## State Management

**Simple state: `useState`**
```typescript
const [count, setCount] = useState<number>(0);
```

**Complex state: `useReducer`**
```typescript
const [state, dispatch] = useReducer(formReducer, initialState);
```

**Global state: `Context API`**
```typescript
const AuthContext = createContext<AuthContextType | undefined>(undefined);
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
};
```

## Error Handling

```typescript
// Error boundaries for risky components
export class ErrorBoundary extends React.Component {
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
}

// Try-catch in async operations
const handleSubmit = async (data: FormData) => {
  try {
    const result = await api.create(data);
    setSuccess("Created successfully");
  } catch (err) {
    setError(err instanceof Error ? err.message : "Unknown error");
  }
};
```

## Performance Optimization (Use Sparingly)

```typescript
// React.memo for expensive renders
export const MaterialTable = React.memo<MaterialTableProps>(({ materials }) => (
  <table>{/* JSX */}</table>
));

// useCallback to stabilize references
const handleClickMemo = useCallback(() => { /* ... */ }, [dependency]);

// useMemo for expensive computations
const sortedItems = useMemo(() => {
  return [...items].sort((a, b) => a.name.localeCompare(b.name));
}, [items]);
```

