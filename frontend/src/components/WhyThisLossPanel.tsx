import { StressRunResult } from '../api/client';
import { Card } from './ui/Card';

interface Props {
  result: StressRunResult | null;
  triggerHeadline?: string | null;
  evidenceSpan?: string | null;
}

const usd = (v: number) => `${v < 0 ? '-' : ''}$${Math.abs(v / 1e6).toFixed(2)}M`;

export function WhyThisLossPanel({ result, triggerHeadline, evidenceSpan }: Props) {
  if (!result) {
    return (
      <Card className="text-xs text-theme-subtle font-mono" data-testid="why-this-loss-panel">
        No stress test result selected to inspect.
      </Card>
    );
  }

  const attr = result.attribution;
  const comp = attr?.by_component ?? {};
  const topPositions = attr?.top_positions ?? [];

  const COMPONENT_LABELS: Record<string, string> = {
    rates_usd: 'Rates (Yield / DV01)',
    spread_usd: 'Credit Spread',
    pd_usd: 'Loan PD Shock',
    lgd_usd: 'Loan LGD Move',
    equity_usd: 'Equity Shock',
    operational_usd: 'Operational Loss (Fraud)',
    clamp_usd: 'Floor Clamp',
  };

  const compSum = Object.values(comp).reduce((acc, v) => acc + v, 0);

  return (
    <Card className="space-y-4 text-xs" data-testid="why-this-loss-panel">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-theme-border pb-3">
        <div>
          <h3 className="text-sm font-bold text-theme-text">Why this loss: Attribution Inspector</h3>
          <p className="text-[11px] text-theme-muted">
            Decomposition into pricing, credit, equity and operational factors
          </p>
        </div>
        <div className="text-right font-mono">
          <span className={`text-base font-bold ${result.total_pnl_usd < 0 ? 'text-theme-loss' : 'text-theme-primary'}`}>
            {usd(result.total_pnl_usd)}
          </span>
          <div className="text-[10px] text-theme-muted">
            Sum of components: {usd(compSum)}
          </div>
        </div>
      </div>

      {/* Trigger & Evidence */}
      {(triggerHeadline || evidenceSpan || result.shock_parameters?.catalog_entry) && (
        <div className="bg-theme-card-subtle p-3.5 rounded-2xl border border-theme-border space-y-1.5" data-testid="trigger-evidence">
          <div className="text-[10px] text-theme-muted font-semibold uppercase font-mono tracking-wider">
            Trigger Headline &amp; Evidence
          </div>
          {triggerHeadline && (
            <div className="text-theme-text font-semibold text-xs">
              "{triggerHeadline}"
            </div>
          )}
          {evidenceSpan && (
            <div className="p-2.5 rounded-xl bg-theme-card border border-theme-border font-sans text-[11px] text-theme-text-body">
              Evidence: <span className="bg-theme-warn-bg text-theme-warn-dark px-1 py-0.5 rounded font-medium border-b border-theme-warn-border">{evidenceSpan}</span>
            </div>
          )}
          {result.shock_parameters?.description && (
            <div className="text-[11px] text-theme-muted italic">
              Scenario anchor: {result.shock_parameters.description}
            </div>
          )}
        </div>
      )}

      {/* Shock Parameters & Rating Tiering */}
      <div className="bg-theme-card-subtle p-3.5 rounded-2xl border border-theme-border space-y-2" data-testid="shock-params">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-theme-muted font-semibold uppercase font-mono tracking-wider">Shock Calibration</span>
          <span className="px-2 py-0.5 rounded-full text-[10px] bg-theme-card border border-theme-border text-theme-primary-text font-mono font-bold">
            {result.shock_parameters?.rating_tiered ? 'Rating-Tiered (IG/HY)' : 'Uniform'}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 font-mono text-[11px]">
          <div className="p-2.5 rounded-xl bg-theme-card border border-theme-border">
            <span className="text-theme-subtle text-[10px] block font-sans">SPREAD SHIFT</span>
            <span className="text-theme-text font-bold">
              {result.shock_parameters?.bond_spread_shift_bps ?? 0} bps
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-theme-card border border-theme-border">
            <span className="text-theme-subtle text-[10px] block font-sans">LOAN &Delta;PD</span>
            <span className="text-theme-loss font-bold">
              {((result.shock_parameters?.loan_pd_increment ?? 0) * 100).toFixed(2)} pp
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-theme-card border border-theme-border">
            <span className="text-theme-subtle text-[10px] block font-sans">BENCHMARK YIELD</span>
            <span className="text-theme-text font-bold">
              {result.shock_parameters?.benchmark_yield_shift_bps ?? 0} bps
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-theme-card border border-theme-border">
            <span className="text-theme-subtle text-[10px] block font-sans">EQUITY SHOCK</span>
            <span className="text-theme-loss font-bold">
              {((result.shock_parameters?.equity_shock_pct ?? 0) * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Component Breakdown Bars */}
      <div className="space-y-2" data-testid="component-breakdown">
        <div className="text-[10px] text-theme-muted font-semibold uppercase font-mono tracking-wider">
          Loss Component Breakdown
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {Object.entries(COMPONENT_LABELS).map(([key, label]) => {
            const val = comp[key] ?? 0;
            return (
              <div
                key={key}
                data-testid={`component-${key}`}
                className="p-2.5 rounded-xl border bg-theme-card border-theme-border flex items-center justify-between font-mono"
              >
                <span className="text-[11px] font-sans font-medium text-theme-text-secondary">{label}</span>
                <span className={`font-bold text-xs ${val < 0 ? 'text-theme-loss' : val > 0 ? 'text-theme-primary' : 'text-theme-subtle'}`}>
                  {usd(val)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top 5 Positions */}
      {topPositions.length > 0 && (
        <div className="space-y-2" data-testid="top-positions">
          <div className="text-[10px] text-theme-muted font-semibold uppercase font-mono tracking-wider">
            Top 5 Impacted Positions &amp; Drivers
          </div>
          <div className="overflow-x-auto rounded-xl border border-theme-border">
            <table className="w-full text-left font-mono text-[11px] bg-theme-card">
              <thead className="text-theme-muted bg-theme-card-subtle border-b border-theme-border">
                <tr>
                  <th className="py-2 px-3">Position</th>
                  <th className="py-2 px-3">Counterparty</th>
                  <th className="py-2 px-3">Driver</th>
                  <th className="py-2 px-3">Dominant Factor</th>
                  <th className="py-2 px-3 text-right">P&amp;L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-theme-border">
                {topPositions.map((pos) => (
                  <tr key={pos.position_id} className="hover:bg-theme-card-subtle">
                    <td className="py-2 px-3 text-theme-text font-bold">{pos.position_id}</td>
                    <td className="py-2 px-3 text-theme-text-body font-sans">{pos.counterparty_name} ({pos.entity_id})</td>
                    <td className="py-2 px-3 text-theme-muted">{pos.driver || 'direct'}</td>
                    <td className="py-2 px-3 text-theme-primary-text uppercase text-[10px] font-bold">{pos.dominant_component}</td>
                    <td className={`py-2 px-3 text-right font-bold ${pos.pnl_usd < 0 ? 'text-theme-loss' : 'text-theme-primary'}`}>
                      {usd(pos.pnl_usd)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Card>
  );
}
