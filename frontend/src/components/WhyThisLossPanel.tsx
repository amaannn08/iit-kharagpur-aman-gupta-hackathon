import { StressRunResult } from '../api/client';

interface Props {
  result: StressRunResult | null;
  triggerHeadline?: string | null;
  evidenceSpan?: string | null;
}

const usd = (v: number) => `${v < 0 ? '-' : ''}$${Math.abs(v / 1e6).toFixed(2)}M`;

export function WhyThisLossPanel({ result, triggerHeadline, evidenceSpan }: Props) {
  if (!result) {
    return (
      <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4 text-xs text-zinc-500 font-mono" data-testid="why-this-loss-panel">
        No stress test result selected to inspect.
      </div>
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
    <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4 space-y-4 text-xs" data-testid="why-this-loss-panel">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
        <div>
          <h3 className="text-sm font-bold text-zinc-100">Why this loss: Attribution Inspector</h3>
          <p className="text-[11px] text-zinc-400 font-mono">
            Decomposition into pricing, credit, equity and operational factors
          </p>
        </div>
        <div className="text-right">
          <span className={`text-base font-bold font-mono ${result.total_pnl_usd < 0 ? 'text-red-400' : 'text-emerald-400'}`}>
            {usd(result.total_pnl_usd)}
          </span>
          <div className="text-[10px] text-zinc-400">
            Sum of components: {usd(compSum)}
          </div>
        </div>
      </div>

      {/* Trigger & Evidence */}
      {(triggerHeadline || evidenceSpan || result.shock_parameters?.catalog_entry) && (
        <div className="bg-black p-3 rounded border border-zinc-800 space-y-1.5" data-testid="trigger-evidence">
          <div className="text-[11px] text-zinc-400 font-semibold uppercase tracking-wider">Trigger Headline & Evidence</div>
          {triggerHeadline && (
            <div className="text-white font-medium text-xs">
              "{triggerHeadline}"
            </div>
          )}
          {evidenceSpan && (
            <div className="p-2 rounded bg-zinc-950 border border-zinc-800 font-sans text-[11px] text-zinc-100">
              Evidence: <span className="underline decoration-zinc-400">{evidenceSpan}</span>
            </div>
          )}
          {result.shock_parameters?.description && (
            <div className="text-[11px] text-zinc-400 italic">
              Scenario anchor: {result.shock_parameters.description}
            </div>
          )}
        </div>
      )}

      {/* Shock Parameters & Rating Tiering */}
      <div className="bg-black p-3 rounded border border-zinc-800 space-y-1.5" data-testid="shock-params">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-zinc-400 font-semibold uppercase tracking-wider">Shock Calibration</span>
          <span className="px-2 py-0.5 rounded text-[10px] bg-zinc-900 border border-zinc-700 text-zinc-200 font-mono font-bold">
            {result.shock_parameters?.rating_tiered ? 'Rating-Tiered (IG/HY)' : 'Uniform'}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 font-mono text-[11px]">
          <div className="p-2 rounded bg-zinc-950 border border-zinc-800">
            <span className="text-zinc-500 text-[10px] block">SPREAD SHIFT</span>
            <span className="text-white font-bold">
              {result.shock_parameters?.bond_spread_shift_bps ?? 0} bps
            </span>
          </div>
          <div className="p-2 rounded bg-zinc-950 border border-zinc-800">
            <span className="text-zinc-500 text-[10px] block">LOAN ΔPD</span>
            <span className="text-red-400 font-bold">
              {((result.shock_parameters?.loan_pd_increment ?? 0) * 100).toFixed(2)} pp
            </span>
          </div>
          <div className="p-2 rounded bg-zinc-950 border border-zinc-800">
            <span className="text-zinc-500 text-[10px] block">BENCHMARK YIELD</span>
            <span className="text-white font-bold">
              {result.shock_parameters?.benchmark_yield_shift_bps ?? 0} bps
            </span>
          </div>
          <div className="p-2 rounded bg-zinc-950 border border-zinc-800">
            <span className="text-zinc-500 text-[10px] block">EQUITY SHOCK</span>
            <span className="text-red-400 font-bold">
              {((result.shock_parameters?.equity_shock_pct ?? 0) * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Component Breakdown Bars */}
      <div className="space-y-2" data-testid="component-breakdown">
        <div className="text-[11px] text-zinc-400 font-semibold uppercase tracking-wider">Loss Component Breakdown</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {Object.entries(COMPONENT_LABELS).map(([key, label]) => {
            const val = comp[key] ?? 0;
            return (
              <div
                key={key}
                data-testid={`component-${key}`}
                className="p-2 rounded border bg-zinc-900 border-zinc-800 flex items-center justify-between font-mono"
              >
                <span className="text-[11px] font-sans font-medium text-zinc-300">{label}</span>
                <span className={`font-bold text-xs ${val < 0 ? 'text-red-400' : val > 0 ? 'text-emerald-400' : 'text-zinc-400'}`}>
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
          <div className="text-[11px] text-zinc-400 font-semibold uppercase tracking-wider">
            Top 5 Impacted Positions & Drivers
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-[11px]">
              <thead className="text-zinc-500 border-b border-zinc-800">
                <tr>
                  <th className="pb-1.5">Position</th>
                  <th className="pb-1.5">Counterparty</th>
                  <th className="pb-1.5">Driver</th>
                  <th className="pb-1.5">Dominant Factor</th>
                  <th className="pb-1.5 text-right">P&L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {topPositions.map((pos) => (
                  <tr key={pos.position_id} className="hover:bg-zinc-900/40">
                    <td className="py-1 text-white font-medium">{pos.position_id}</td>
                    <td className="text-zinc-200 font-sans">{pos.counterparty_name} ({pos.entity_id})</td>
                    <td className="text-zinc-400">{pos.driver || 'direct'}</td>
                    <td className="text-zinc-300 uppercase text-[10px] font-bold">{pos.dominant_component}</td>
                    <td className={`text-right font-bold ${pos.pnl_usd < 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                      {usd(pos.pnl_usd)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
