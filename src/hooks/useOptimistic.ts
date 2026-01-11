import { useState, useCallback, useRef } from 'react';

export interface OptimisticUpdate<T> {
  id: string;
  data: T;
  timestamp: number;
}

export interface UseOptimisticOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: Error, rollbackData: T) => void;
  onSettled?: () => void;
}

export function useOptimistic<T>(
  initialData: T,
  options?: UseOptimisticOptions<T>
) {
  const [data, setData] = useState<T>(initialData);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const previousDataRef = useRef<T>(initialData);
  const pendingUpdatesRef = useRef<Map<string, OptimisticUpdate<T>>>(new Map());

  const update = useCallback(
    async <R = void>(
      optimisticData: Partial<T>,
      asyncFn: () => Promise<R>
    ): Promise<R | void> => {
      const updateId = `update-${Date.now()}-${Math.random()}`;
      const timestamp = Date.now();

      // Store the current data for potential rollback
      previousDataRef.current = data;

      // Apply optimistic update
      const newData = { ...data, ...optimisticData };
      setData(newData);
      setIsLoading(true);
      setError(null);

      // Track this update
      pendingUpdatesRef.current.set(updateId, {
        id: updateId,
        data: previousDataRef.current,
        timestamp,
      });

      try {
        // Execute the async operation
        const result = await asyncFn();

        // Clear this update from pending
        pendingUpdatesRef.current.delete(updateId);

        // Call success callback
        options?.onSuccess?.(newData);
        options?.onSettled?.();

        return result;
      } catch (err) {
        // Rollback to previous data
        setData(previousDataRef.current);
        setError(err as Error);

        // Clear this update from pending
        pendingUpdatesRef.current.delete(updateId);

        // Call error callback
        options?.onError?.(err as Error, previousDataRef.current);
        options?.onSettled?.();

        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [data, options]
  );

  const rollback = useCallback(() => {
    setData(previousDataRef.current);
    setError(null);
    pendingUpdatesRef.current.clear();
  }, []);

  const reset = useCallback(() => {
    setData(initialData);
    setError(null);
    setIsLoading(false);
    previousDataRef.current = initialData;
    pendingUpdatesRef.current.clear();
  }, [initialData]);

  return {
    data,
    isLoading,
    error,
    update,
    rollback,
    reset,
    hasPendingUpdates: pendingUpdatesRef.current.size > 0,
  };
}

// Hook for optimistic list operations
export function useOptimisticList<T extends { id: string | number }>(
  initialItems: T[],
  options?: UseOptimisticOptions<T[]>
) {
  const [items, setItems] = useState<T[]>(initialItems);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const previousItemsRef = useRef<T[]>(initialItems);

  const addItem = useCallback(
    async (item: T, asyncFn: () => Promise<void>) => {
      previousItemsRef.current = items;
      const newItems = [...items, item];
      setItems(newItems);
      setIsLoading(true);
      setError(null);

      try {
        await asyncFn();
        options?.onSuccess?.(newItems);
        options?.onSettled?.();
      } catch (err) {
        setItems(previousItemsRef.current);
        setError(err as Error);
        options?.onError?.(err as Error, previousItemsRef.current);
        options?.onSettled?.();
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [items, options]
  );

  const updateItem = useCallback(
    async (id: string | number, updates: Partial<T>, asyncFn: () => Promise<void>) => {
      previousItemsRef.current = items;
      const newItems = items.map((item) =>
        item.id === id ? { ...item, ...updates } : item
      );
      setItems(newItems);
      setIsLoading(true);
      setError(null);

      try {
        await asyncFn();
        options?.onSuccess?.(newItems);
        options?.onSettled?.();
      } catch (err) {
        setItems(previousItemsRef.current);
        setError(err as Error);
        options?.onError?.(err as Error, previousItemsRef.current);
        options?.onSettled?.();
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [items, options]
  );

  const removeItem = useCallback(
    async (id: string | number, asyncFn: () => Promise<void>) => {
      previousItemsRef.current = items;
      const newItems = items.filter((item) => item.id !== id);
      setItems(newItems);
      setIsLoading(true);
      setError(null);

      try {
        await asyncFn();
        options?.onSuccess?.(newItems);
        options?.onSettled?.();
      } catch (err) {
        setItems(previousItemsRef.current);
        setError(err as Error);
        options?.onError?.(err as Error, previousItemsRef.current);
        options?.onSettled?.();
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [items, options]
  );

  const rollback = useCallback(() => {
    setItems(previousItemsRef.current);
    setError(null);
  }, []);

  return {
    items,
    isLoading,
    error,
    addItem,
    updateItem,
    removeItem,
    rollback,
  };
}
