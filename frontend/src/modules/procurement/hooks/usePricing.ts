/**
 * Custom React hooks for procurement pricing.
 * 
 * Provides data fetching, state management, and business logic for pricing features.
 */

import { useEffect, useState, useCallback } from 'react';
import { pricingApi, PricingSuggestion, PricingAnalysis, OverrideRecord, OverrideStatistics, OverrideTrend } from '@/modules/procurement/services/pricingApi';

interface UsePricingSuggestionsReturn {
  suggestion: PricingSuggestion | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch 6-level pricing suggestions for a material-supplier pair.
 * 
 * Levels (in priority order):
 * 1. Active supplier agreement (HIGH confidence)
 * 2. Approved quotation (MEDIUM confidence)
 * 3. Latest purchase same supplier (MEDIUM confidence)
 * 4. Latest purchase any supplier - benchmarking (LOW confidence)
 * 5. Approved standard cost (LOW confidence)
 * 6. Manual (no suggestion)
 */
export const usePricingSuggestions = (
  materialId: string | undefined,
  supplierId: string | undefined,
  enabled: boolean = true
): UsePricingSuggestionsReturn => {
  const [suggestion, setSuggestion] = useState<PricingSuggestion | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async () => {
    if (!materialId || !supplierId || !enabled) {
      setSuggestion(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await pricingApi.getSixLevelSuggestions(materialId, supplierId);
      setSuggestion(data);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch pricing suggestions');
      setError(error);
      setSuggestion(null);
    } finally {
      setLoading(false);
    }
  }, [materialId, supplierId, enabled]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { suggestion, loading, error, refetch: fetch };
};

interface UsePricingAnalysisReturn {
  analysis: PricingAnalysis | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch detailed analysis of all 6 pricing levels.
 * Shows what's available at each level for transparency.
 */
export const usePricingAnalysis = (
  materialId: string | undefined,
  supplierId: string | undefined,
  enabled: boolean = true
): UsePricingAnalysisReturn => {
  const [analysis, setAnalysis] = useState<PricingAnalysis | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async () => {
    if (!materialId || !supplierId || !enabled) {
      setAnalysis(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await pricingApi.getSixLevelAnalysis(materialId, supplierId);
      setAnalysis(data);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch pricing analysis');
      setError(error);
      setAnalysis(null);
    } finally {
      setLoading(false);
    }
  }, [materialId, supplierId, enabled]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { analysis, loading, error, refetch: fetch };
};

interface UseOverrideHistoryReturn {
  history: OverrideRecord[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch price override history for a material-supplier pair.
 * Shows all overrides in reverse chronological order.
 */
export const useOverrideHistory = (
  materialId: string | undefined,
  supplierId: string | undefined,
  enabled: boolean = true
): UseOverrideHistoryReturn => {
  const [history, setHistory] = useState<OverrideRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async () => {
    if (!materialId || !supplierId || !enabled) {
      setHistory([]);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await pricingApi.getOverrideHistory(materialId, supplierId);
      setHistory(data);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch override history');
      setError(error);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  }, [materialId, supplierId, enabled]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { history, loading, error, refetch: fetch };
};

interface UseOverrideStatisticsReturn {
  statistics: OverrideStatistics | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch override statistics.
 * Useful for compliance audits and cost analysis.
 */
export const useOverrideStatistics = (
  materialId: string | undefined,
  supplierId: string | undefined,
  enabled: boolean = true
): UseOverrideStatisticsReturn => {
  const [statistics, setStatistics] = useState<OverrideStatistics | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async () => {
    if (!materialId || !supplierId || !enabled) {
      setStatistics(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await pricingApi.getOverrideStatistics(materialId, supplierId);
      setStatistics(data);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch override statistics');
      setError(error);
      setStatistics(null);
    } finally {
      setLoading(false);
    }
  }, [materialId, supplierId, enabled]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { statistics, loading, error, refetch: fetch };
};

interface UseOverrideTrendsReturn {
  trend: OverrideTrend | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch price override trends over time.
 * Helps identify pricing patterns (e.g., consistent discounts).
 */
export const useOverrideTrends = (
  materialId: string | undefined,
  supplierId: string | undefined,
  enabled: boolean = true
): UseOverrideTrendsReturn => {
  const [trend, setTrend] = useState<OverrideTrend | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async () => {
    if (!materialId || !supplierId || !enabled) {
      setTrend(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await pricingApi.getOverrideTrends(materialId, supplierId);
      setTrend(data);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch override trends');
      setError(error);
      setTrend(null);
    } finally {
      setLoading(false);
    }
  }, [materialId, supplierId, enabled]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { trend, loading, error, refetch: fetch };
};

interface UseRecordOverrideReturn {
  recording: boolean;
  error: Error | null;
  recordOverride: (
    materialId: string,
    supplierId: string,
    originalPrice: number,
    overridePrice: number,
    reason?: string,
    source?: string
  ) => Promise<OverrideRecord | null>;
}

/**
 * Hook to record a price override.
 * Called when user overrides the suggested price.
 */
export const useRecordOverride = (): UseRecordOverrideReturn => {
  const [recording, setRecording] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const recordOverride = useCallback(
    async (
      materialId: string,
      supplierId: string,
      originalPrice: number,
      overridePrice: number,
      reason?: string,
      source?: string
    ): Promise<OverrideRecord | null> => {
      setRecording(true);
      setError(null);
      try {
        const result = await pricingApi.recordOverride(
          materialId,
          supplierId,
          originalPrice,
          overridePrice,
          reason,
          source
        );
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to record price override');
        setError(error);
        return null;
      } finally {
        setRecording(false);
      }
    },
    []
  );

  return { recording, error, recordOverride };
};

interface UsePricingDashboardReturn {
  suggestion: PricingSuggestion | null;
  analysis: PricingAnalysis | null;
  history: OverrideRecord[];
  statistics: OverrideStatistics | null;
  trend: OverrideTrend | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Composite hook for complete pricing dashboard.
 * Fetches all pricing data for a material-supplier pair.
 */
export const usePricingDashboard = (
  materialId: string | undefined,
  supplierId: string | undefined,
  enabled: boolean = true
): UsePricingDashboardReturn => {
  const suggestions = usePricingSuggestions(materialId, supplierId, enabled);
  const analysis = usePricingAnalysis(materialId, supplierId, enabled);
  const historyData = useOverrideHistory(materialId, supplierId, enabled);
  const stats = useOverrideStatistics(materialId, supplierId, enabled);
  const trendData = useOverrideTrends(materialId, supplierId, enabled);

  const loading = suggestions.loading || analysis.loading || historyData.loading || stats.loading || trendData.loading;
  const error = suggestions.error || analysis.error || historyData.error || stats.error || trendData.error;

  const refetch = useCallback(async () => {
    await Promise.all([
      suggestions.refetch(),
      analysis.refetch(),
      historyData.refetch(),
      stats.refetch(),
      trendData.refetch(),
    ]);
  }, [suggestions, analysis, historyData, stats, trendData]);

  return {
    suggestion: suggestions.suggestion,
    analysis: analysis.analysis,
    history: historyData.history,
    statistics: stats.statistics,
    trend: trendData.trend,
    loading,
    error,
    refetch,
  };
};
