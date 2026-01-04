import { useEffect, useRef, useState } from 'react';

export interface UseAutoRefreshOptions {
  interval?: number; // in milliseconds
  enabled?: boolean;
  onRefresh: () => void | Promise<void>;
  dependencies?: any[];
}

/**
 * Custom hook for auto-refreshing data at configurable intervals
 *
 * @param options Configuration options
 * @returns Object with pause/resume controls and refresh status
 */
export function useAutoRefresh({
  interval = 300000, // Default: 5 minutes
  enabled = true,
  onRefresh,
  dependencies = []
}: UseAutoRefreshOptions) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isPaused, setIsPaused] = useState(!enabled);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = async () => {
    if (isRefreshing || isPaused) return;

    try {
      setIsRefreshing(true);
      await Promise.resolve(onRefresh());
      setLastRefresh(new Date());
    } catch (error) {
      console.error('Auto-refresh error:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    // Clear existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // Set up new interval if not paused
    if (!isPaused && interval > 0) {
      intervalRef.current = setInterval(() => {
        refresh();
      }, interval);
    }

    // Cleanup on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [interval, isPaused, ...dependencies]);

  const pause = () => setIsPaused(true);
  const resume = () => setIsPaused(false);
  const toggle = () => setIsPaused(prev => !prev);

  return {
    isRefreshing,
    isPaused,
    lastRefresh,
    pause,
    resume,
    toggle,
    refresh // Manual refresh
  };
}
