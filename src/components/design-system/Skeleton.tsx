interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`skeleton animate-pulse rounded-md bg-surface border border-border ${className}`}
      aria-busy="true"
      aria-live="polite"
    />
  );
}
