import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { IndexPanel } from './IndexPanel';
import { MetricsPanel } from './MetricsPanel';
import { StressCharts, waterfallData } from './StressCharts';
import { WhyThisLossPanel } from './WhyThisLossPanel';
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

describe('WhyThisLossPanel', () => {
  it('renders loss attribution panel and components sum to total within $1', () => {
    const mockResult = {
      stress_id: 'stress-test-1',
      run_id: 'run-1',
      executed_at: '2026-03-01T12:00:00Z',
      trigger_type: 'EVENT_TRIGGERED',
      event_class: 'CREDIT',
      impact_score: 9,
      target_entity: 'JPM',
      target_scope: 'entity',
      total_pnl_usd: -12500000.0,
      total_pnl_pct: -0.025,
      credit_ecl_change_usd: 7500000.0,
      market_mtm_change_usd: 5000000.0,
      reconciliation_passed: true,
      shock_parameters: {
        bond_spread_shift_bps: 120,
        loan_pd_increment: 0.015,
        benchmark_yield_shift_bps: 0,
        rating_tiered: true,
      },
      attribution: {
        by_component: {
          rates_usd: 0.0,
          spread_usd: -5000000.0,
          pd_usd: -6500000.0,
          lgd_usd: -1000000.0,
          equity_usd: 0.0,
          operational_usd: 0.0,
          clamp_usd: 0.0,
        },
        by_driver: {
          direct: -12500000.0,
        },
        top_positions: [
          {
            position_id: 'LOAN-JPM-1',
            entity_id: 'JPM',
            counterparty_name: 'JPMorgan Chase',
            asset_class: 'loan',
            pnl_usd: -6500000.0,
            dominant_component: 'pd',
            driver: 'direct',
          },
          {
            position_id: 'BOND-JPM-1',
            entity_id: 'JPM',
            counterparty_name: 'JPMorgan Chase',
            asset_class: 'bond',
            pnl_usd: -5000000.0,
            dominant_component: 'spread',
            driver: 'direct',
          },
        ],
      },
    } as unknown as StressRunResult;

    render(
      <WhyThisLossPanel
        result={mockResult}
        triggerHeadline="JPMorgan faces credit downgrade"
        evidenceSpan="downgrade across senior notes"
      />
    );

    expect(screen.getByTestId('why-this-loss-panel')).toBeInTheDocument();
    expect(screen.getByText(/Why this loss/)).toBeInTheDocument();
    expect(screen.getByText(/"JPMorgan faces credit downgrade"/)).toBeInTheDocument();
    expect(screen.getByText(/downgrade across senior notes/)).toBeInTheDocument();
    expect(screen.getByText('LOAN-JPM-1')).toBeInTheDocument();

    const comp = mockResult.attribution!.by_component;
    const sum = Object.values(comp).reduce((a, b) => a + b, 0);
    expect(Math.abs(sum - mockResult.total_pnl_usd)).toBeLessThan(1.0);
  });

  it('waterfallData decomposes by by_component when attribution is available', () => {
    const mockResult = {
      funded_baseline_value_usd: 500e6,
      baseline_total_book_value_usd: 500e6,
      total_pnl_usd: -15e6,
      attribution: {
        by_component: {
          rates_usd: -3e6,
          spread_usd: -7e6,
          pd_usd: -4e6,
          lgd_usd: -1e6,
          equity_usd: 0,
          operational_usd: 0,
          clamp_usd: 0,
        },
      },
    } as unknown as StressRunResult;

    const rows = waterfallData(mockResult);
    expect(rows[0].name).toBe('Funded baseline');
    expect(rows.some((r) => r.name === 'Rates')).toBe(true);
    expect(rows.some((r) => r.name === 'Spread')).toBe(true);
    expect(rows.find((r) => r.name === 'Spread')?.pnl).toBe(-7e6);
    expect(rows.some((r) => r.name === 'Loan PD')).toBe(true);
    expect(rows[rows.length - 1].name).toBe('After stress');
    expect(rows[rows.length - 1].delta).toBeCloseTo(485e6, 0);
  });

  it('renders waterfall chart and decomposes loss components with signed pnl', () => {
    const mockResult = {
      funded_baseline_value_usd: 500e6,
      baseline_total_book_value_usd: 500e6,
      total_pnl_usd: -15e6,
      total_pnl_pct: -0.03,
      reconciliation_passed: true,
      attribution: {
        by_component: {
          rates_usd: -3e6,
          spread_usd: -7e6,
          pd_usd: -4e6,
          lgd_usd: -1e6,
          equity_usd: 0,
          operational_usd: 0,
          clamp_usd: 0,
        },
      },
    } as unknown as StressRunResult;

    render(<StressCharts result={mockResult} onResult={() => {}} />);
    expect(screen.getByText(/Loss waterfall: total -\$15\.00M/)).toBeInTheDocument();
    expect(screen.getByText('Reconciled')).toBeInTheDocument();
  });
});

describe('PS benchmark card in StressCharts', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/stress/scenarios')) return ok({ scenarios: [] });
        if (url.includes('/datasets/metrics'))
          return ok({
            stress: {
              'ps_example_equities_-10pct_rates_+200bp': {
                total_pnl_usd: -23300600.0,
                funded_baseline_usd: 610000000.0,
                funded_stressed_usd: 588240467.2,
                derivative_mtm_change_usd: 300000.0,
                by_sleeve_usd: { equity: -5470600.0, retail_sme: 0.0, wholesale: -18130000.0 },
                top_drivers: [
                  { counterparty_name: 'Global Clearing House', dominant_component: 'rates', pnl_usd: -6900000.0 },
                ],
              },
            },
          });
        return ok({});
      }),
    );
  });

  it('renders the PS benchmark card with metrics from /api/datasets/metrics', async () => {
    render(<StressCharts result={null} onResult={() => {}} />);
    await waitFor(() => expect(screen.getByTestId('ps-benchmark-card')).toBeInTheDocument());
    expect(screen.getByText(/Problem Statement Benchmark/)).toBeInTheDocument();
    expect(screen.getByText('-$23.30M')).toBeInTheDocument();
    expect(screen.getByText('$610.0M')).toBeInTheDocument();
    expect(screen.getByText('Run live')).toBeInTheDocument();
  });
});
