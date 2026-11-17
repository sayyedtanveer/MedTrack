/**
 * Price Suggestion Card Component
 * 
 * Displays pricing suggestions from the 6-level hierarchy with:
 * - Suggested price and pricing source
 * - Confidence level indicator
 * - Rationale/explanation
 * - Option to view full analysis
 */

import React, { useState } from 'react';
import { ChevronDown, AlertCircle, Check, TrendingUp, Zap } from 'lucide-react';
import { usePricingAnalysis } from '@/modules/procurement/hooks/usePricing';
import { PricingSuggestion } from '@/modules/procurement/services/pricingApi';

interface PriceSuggestionCardProps {
  materialId: string;
  supplierId: string;
  suggestion: PricingSuggestion | null;
  loading: boolean;
  onOverride?: (price: number) => void;
}

/**
 * Get color based on confidence level
 */
const getConfidenceColor = (level: string): string => {
  switch (level?.toUpperCase()) {
    case 'HIGH':
      return 'bg-green-50 border-green-200';
    case 'MEDIUM':
      return 'bg-yellow-50 border-yellow-200';
    case 'LOW':
      return 'bg-orange-50 border-orange-200';
    default:
      return 'bg-gray-50 border-gray-200';
  }
};

/**
 * Get badge color based on confidence level
 */
