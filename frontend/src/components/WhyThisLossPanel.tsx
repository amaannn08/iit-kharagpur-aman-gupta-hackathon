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
      <div className="bg-[#111827] border border-gray-800 rounded-lg p-4 text-xs text-gray-500 font-mono" data-testid="why-this-loss-panel">
        No stress test result selected to inspect.
      </div>
    );
  }

  const attr = result.attribution;
  const comp = attr?.by_component ?? {};
  const topPositions = attr?.top_positions ?? [];

  const COMPONENT_LABELS: Record<string, { label: string; color: string }> = {
    rates_usd: { label: 'Rates (Yield / DV01)', color: 'text-cyan-400 bg-cyan-950/40 border-cyan-800' },
    spread_usd: { label: 'Credit Spread', color: 'text-amber-400 bg-amber-950/40 border-amber-800' },
    pd_usd: { label: 'Loan PD Shock', color: 'text-rose-400 bg-rose-950/40 border-rose-800' },
    lgd_usd: { label: 'Loan LGD Move', color: 'text-orange-400 bg-orange-950/40 border-orange-800' },
    equity_usd: { label: 'Equity Shock', color: 'text-purple-400 bg-purple-950/40 border-purple-800' },
    operational_usd: { label: 'Operational Loss (Fraud)', color: 'text-red-400 bg-red-950/40 border-red-800' },
    clamp_usd: { label: 'Floor Clamp', color: 'text-gray-400 bg-gray-900 border-gray-700' },
  };

  const compSum = Object.values(comp).reduce((acc, v) => acc + v, 0);

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-lg p-4 space-y-4 text-xs" data-testid="why-this-loss-panel">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-800 pb-2">
        <div>
          <h3 className="text-sm font-bold text-gray-200">Why this loss: Attribution Inspector</h3>
          <p className="text-[11px] text-gray-400 font-mono">
            Decomposition into pricing, credit, equity and operational factors
          </p>
        </div>
        <div className="text-right">
          <span className={`text-base font-bold font-mono ${result.total_pnl_usd < 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
            {usd(result.total_pnl_usd)}
          </span>
          <div className="text-[10px] text-gray-400">
            Sum of components: {usd(compSum)}
          </div>
        </div>
      </div>

      {/* Trigger & Evidence */}
      {(triggerHeadline || evidenceSpan || result.shock_parameters?.catalog_entry) && (
        <div className="bg-[#0B0F17] p-3 rounded border border-gray-800 space-y-1.5" data-testid="trigger-evidence">
          <div className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider">Trigger Headline & Evidence</div>
          {triggerHeadline && (
            <div className="text-white font-medium text-xs">
              "{triggerHeadline}"
            </div>
          )}
          {evidenceSpan && (
            <div className="p-2 rounded bg-black/40 border border-gray-800 font-sans text-[11px] text-cyan-300">
              Evidence: <span className="underline decoration-cyan-500">{evidenceSpan}</span>
            </div>
          )}
          {result.shock_parameters?.description && (
            <div className="text-[11px] text-gray-400 italic">
              Scenario anchor: {result.shock_parameters.description}
            </div>
          )}
        </div>
      )}

      {/* Shock Parameters & Rating Tiering */}
      <div className="bg-[#0B0F17] p-3 rounded border border-gray-800 space-y-1.5" data-testid="shock-params">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider">Shock Calibration</span>
          <span className="px-1.5 py-0.5 rounded text-[10px] bg-cyan-950 border border-cyan-800 text-cyan-300 font-mono">
            {result.shock_parameters?.rating_tiered ? 'Rating-Tiered (IG/HY)' : 'Uniform'}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 font-mono text-[11px]">
          <div className="p-1.5 rounded bg-gray-900 border border-gray-800">
            <span className="text-gray-500 text-[10px] block">SPREAD SHIFT</span>
            <span className="text-amber-400 font-bold">
              {result.shock_parameters?.bond_spread_shift_bps ?? 0} bps
            </span>
          </div>
          <div className="p-1.5 rounded bg-gray-900 border border-gray-800">
            <span className="text-gray-500 text-[10px] block">LOAN ΔPD</span>
            <span className="text-rose-400 font-bold">
              {((result.shock_parameters?.loan_pd_increment ?? 0) * 100).toFixed(2)} pp
            </span>
          </div>
          <div className="p-1.5 rounded bg-gray-900 border border-gray-800">
            <span className="text-gray-500 text-[10px] block">BENCHMARK YIELD</span>
            <span className="text-cyan-400 font-bold">
              {result.shock_parameters?.benchmark_yield_shift_bps ?? 0} bps
            </span>
          </div>
          <div className="p-1.5 rounded bg-gray-900 border border-gray-800">
            <span className="text-gray-500 text-[10px] block">EQUITY SHOCK</span>
            <span className="text-purple-400 font-bold">
              {((result.shock_parameters?.equity_shock_pct ?? 0) * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Component Breakdown Bars */}
      <div className="space-y-2" data-testid="component-breakdown">
        <div className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider">Loss Component Breakdown</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {Object.entries(COMPONENT_LABELS).map(([key, meta]) => {
            const val = comp[key] ?? 0;
            return (
              <div
                key={key}
                data-testid={`component-${key}`}
                className={`p-2 rounded border flex items-center justify-between font-mono ${meta.color}`}
              >
                <span className="text-[11px] font-sans font-medium text-gray-300">{meta.label}</span>
                <span className="font-bold text-xs">{usd(val)}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top 5 Positions */}
      {topPositions.length > 0 && (
        <div className="space-y-2" data-testid="top-positions">
          <div className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider">
            Top 5 Impacted Positions & Drivers
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-[11px]">
              <thead className="text-gray-500 border-b border-gray-800">
                <tr>
                  <th className="pb-1.5">Position</th>
                  <th className="pb-1.5">Counterparty</th>
                  <th className="pb-1.5">Driver</th>
                  <th className="pb-1.5">Dominant Factor</th>
                  <th className="pb-1.5 text-right">P&L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/40">
                {topPositions.map((pos) => (
                  <tr key={pos.position_id} className="hover:bg-gray-900/30">
                    <td className="py-1 text-cyan-400 font-medium">{pos.position_id}</td>
                    <td className="text-gray-200 font-sans">{pos.counterparty_name} ({pos.entity_id})</td>
                    <td className="text-gray-400">{pos.driver || 'direct'}</td>
                    <td className="text-amber-300 uppercase text-[10px] font-bold">{pos.dominant_component}</td>
                    <td className={`text-right font-bold ${pos.pnl_usd < 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
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
