import { useState, useEffect, useRef } from 'react';

export function useFetch<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const hasFetched = useRef(false);

  useEffect(() => {
    let cancelled = false;
    // Only show loading spinner on first fetch; subsequent re-fetches keep stale data visible
    if (!hasFetched.current) setLoading(true);
    setError(null);
    fetcher()
      .then((d) => { if (!cancelled) { setData(d); hasFetched.current = true; } })
      .catch((e) => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error };
}

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  enabled: boolean,
  deps: unknown[] = [],
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch and poll only when enabled
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    // Initial fetch
    fetcher()
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => { if (!cancelled) setError(e.message); });

    // Polling
    const id = setInterval(() => {
      if (!cancelled) {
        fetcher()
          .then((d) => { if (!cancelled) setData(d); })
          .catch((e) => { if (!cancelled) setError(e.message); });
      }
    }, intervalMs);

    return () => { cancelled = true; clearInterval(id); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, intervalMs, ...deps]);

  return { data, error };
}

export function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
