/**
 * ResponsiveDataTable — full table on desktop, card layout on mobile.
 * Requirements: 35.2, 35.3
 */
import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface ColumnDef<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
  headerClassName?: string;
}

interface ResponsiveDataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  getRowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  renderMobileCard?: (row: T) => ReactNode;
  emptyMessage?: string;
  isLoading?: boolean;
  className?: string;
}

export default function ResponsiveDataTable<T>({
  data,
  columns,
  getRowKey,
  onRowClick,
  renderMobileCard,
  emptyMessage = 'No data found',
  isLoading = false,
  className,
}: ResponsiveDataTableProps<T>) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Desktop: Full table */}
      <div className="hidden lg:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              {columns.map(col => (
                <th
                  key={col.key}
                  className={cn('px-4 py-3 text-left font-medium text-gray-700', col.headerClassName)}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map(row => (
              <tr
                key={getRowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cn('border-b hover:bg-gray-50', onRowClick && 'cursor-pointer')}
              >
                {columns.map(col => (
                  <td key={col.key} className={cn('px-4 py-3', col.className)}>
                    {col.cell(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Tablet: Horizontal scroll with sticky first column */}
      <div className="hidden md:block lg:hidden overflow-x-auto">
        <table className="w-full text-sm min-w-[640px]">
          <thead className="bg-gray-50 border-b">
            <tr>
              {columns.map((col, idx) => (
                <th
                  key={col.key}
                  className={cn(
                    'px-4 py-3 text-left font-medium text-gray-700',
                    idx === 0 && 'sticky left-0 bg-gray-50 z-10',
                    col.headerClassName
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map(row => (
              <tr
                key={getRowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cn('border-b hover:bg-gray-50', onRowClick && 'cursor-pointer')}
              >
                {columns.map((col, idx) => (
                  <td
                    key={col.key}
                    className={cn(
                      'px-4 py-3',
                      idx === 0 && 'sticky left-0 bg-white z-10',
                      col.className
                    )}
                  >
                    {col.cell(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile: Card layout */}
      <div className="block md:hidden space-y-3">
        {data.map(row => (
          <div
            key={getRowKey(row)}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            className={cn(onRowClick && 'cursor-pointer')}
          >
            {renderMobileCard ? renderMobileCard(row) : (
              <div className="rounded-lg border bg-white p-4 space-y-2">
                {columns.map(col => (
                  <div key={col.key} className="flex justify-between gap-4">
                    <span className="text-xs text-gray-500 shrink-0">{col.header}</span>
                    <span className="text-sm text-right">{col.cell(row)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
