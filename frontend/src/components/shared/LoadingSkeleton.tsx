/**
 * Skeleton loading components for consistent loading states across the app.
 * Requirements: 52.1–52.5
 */
import { Skeleton } from "@/components/ui/skeleton"

// ─── Table skeleton ────────────────────────────────────────────────────────────

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-10 w-24" />
      </div>
      <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm">
        {/* Header row */}
        <div className="flex gap-4 mb-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-4 flex-1" />
          ))}
        </div>
        {/* Data rows */}
        <div className="space-y-4">
          {Array.from({ length: rows }).map((_, i) => (
            <div key={i} className="flex gap-4 items-center">
              {Array.from({ length: 5 }).map((_, j) => (
                <Skeleton key={j} className="h-10 flex-1" />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/** Alias matching skeleton naming convention (Requirements: 52.2) */
export const SkeletonTable = TableSkeleton;

// ─── Form skeleton ─────────────────────────────────────────────────────────────

export function FormSkeleton({ fields = 4 }: { fields?: number }) {
  return (
    <div className="space-y-6 max-w-2xl">
      {Array.from({ length: fields }).map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-10 w-full" />
        </div>
      ))}
      <div className="flex gap-4 pt-4">
        <Skeleton className="h-10 w-24" />
        <Skeleton className="h-10 w-24" />
      </div>
    </div>
  )
}

/** Alias matching skeleton naming convention (Requirements: 52.4) */
export const SkeletonForm = FormSkeleton;

// ─── Card skeleton ─────────────────────────────────────────────────────────────

export function CardSkeleton() {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-card text-card-foreground shadow-sm space-y-4 p-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-4 w-4 rounded-full" />
      </div>
      <Skeleton className="h-8 w-1/2" />
      <Skeleton className="h-4 w-3/4" />
    </div>
  )
}

/** Alias matching skeleton naming convention (Requirements: 52.3) */
export const SkeletonCard = CardSkeleton;
