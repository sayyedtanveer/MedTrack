/**
 * Empty state component for consistent zero-data messaging.
 * Requirements: 54.1–54.5
 */
import { LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
  /**
   * 'no-records'  — no data exists yet (neutral/informational tone)
   * 'filtered'    — data exists but current filters returned nothing
   */
  variant?: 'no-records' | 'filtered';
}

export default function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  variant = 'no-records',
}: EmptyStateProps) {
  // Provide contextual sub-text when caller doesn't supply a description
  const defaultDescription =
    variant === 'filtered'
      ? 'Try adjusting your filters or search terms to see results.'
      : undefined;

  const displayDescription = description ?? defaultDescription;

  return (
    <div className="text-center py-12 px-4">
      {Icon && (
        <Icon
          className={
            variant === 'filtered'
              ? 'mx-auto h-12 w-12 text-amber-300 mb-4'
              : 'mx-auto h-12 w-12 text-gray-300 mb-4'
          }
        />
      )}
      <h3 className="text-sm font-semibold text-gray-900 mb-1">{title}</h3>
      {displayDescription && (
        <p className="text-sm text-gray-500 mb-4">{displayDescription}</p>
      )}
      {action && (
        <Button variant="outline" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
