import { useCallback, useEffect, useState } from "react";

/**
 * Configuration options for useApiList hook
 */
export interface UseApiListOptions<T> {
  page?: number;
  pageSize?: number;
  /**
   * Optional function to transform/filter items after fetching
   * Useful for client-side filtering or grouping
   */
  transformData?: (items: T[]) => T[];
}

/**
 * Return type for useApiList hook
 */
export interface UseApiListReturn<T> {
  items: T[];
  total: number;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Generic reusable hook for fetching paginated lists from API
 * 
 * Eliminates duplicate fetch + transform logic across modules.
 * Supports client-side data transformation and error handling.
 * 
 * @example
 * ```typescript
 * const { items, loading, error } = useApiList(
 *   (page, size) => materialApi.list({ page, page_size: size }),
 *   { pageSize: 50 }
 * );
 * ```
 */
export const useApiList = <T,>(
  apiFn: (page: number, pageSize: number) => Promise<{ items: T[]; total: number }>,
  options?: UseApiListOptions<T>
): UseApiListReturn<T> => {
  const [items, setItems] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const page = options?.page || 1;
  const pageSize = options?.pageSize || 20;

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await apiFn(page, pageSize);
      const transformedItems = options?.transformData
        ? options.transformData(result.items)
        : result.items;
      setItems(transformedItems);
      setTotal(result.total);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to fetch data";
      setError(new Error(errorMessage));
      console.error("Error fetching data:", err);
    } finally {
      setLoading(false);
    }
  }, [apiFn, page, pageSize, options]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { items, total, loading, error, refetch: fetch };
};
