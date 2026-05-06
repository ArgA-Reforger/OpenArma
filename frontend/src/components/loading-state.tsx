import { Skeleton } from '@/components/ui/skeleton'

interface LoadingStateProps {
  rows?: number
  className?: string
}

export function LoadingState({ rows = 3, className }: LoadingStateProps) {
  return (
    <div className={className}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="space-y-2 mb-4">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      ))}
    </div>
  )
}

export function LoadingSpinner({ className }: { className?: string }) {
  return (
    <div className={`flex items-center justify-center py-12 ${className || ''}`}>
      <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
    </div>
  )
}

export function CardLoadingState({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-lg border p-4 space-y-3">
          <div className="flex items-center gap-3">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
          <Skeleton className="h-4 w-2/3" />
        </div>
      ))}
    </div>
  )
}
