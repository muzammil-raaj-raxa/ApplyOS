/** Skeletons copy the geometry of what is loading, so nothing jumps when data arrives. */
export function JobRowSkeleton() {
  return (
    <div className="flex items-center gap-5 border-b border-[var(--hairline)] py-6" aria-hidden="true">
      <div className="shimmer size-14 shrink-0 rounded-full" />
      <div className="min-w-0 flex-1 space-y-3">
        <div className="shimmer h-5 w-2/5 rounded-md" />
        <div className="shimmer h-3.5 w-3/5 rounded-md" />
      </div>
    </div>
  )
}

export function JobListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div role="status" aria-label="Loading jobs">
      {Array.from({ length: rows }, (_, i) => (
        <JobRowSkeleton key={i} />
      ))}
    </div>
  )
}

export function Bar({ className = '' }: { className?: string }) {
  return <div className={`shimmer rounded-md ${className}`} aria-hidden="true" />
}
