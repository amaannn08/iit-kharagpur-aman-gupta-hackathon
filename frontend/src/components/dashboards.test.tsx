import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { IndexPanel } from './IndexPanel';
import { MetricsPanel } from './MetricsPanel';
import { waterfallData } from './StressCharts';
import type { StressRunResult } from '../api/client';

const ok = (body: unknown) => Promise.resolve({ ok: true, json: () => Promise.resolve(body) } as Response);

describe('Module B waterfall', () => {
  it('bars bridge funded baseline to stressed value and sum to total P&L', () => {
    const r = {
      funded_baseline_value_usd: 610e6,
      baseline_total_book_value_usd: 610e6,
      total_pnl_usd: -23.3e6,
      derivative_mtm_change_usd: 0.3e6,
      asset_class_breakdown: [
        { asset_class: 'bond', total_pnl_usd: -18.13e6 },
        { asset_class: 'equity', total_pnl_usd: -5.47e6 },
        { asset_class: 'loan', total_pnl_usd: 0 },
        { asset_class: 'swap', total_pnl_usd: 0.3e6 },
        { asset_class: 'cash', total_pnl_usd: 0 },
      ],
    } as unknown as StressRunResult;
    const rows = waterfallData(r);
    expect(rows[0].name).toBe('Funded baseline');
    expect(rows[rows.length - 1].delta).toBeCloseTo(610e6 - 23.3e6, 0);
    const signed = rows.slice(1, -1).reduce((acc, x) => acc + (x.kind === 'loss' ? -x.delta : x.delta), 0);
    expect(signed).toBeCloseTo(r.total_pnl_usd, 0);
    expect(rows.filter((x) => x.name === 'swap')).toHaveLength(0); // swaps shown once, as MTM
  });
});

describe('Module A index panel', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/index/current'))
          return ok({
            label: 'Mock index (20 S&P 100 names), not an S&P product',
            weights: { AAPL: 0.6, BA: 0.4 },
            base_weights: { AAPL: 0.5, BA: 0.5 },
            sentiment_ema: { AAPL: 0.3, BA: -0.2 },
            sectors: { AAPL: 'Information Technology', BA: 'Industrials' },
            reasons: { AAPL: 'increase: positive sentiment +0.30', BA: 'decrease: negative sentiment -0.20' },
            constraints: { name_cap: 0.2, sector_cap: 0.4, k: 1.5, halflife_days: 5 },
            rebalances: 2,
          });
        if (url.includes('/index/history'))
          return ok([{ timestamp: 'initial', weights: { AAPL: 0.5, BA: 0.5 }, sentiment_ema: {}, turnover: 0, reasons: {} }]);
        return ok({});
      }),
    );
  });

  it('shows the mock-index label and the reason for each move', async () => {
    render(<IndexPanel />);
    await waitFor(() => expect(screen.getByText(/not an S&P product/)).toBeInTheDocument());
    expect(screen.getByText('increase: positive sentiment +0.30')).toBeInTheDocument();
    expect(screen.getByText('Index weights over time')).toBeInTheDocument();
  });
});

describe('Metrics panel', () => {
  it('states clearly when real-data metrics have not been generated', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: false, status: 404 } as Response)));
    render(<MetricsPanel />);
    await waitFor(() => expect(screen.getByText(/Real-data metrics unavailable/)).toBeInTheDocument());
  });
});
