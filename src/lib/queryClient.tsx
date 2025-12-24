import { createContext, ReactNode, useContext, useEffect, useMemo, useRef, useState } from 'react';

type QueryKey = string | readonly unknown[];

interface CachedQuery<TData = unknown> {
  key: string;
  data?: TData;
  error?: unknown;
  status: 'idle' | 'loading' | 'success' | 'error';
  updatedAt?: number;
  promise?: Promise<TData>;
  queryFn?: () => Promise<TData>;
  subscribers: Set<() => void>;
}

const getCacheKey = (queryKey: QueryKey) =>
  typeof queryKey === 'string' ? queryKey : JSON.stringify(queryKey);

class QueryClient {
  private cache = new Map<string, CachedQuery>();

  private notify(key: string) {
    const cached = this.cache.get(key);
    cached?.subscribers.forEach((subscriber) => subscriber());
  }

  getQueryData<TData>(queryKey: QueryKey) {
    const cached = this.cache.get(getCacheKey(queryKey));
    return cached?.data as TData | undefined;
  }

  getQueryError(queryKey: QueryKey) {
    const cached = this.cache.get(getCacheKey(queryKey));
    return cached?.error;
  }

  getQueryStatus(queryKey: QueryKey) {
    const cached = this.cache.get(getCacheKey(queryKey));
    return cached?.status ?? 'idle';
  }

  getUpdatedAt(queryKey: QueryKey) {
    const cached = this.cache.get(getCacheKey(queryKey));
    return cached?.updatedAt;
  }

  setQueryData<TData>(
    queryKey: QueryKey,
    updater: TData | ((oldData: TData | undefined) => TData)
  ) {
    const key = getCacheKey(queryKey);
    const cached =
      this.cache.get(key) ??
      ({
        key,
        status: 'idle',
        subscribers: new Set()
      } as CachedQuery);

    const nextData =
      typeof updater === 'function'
        ? (updater as (oldData: TData | undefined) => TData)(cached.data as TData | undefined)
        : updater;

    this.cache.set(key, {
      ...cached,
      data: nextData,
      status: 'success',
      updatedAt: Date.now()
    });
    this.notify(key);
  }

  async fetchQuery<TData>(queryKey: QueryKey, queryFn: () => Promise<TData>, staleTime = 0) {
    const key = getCacheKey(queryKey);
    const cached =
      this.cache.get(key) ??
      ({
        key,
        status: 'idle',
        subscribers: new Set()
      } as CachedQuery);

    const isFresh = cached.updatedAt && Date.now() - cached.updatedAt < staleTime;
    if (cached.promise) {
      return cached.promise;
    }

    if (isFresh && cached.data !== undefined) {
      return Promise.resolve(cached.data as TData);
    }

    cached.status = 'loading';
    cached.queryFn = queryFn;
    const promise = queryFn()
      .then((data) => {
        this.cache.set(key, {
          ...cached,
          data,
          status: 'success',
          updatedAt: Date.now(),
          promise: undefined
        });
        this.notify(key);
        return data;
      })
      .catch((error) => {
        this.cache.set(key, {
          ...cached,
          error,
          status: 'error',
          updatedAt: Date.now(),
          promise: undefined
        });
        this.notify(key);
        throw error;
      });

    this.cache.set(key, { ...cached, promise });
    this.notify(key);
    return promise;
  }

  async invalidateQueries({ queryKey }: { queryKey?: QueryKey } = {}) {
    const prefix = queryKey ? getCacheKey(queryKey) : null;
    const matching = Array.from(this.cache.entries()).filter(([key]) =>
      prefix ? key.startsWith(prefix) : true
    );

    await Promise.all(
      matching.map(async ([key, cached]) => {
        if (cached.queryFn) {
          return this.fetchQuery(key, cached.queryFn);
        }
        this.cache.set(key, {
          ...cached,
          status: 'idle',
          promise: undefined
        });
        this.notify(key);
        return undefined;
      })
    );
  }

  subscribe(queryKey: QueryKey, callback: () => void) {
    const key = getCacheKey(queryKey);
    const cached =
      this.cache.get(key) ??
      ({
        key,
        status: 'idle',
        subscribers: new Set()
      } as CachedQuery);

    cached.subscribers.add(callback);
    this.cache.set(key, cached);

    return () => {
      const current = this.cache.get(key);
      if (!current) return;
      current.subscribers.delete(callback);
    };
  }
}

const QueryClientContext = createContext<QueryClient | null>(null);

export function QueryClientProvider({ client, children }: { client: QueryClient; children: ReactNode }) {
  const value = useMemo(() => client, [client]);
  return <QueryClientContext.Provider value={value}>{children}</QueryClientContext.Provider>;
}

export const useQueryClient = () => {
  const context = useContext(QueryClientContext);
  if (!context) {
    throw new Error('useQueryClient must be used within a QueryClientProvider');
  }
  return context;
};

interface UseQueryOptions<TData> {
  queryKey: QueryKey;
  queryFn: () => Promise<TData>;
  enabled?: boolean;
  staleTime?: number;
}

export function useQuery<TData>({
  queryKey,
  queryFn,
  enabled = true,
  staleTime = 0
}: UseQueryOptions<TData>) {
  const client = useQueryClient();
  const key = useMemo(() => getCacheKey(queryKey), [queryKey]);
  const [data, setData] = useState<TData | undefined>(() => client.getQueryData(queryKey));
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>(() =>
    client.getQueryStatus(queryKey)
  );
  const [error, setError] = useState<unknown>(() => client.getQueryError(queryKey));
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    const run = async () => {
      try {
        setStatus((prev) => (prev === 'success' && data !== undefined ? prev : 'loading'));
        const result = await client.fetchQuery(queryKey, queryFn, staleTime);
        if (!cancelled && mountedRef.current) {
          setData(result);
          setStatus('success');
        }
      } catch (err) {
        if (!cancelled && mountedRef.current) {
          setError(err);
          setStatus('error');
        }
      }
    };

    run();
    const unsubscribe = client.subscribe(queryKey, () => {
      if (!mountedRef.current) return;
      const cached = client.getQueryData<TData>(queryKey);
      setData(cached);
      setStatus(client.getQueryStatus(queryKey));
      setError(client.getQueryError(queryKey));
    });

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [client, key, enabled, queryFn, staleTime]);

  return {
    data,
    status,
    error,
    isLoading: status === 'loading' && !data,
    isFetching: status === 'loading',
    refetch: () => client.fetchQuery(queryKey, queryFn, staleTime)
  };
}

interface UseMutationOptions<TData, TVariables> {
  mutationFn: (variables: TVariables) => Promise<TData>;
  onSuccess?: (data: TData, variables: TVariables, client: QueryClient) => void;
  onError?: (error: unknown, variables: TVariables, client: QueryClient) => void;
}

export function useMutation<TData, TVariables = void>({
  mutationFn,
  onSuccess,
  onError
}: UseMutationOptions<TData, TVariables>) {
  const client = useQueryClient();
  const [status, setStatus] = useState<'idle' | 'pending' | 'success' | 'error'>('idle');
  const [error, setError] = useState<unknown>(null);

  const mutateAsync = async (variables: TVariables) => {
    setStatus('pending');
    setError(null);
    try {
      const data = await mutationFn(variables);
      setStatus('success');
      onSuccess?.(data, variables, client);
      return data;
    } catch (err) {
      setError(err);
      setStatus('error');
      onError?.(err, variables, client);
      throw err;
    }
  };

  return {
    mutateAsync,
    status,
    error,
    isPending: status === 'pending'
  };
}

export { QueryClient, type QueryKey };