const getConfidenceBadgeColor = (level: string): string => {
  switch (level?.toUpperCase()) {
    case 'HIGH':
      return 'bg-green-100 text-green-800';
    case 'MEDIUM':
      return 'bg-yellow-100 text-yellow-800';
    case 'LOW':
      return 'bg-orange-100 text-orange-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

/**
 * Get icon for pricing source
 */
const getSourceIcon = (source: string): React.ReactNode => {
  switch (source?.toUpperCase()) {
    case 'SUPPLIER_AGREEMENT':
      return <Check className="w-4 h-4" />;
    case 'QUOTATION':
      return <Zap className="w-4 h-4" />;
    case 'PURCHASE_HISTORY':
      return <TrendingUp className="w-4 h-4" />;
    case 'BENCHMARK_ANY_SUPPLIER':
      return <TrendingUp className="w-4 h-4" />;
    case 'STANDARD_COST':
      return <AlertCircle className="w-4 h-4" />;
    default:
      return <AlertCircle className="w-4 h-4" />;
  }
};

/**
 * Format pricing source for display
 */
const formatSource = (source: string): string => {
  return source
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

export const PriceSuggestionCard: React.FC<PriceSuggestionCardProps> = ({
  materialId,
  supplierId,
  suggestion,
  loading,
  onOverride,
}) => {
  const [showAnalysis, setShowAnalysis] = useState(false);
  const { analysis, loading: analysisLoading } = usePricingAnalysis(
    materialId,
    supplierId,
    showAnalysis
  );

  if (loading) {
    return (
      <div className="border rounded-lg p-4 bg-gray-50 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-2"></div>
        <div className="h-8 bg-gray-200 rounded w-1/4 mb-2"></div>
        <div className="h-4 bg-gray-200 rounded w-2/3"></div>
      </div>
    );
  }

  if (!suggestion) {
    return (
      <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-gray-500 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="font-medium text-gray-900">No Pricing Available</h4>
            <p className="text-sm text-gray-600 mt-1">
              No pricing found from any source. Manual pricing required. 
              <span className="block mt-1">Level 6: Manual (No suggestion)</span>
            </p>
          </div>
        </div>
      </div>
    );
  }

  const levelDescriptions: Record<number, string> = {
    1: 'Active supplier agreement (highest priority)',
    2: 'Approved supplier quotation',
    3: 'Latest purchase from same supplier',
    4: 'Market benchmark (any supplier)',
    5: 'Approved standard cost',
    6: 'Manual pricing (no suggestion)',
  };

  return (
    <div className={`border rounded-lg p-4 ${getConfidenceColor(suggestion.confidence_level)}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h4 className="font-semibold text-gray-900">Suggested Price</h4>
          <p className="text-sm text-gray-600 mt-1">Level {suggestion.level_number}: {levelDescriptions[suggestion.level_number as keyof typeof levelDescriptions]}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getConfidenceBadgeColor(suggestion.confidence_level)}`}>
          {suggestion.confidence_level} Confidence
        </span>
      </div>

      {/* Price Display */}
      <div className="bg-white rounded-lg p-3 mb-4 border border-gray-200">
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold text-gray-900">
            {Number(suggestion.suggested_price).toFixed(2)}
          </span>
          {suggestion.currency_code && (
            <span className="text-lg text-gray-600">{suggestion.currency_code}</span>
          )}
        </div>
      </div>

      {/* Source Information */}
      <div className="mb-4 flex items-center gap-2">
        <div className="w-5 h-5 text-blue-600">
          {getSourceIcon(suggestion.pricing_source)}
        </div>
        <span className="text-sm font-medium text-gray-700">
          {formatSource(suggestion.pricing_source)}
        </span>
        {suggestion.source_date && (
          <span className="text-xs text-gray-500">
            ({new Date(suggestion.source_date).toLocaleDateString()})
          </span>
        )}
      </div>

      {/* Rationale */}
      <div className="mb-4 p-3 bg-white rounded border border-gray-200">
        <p className="text-sm text-gray-700">{suggestion.rationale}</p>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => setShowAnalysis(!showAnalysis)}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-gray-300 rounded text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition"
        >
          View Full Analysis
          <ChevronDown
            className={`w-4 h-4 transition-transform ${showAnalysis ? 'rotate-180' : ''}`}
          />
        </button>
        {onOverride && (
          <button
            onClick={() => onOverride(Number(suggestion.suggested_price))}
            className="flex-1 px-3 py-2 border border-gray-300 rounded text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition"
          >
            Accept & Use Price
          </button>
        )}
      </div>

      {/* Full Analysis */}
      {showAnalysis && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          {analysisLoading ? (
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              <div className="h-4 bg-gray-200 rounded w-2/3"></div>
            </div>
          ) : analysis ? (
            <PricingAnalysisView analysis={analysis} />
          ) : (
            <p className="text-sm text-gray-600">Failed to load analysis</p>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Pricing Analysis View - shows all 6 levels
 */
interface PricingAnalysisViewProps {
  analysis: any;
}

const PricingAnalysisView: React.FC<PricingAnalysisViewProps> = ({ analysis }) => {
  const levels = [
    {
      number: 1,
      title: 'Supplier Agreement',
      price: analysis.level_1_agreement_price,
      status: analysis.level_1_agreement_status,
    },
    {
      number: 2,
      title: 'Quotation',
      price: analysis.level_2_quotation_price,
      status: analysis.level_2_quotation_status,
    },
    {
      number: 3,
      title: 'Purchase History (Same Supplier)',
      price: analysis.level_3_grn_price,
      date: analysis.level_3_grn_date,
    },
    {
      number: 4,
      title: 'Benchmarking (Any Supplier)',
      price: analysis.level_4_benchmark_price,
    },
    {
      number: 5,
      title: 'Standard Cost',
      price: analysis.level_5_standard_cost,
      status: analysis.level_5_standard_cost_status,
    },
  ];

  return (
    <div className="space-y-2">
      <h5 className="font-medium text-gray-900 mb-3">All 6 Pricing Levels</h5>
      {levels.map((level) => (
        <div key={level.number} className="flex items-center justify-between p-2 bg-white rounded border border-gray-200">
          <div>
            <span className="text-sm font-medium text-gray-900">
              Level {level.number}: {level.title}
            </span>
            {level.status && (
              <p className="text-xs text-gray-500">Status: {level.status}</p>
            )}
            {level.date && (
              <p className="text-xs text-gray-500">Date: {new Date(level.date).toLocaleDateString()}</p>
            )}
          </div>
          <div>
            {level.price ? (
              <span className="text-sm font-semibold text-gray-900">
                ${Number(level.price).toFixed(2)}
              </span>
            ) : (
              <span className="text-xs text-gray-400">—</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
