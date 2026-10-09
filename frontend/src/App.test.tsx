import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App } from './App';

describe('S&P Sentinel Risk Terminal', () => {
  beforeEach(() => {
    // Mock global EventSource
    class MockEventSource {
      addEventListener = vi.fn();
      removeEventListener = vi.fn();
      close = vi.fn();
    }
    vi.stubGlobal('EventSource', MockEventSource);

    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/api/health')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                project: 'S&P Sentinel',
                version: '0.1.0',
                mode: 'offline-replay',
                timestamp: '2026-03-01T12:00:00Z',
                datasets_ready: true,
                environment: {
                  offline_only: true,
                  external_apis: false,
                  database_ready: true,
                },
              }),
          } as Response);
        }
        if (url.includes('/api/datasets')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                manifest_version: '1.0',
                author: 'Aman Gupta (IIT Kharagpur)',
                compliance: {
                  synthetic_data_disclosed: true,
                  hackathon_guidelines_section_8_compliant: true,
                },
                datasets: [
                  {
                    file_path: 'data/news_demo.csv',
                    format: 'csv',
                    record_count: 25,
                    is_synthetic: true,
                    license: 'MIT License (Project-Authored Synthetic Data)',
                    sha256: '0f4ec4ae71089cf953abf953ecd888746f56e0cba487d703220ad2d4369b32fb',
                    byte_size: 8906,
                    description: 'Curated synthetic financial news headlines',
                  },
                ],
              }),
          } as Response);
        }
        if (url.includes('/api/portfolio')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                portfolio_name: 'Synthetic Wholesale Banking Book',
                base_currency: 'USD',
                valuation_date: '2026-03-01',
                summary: {
                  total_book_value_usd: 500000000.0,
                  corporate_loans_value_usd: 220000000.0,
                  corporate_bonds_value_usd: 200000000.0,
                  cash_reserves_usd: 80000000.0,
                  interest_rate_swaps_mtm_usd: 0.0,
                  interest_rate_swaps_gross_notional_usd: 150000000.0,
                },
                loans: [],
                bonds: [],
                swaps: [],
                cash: [],
              }),
          } as Response);
        }
        if (url.includes('/api/replay/status')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                run_id: 'test_run_1',
                state: 'idle',
                speed: 1,
                simulated_at: '2026-03-01T10:00:00Z',
                total_records: 25,
                processed_count: 5,
                pending_count: 20,
                duplicate_count: 1,
                error_count: 0,
                is_paused: false,
                is_completed: false,
              }),
          } as Response);
        }
        if (url.includes('/api/signals')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve([
                {
                  schema_version: '1.0',
                  signal_id: 'sig_test_1',
                  run_id: 'test_run_1',
                  record_id: 'rec_1',
                  source_id: 'news_demo',
                  source_type: 'news',
                  is_synthetic: true,
                  simulated_at: '2026-03-01T10:15:00Z',
                  processed_at: '2026-03-01T10:15:01Z',
                  entity: {
                    name: 'Apex Industrial Holdings',
                    ticker: '$APEX',
                    scope: 'entity',
                    resolved: true,
                  },
                  sentiment: {
                    score: -0.92,
                    label: 'negative',
                    probabilities: {
                      positive: 0.02,
                      neutral: 0.06,
                      negative: 0.92,
                    },
                  },
                  event: {
                    label: 'credit',
                    confidence: 0.88,
                    abstained: false,
                  },
                  impact: {
                    score: 8,
                    rubric_version: '1.0',
                    components: {
                      event_base: 5,
                      scope: 1,
                      explicit_severity: 2,
                    },
                  },
                  evidence: [
                    {
                      start: 0,
                      end: 50,
                      text: 'Apex Industrial Holdings missed coupon payment',
                    },
                  ],
                  duplicate_group_id: undefined,
                  eligible_for_action: true,
                  action_block_reasons: [],
                },
              ]),
          } as Response);
        }
        if (url.includes('/api/stress/runs')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve([
                {
                  stress_id: 'str_1',
                  run_id: 'test_run_1',
                  executed_at: '2026-03-01T10:15:02Z',
                  trigger_type: 'signal',
                  event_class: 'credit',
                  impact_score: 8,
                  target_entity: 'Apex Industrial Holdings',
                  target_scope: 'entity',
                  shock_parameters: {},
                  model_version: '1.0',
                  baseline_total_book_value_usd: 500000000.0,
                  stressed_total_book_value_usd: 488000000.0,
                  total_pnl_usd: -12000000.0,
                  total_pnl_pct: -2.4,
                  credit_ecl_change_usd: 8000000.0,
                  market_mtm_change_usd: -4000000.0,
                  asset_class_breakdown: [
                    {
                      asset_class: 'loan',
                      baseline_value_usd: 220000000.0,
                      stressed_value_usd: 212000000.0,
                      total_pnl_usd: -8000000.0,
                      pct_change: -3.64,
                      credit_ecl_delta_usd: 8000000.0,
                      mark_to_market_pnl_usd: 0.0,
                      derivative_gross_notional_usd: 0.0,
                    },
                  ],
                  sector_breakdown: [],
                  position_deltas: [
                    {
                      position_id: 'LN-001',
                      asset_class: 'loan',
                      entity_id: 'ENT-APEX',
                      counterparty_name: 'Apex Industrial Holdings',
                      sector: 'Industrials',
                      baseline_value_usd: 60000000.0,
                      stressed_value_usd: 54000000.0,
                      pnl_usd: -6000000.0,
                      pct_change: -10.0,
                      ecl_baseline_usd: 3000000.0,
                      ecl_stressed_usd: 9000000.0,
                      incremental_ecl_usd: 6000000.0,
                      market_risk_pnl_usd: 0.0,
                      applied_shock_summary: 'PD shock +15.0%',
                    },
                  ],
                  reconciliation_passed: true,
                },
              ]),
          } as Response);
        }
        return Promise.reject(new Error(`Unhandled URL: ${url}`));
      })
    );
  });

  it('renders the header and mandatory historical replay honesty badge', async () => {
    render(<App />);

    // Assert mandatory honesty badge is present
    expect(
      screen.getByText(/HISTORICAL REPLAY \/ SYNTHETIC SCENARIO/i)
    ).toBeInTheDocument();

    // Assert candidate and app identity
    expect(screen.getByText('S&P Sentinel')).toBeInTheDocument();
    expect(screen.getByText(/Candidate: Aman Gupta \(IIT Kharagpur\)/i)).toBeInTheDocument();

    // Assert Replay controls toolbar is active and rendered
    await waitFor(() => {
      expect(screen.getByText('Synthetic demo scenario (news + social)')).toBeInTheDocument();
      expect(screen.getByText('5 / 25')).toBeInTheDocument();
    });
  });

  it('renders signals feed and signal inspector details', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getAllByText('$APEX').length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Apex Industrial Holdings missed coupon payment/i).length).toBeGreaterThan(0);
      expect(screen.getByText('CREDIT (88%)')).toBeInTheDocument();
      expect(screen.getByText('ACTION ELIGIBLE')).toBeInTheDocument();
    });
  });

  it('allows switching between terminal workspace tabs', async () => {
    render(<App />);

    // Wait for initial render
    await waitFor(() => {
      expect(screen.getAllByText('$APEX').length).toBeGreaterThan(0);
    });

    // Switch to Wholesale Stress tab
    const stressTabButton = screen.getByRole('button', { name: /Wholesale Stress/i });
    fireEvent.click(stressTabButton);

    expect(screen.getByText('Funded Book Value (PRD §9.1)')).toBeInTheDocument();
    expect(screen.getByText('Derivative Gross Notional (Segregated)')).toBeInTheDocument();
    // funded book value is rendered from /api/portfolio data (no longer hardcoded)
    expect(await screen.findByText('$500,000,000')).toBeInTheDocument();
    expect(screen.getByText('$150,000,000')).toBeInTheDocument();

    // Switch to NLP Sandbox tab
    const playgroundTabButton = screen.getByRole('button', { name: /NLP Sandbox/i });
    fireEvent.click(playgroundTabButton);

    expect(
      screen.getByText(/NLP Pipeline Sandbox & Risk Signal Generator/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Process Through NLP Pipeline/i })
    ).toBeInTheDocument();

    // Switch to Datasets tab
    const datasetsTabButton = screen.getByRole('button', { name: /Datasets & Readiness/i });
    fireEvent.click(datasetsTabButton);

    await waitFor(() => {
      expect(screen.getByText('data/news_demo.csv')).toBeInTheDocument();
    });

    // Switch to Evaluation & Governance tab
    const evalTabButton = screen.getByRole('button', { name: /Evaluation & Governance/i });
    fireEvent.click(evalTabButton);

    expect(
      screen.getByText(/Evaluation Framework & Release Gates/i)
    ).toBeInTheDocument();
  });

  it('renders clear unavailable state without hardcoded fallback records when API fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new Error('Network error: Connection refused')))
    );

    render(<App />);

    // Switch to Datasets tab to verify failure state
    const datasetsTabButton = screen.getByRole('button', { name: /Datasets & Readiness/i });
    fireEvent.click(datasetsTabButton);

    await waitFor(() => {
      expect(screen.getByText(/Dataset Manifest Unavailable/i)).toBeInTheDocument();
      expect(screen.getByText('0 Registered Datasets')).toBeInTheDocument();
      expect(screen.getByText('Manifest: Unavailable')).toBeInTheDocument();
      expect(screen.getByText('AWAITING MANIFEST')).toBeInTheDocument();
    });

    // Verify absolutely no hardcoded fallback records are rendered
    expect(screen.queryByText('data/news_demo.csv')).not.toBeInTheDocument();
    expect(screen.queryByText('data/social_demo.csv')).not.toBeInTheDocument();
    expect(screen.queryByText('data/wholesale_positions.json')).not.toBeInTheDocument();
  });
});
