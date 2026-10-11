import { useEffect, useState } from 'react';
import { fetchMetrics } from '../api/client';

/** docs/metrics.json as served by /api/datasets/metrics (null until loaded or if unavailable). */
export function useMetrics(): Record<string, any> | null {
  const [metrics, setMetrics] = useState<Record<string, any> | null>(null);
  useEffect(() => {
    fetchMetrics().then(setMetrics).catch(() => setMetrics(null));
  }, []);
  return metrics;
}

export const fmt = (v: unknown, digits = 3): string =>
  typeof v === 'number' && Number.isFinite(v) ? v.toFixed(digits) : '—';

export const pct = (v: unknown, digits = 2): string =>
  typeof v === 'number' && Number.isFinite(v) ? `${(v * 100).toFixed(digits)}%` : '—';

export const musd = (v: unknown): string =>
  typeof v === 'number' && Number.isFinite(v) ? `$${(v / 1e6).toFixed(0)}M` : '—';
