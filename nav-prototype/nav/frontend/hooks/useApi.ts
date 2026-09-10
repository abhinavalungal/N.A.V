"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface State<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/** Small fetch hook: no cache, no library, refetch on demand. */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<State<T>>({ data: null, error: null, loading: true });
  const alive = useRef(true);
  const fn = useRef(fetcher);
  fn.current = fetcher;

  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true }));
    try {
      const data = await fn.current();
      if (alive.current) setState({ data, error: null, loading: false });
    } catch (error) {
      if (alive.current)
        setState({
          data: null,
          error: error instanceof Error ? error.message : "Request failed",
          loading: false,
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    alive.current = true;
    load();
    return () => {
      alive.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { ...state, reload: load, setData: (d: T) => setState({ data: d, error: null, loading: false }) };
}
