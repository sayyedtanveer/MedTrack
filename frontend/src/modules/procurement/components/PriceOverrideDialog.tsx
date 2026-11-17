/**
 * Price Override Dialog Component
 * 
 * Modal dialog for recording price overrides with:
 * - Original suggested price display
 * - User override price input with validation
 * - Reason/notes for override
 * - History of past overrides
 * - Trend analysis
 */

import React, { useState, useEffect } from 'react';
import { X, AlertCircle, TrendingDown, TrendingUp, Minus, Plus, ChevronDown } from 'lucide-react';
import { useRecordOverride, useOverrideHistory, useOverrideTrends } from '@/modules/procurement/hooks/usePricing';
import { OverrideRecord, OverrideTrend } from '@/modules/procurement/services/pricingApi';

interface PriceOverrideDialogProps {
  isOpen: boolean;
  onClose: () => void;
  materialId: string;
  supplierId: string;
  suggestedPrice: number;
  onSuccess?: (record: OverrideRecord) => void;
}

const OVERRIDE_REASONS = [
  'Quality Issue',
  'Rush Order',
  'Bulk Discount',
  'Vendor Preference',
  'Budget Constraint',
  'Market Rate Adjustment',
  'Negotiation',
  'Other',
];

export const PriceOverrideDialog: React.FC<PriceOverrideDialogProps> = ({
  isOpen,
  onClose,
  materialId,
  supplierId,
  suggestedPrice,
  onSuccess,
}) => {
  const [overridePrice, setOverridePrice] = useState<number>(suggestedPrice);
  const [reason, setReason] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [showHistory, setShowHistory] = useState(false);
  const [showTrends, setShowTrends] = useState(false);

  const { recording, error: recordError, recordOverride } = useRecordOverride();
  const { history, loading: historyLoading } = useOverrideHistory(
    materialId,
    supplierId,
    showHistory
  );
  const { trend, loading: trendLoading } = useOverrideTrends(
    materialId,
    supplierId,
    showTrends
  );

  // Update override price when suggested price changes
  useEffect(() => {
    setOverridePrice(suggestedPrice);
  }, [suggestedPrice, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (overridePrice <= 0) {
      alert('Override price must be greater than 0');
      return;
    }

    const result = await recordOverride(
      materialId,
      supplierId,
      suggestedPrice,
      overridePrice,
      reason || undefined,
      'MANUAL'
    );

    if (result) {
      // Reset form
      setOverridePrice(suggestedPrice);
      setReason('');
      setNotes('');

      if (onSuccess) {
        onSuccess(result);
      }

      // Close after a short delay to show success feedback
      setTimeout(() => {
        onClose();
      }, 500);
    }
  };

  const variance = overridePrice - suggestedPrice;
  const variancePercent = ((variance / suggestedPrice) * 100).toFixed(2);
  const isDiscount = variance < 0;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 sticky top-0 bg-white">
          <h2 className="text-xl font-semibold text-gray-900">Override Price</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded transition"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Suggested Price Display */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm font-medium text-blue-900 mb-2">Suggested Price</p>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-blue-900">
                ${suggestedPrice.toFixed(2)}
              </span>
              <span className="text-sm text-blue-700">per unit</span>
            </div>
          </div>

          {/* Override Price Input */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Override Price *
            </label>
            <div className="flex gap-2 items-end">
              <div className="flex-1">
                <div className="relative">
                  <span className="absolute left-3 top-3 text-gray-600">$</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={overridePrice}
                    onChange={(e) => setOverridePrice(parseFloat(e.target.value) || 0)}
                    className="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter override price"
                  />
                </div>
              </div>
              <div className="flex gap-1">
                <button
                  type="button"
                  onClick={() => setOverridePrice(Math.max(0.01, overridePrice - 1))}
                  className="p-2 border border-gray-300 rounded hover:bg-gray-50 transition"
                  title="Decrease by $1"
                >
                  <Minus className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setOverridePrice(overridePrice + 1)}
                  className="p-2 border border-gray-300 rounded hover:bg-gray-50 transition"
                  title="Increase by $1"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Variance Display */}
          {variance !== 0 && (
            <div className={`p-3 rounded-lg border ${isDiscount ? 'bg-green-50 border-green-200' : 'bg-orange-50 border-orange-200'}`}>
              <div className="flex items-center gap-2">
                {isDiscount ? (
                  <TrendingDown className="w-4 h-4 text-green-600" />
                ) : (
                  <TrendingUp className="w-4 h-4 text-orange-600" />
                )}
                <span className={`font-medium ${isDiscount ? 'text-green-900' : 'text-orange-900'}`}>
                  {isDiscount ? 'Discount' : 'Premium'}: ${Math.abs(variance).toFixed(2)} ({variancePercent}%)
                </span>
              </div>
            </div>
          )}

          {/* Reason Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Reason for Override
            </label>
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a reason...</option>
              {OVERRIDE_REASONS.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>

          {/* Additional Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any additional context for this override..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
            />
          </div>

          {/* History Section */}
          <div className="border-t border-gray-200 pt-4">
            <button
              type="button"
              onClick={() => setShowHistory(!showHistory)}
              className="w-full flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
            >
              <span className="font-medium text-gray-900">Override History</span>
              <ChevronDown
                className={`w-4 h-4 transition-transform ${showHistory ? 'rotate-180' : ''}`}
              />
            </button>

            {showHistory && (
              <div className="mt-3 space-y-2">
                {historyLoading ? (
                  <div className="text-sm text-gray-500">Loading history...</div>
                ) : history.length > 0 ? (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {history.slice(0, 5).map((record) => (
                      <div key={record.id} className="p-2 bg-gray-50 rounded border border-gray-200">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-gray-900">
                              ${record.override_price.toFixed(2)}
                            </p>
                            {record.override_reason && (
                              <p className="text-xs text-gray-600">{record.override_reason}</p>
                            )}
                          </div>
                          <span className="text-xs text-gray-500">
                            {new Date(record.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No previous overrides</p>
                )}
              </div>
            )}
          </div>

          {/* Trends Section */}
          <div className="border-t border-gray-200 pt-4">
            <button
              type="button"
              onClick={() => setShowTrends(!showTrends)}
              className="w-full flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
            >
              <span className="font-medium text-gray-900">Price Trends</span>
              <ChevronDown
                className={`w-4 h-4 transition-transform ${showTrends ? 'rotate-180' : ''}`}
              />
            </button>

            {showTrends && (
              <div className="mt-3 p-3 bg-gray-50 rounded border border-gray-200">
                {trendLoading ? (
                  <div className="text-sm text-gray-500">Loading trends...</div>
                ) : trend ? (
                  <TrendAnalysisView trend={trend} />
                ) : (
                  <p className="text-sm text-gray-500">No trend data available</p>
                )}
              </div>
            )}
          </div>

          {/* Error Message */}
          {recordError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-red-800">{recordError.message}</p>
            </div>
          )}

          {/* Buttons */}
          <div className="flex gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={recording || !reason}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {recording ? 'Recording...' : 'Record Override'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

/**
 * Trend Analysis View Component
 */
interface TrendAnalysisViewProps {
  trend: OverrideTrend;
}

const TrendAnalysisView: React.FC<TrendAnalysisViewProps> = ({ trend }) => {
  const getTrendIcon = (direction: string) => {
    switch (direction?.toUpperCase()) {
      case 'UPWARD':
        return <TrendingUp className="w-4 h-4 text-orange-600" />;
      case 'DOWNWARD':
        return <TrendingDown className="w-4 h-4 text-green-600" />;
      default:
        return <Minus className="w-4 h-4 text-gray-600" />;
    }
  };

  const getTrendColor = (direction: string): string => {
    switch (direction?.toUpperCase()) {
      case 'UPWARD':
        return 'text-orange-900';
      case 'DOWNWARD':
        return 'text-green-900';
      default:
        return 'text-gray-900';
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {getTrendIcon(trend.trend_direction)}
        <span className={`font-medium ${getTrendColor(trend.trend_direction)}`}>
          {trend.trend_direction === 'UPWARD' && 'Prices Increasing'}
          {trend.trend_direction === 'DOWNWARD' && 'Prices Decreasing'}
          {trend.trend_direction === 'STABLE' && 'Prices Stable'}
          {trend.trend_direction === 'INSUFFICIENT_DATA' && 'Insufficient Data'}
        </span>
      </div>

      {trend.total_records_analyzed > 0 && (
        <>
          <p className="text-sm text-gray-700">
            Based on {trend.total_records_analyzed} override(s)
            {trend.time_period_days && ` over ${trend.time_period_days} days`}
          </p>

          {trend.price_change_percent && (
            <p className="text-sm text-gray-700">
              Price change: {trend.price_change_percent > 0 ? '+' : ''}{trend.price_change_percent.toFixed(2)}%
            </p>
          )}

          <p className="text-xs text-gray-600">
            Confidence: <span className="font-medium">{trend.trend_confidence}</span>
          </p>
        </>
      )}
    </div>
  );
};
