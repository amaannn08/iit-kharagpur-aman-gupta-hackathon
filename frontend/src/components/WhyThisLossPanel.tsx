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
      <Card className="text-xs text-[#9CA3AF] font-mono" data-testid="why-this-loss-panel">
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
      <div className="flex items-center justify-between border-b border-[#ECEDEC] pb-3">
        <div>
          <h3 className="text-sm font-bold text-[#111827]">Why this loss: Attribution Inspector</h3>
          <p className="text-[11px] text-[#6B7280]">
            Decomposition into pricing, credit, equity and operational factors
          </p>
        </div>
        <div className="text-right font-mono">
          <span className={`text-base font-bold ${result.total_pnl_usd < 0 ? 'text-[#DC2626]' : 'text-[#1F6B45]'}`}>
            {usd(result.total_pnl_usd)}
          </span>
          <div className="text-[10px] text-[#6B7280]">
            Sum of components: {usd(compSum)}
          </div>
        </div>
      </div>

      {/* Trigger & Evidence */}
      {(triggerHeadline || evidenceSpan || result.shock_parameters?.catalog_entry) && (
        <div className="bg-[#F9FAF9] p-3.5 rounded-2xl border border-[#ECEDEC] space-y-1.5" data-testid="trigger-evidence">
          <div className="text-[10px] text-[#6B7280] font-semibold uppercase font-mono tracking-wider">
            Trigger Headline &amp; Evidence
          </div>
          {triggerHeadline && (
            <div className="text-[#111827] font-semibold text-xs">
              "{triggerHeadline}"
            </div>
          )}
          {evidenceSpan && (
            <div className="p-2.5 rounded-xl bg-white border border-[#ECEDEC] font-sans text-[11px] text-[#374151]">
              Evidence: <span className="bg-[#FEF3C7] text-[#92400E] px-1 py-0.5 rounded font-medium border-b border-amber-300">{evidenceSpan}</span>
            </div>
          )}
          {result.shock_parameters?.description && (
            <div className="text-[11px] text-[#6B7280] italic">
              Scenario anchor: {result.shock_parameters.description}
            </div>
          )}
        </div>
      )}

      {/* Shock Parameters & Rating Tiering */}
      <div className="bg-[#F9FAF9] p-3.5 rounded-2xl border border-[#ECEDEC] space-y-2" data-testid="shock-params">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-[#6B7280] font-semibold uppercase font-mono tracking-wider">Shock Calibration</span>
          <span className="px-2 py-0.5 rounded-full text-[10px] bg-white border border-[#ECEDEC] text-[#14532D] font-mono font-bold">
            {result.shock_parameters?.rating_tiered ? 'Rating-Tiered (IG/HY)' : 'Uniform'}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 font-mono text-[11px]">
          <div className="p-2.5 rounded-xl bg-white border border-[#ECEDEC]">
            <span className="text-[#9CA3AF] text-[10px] block font-sans">SPREAD SHIFT</span>
            <span className="text-[#111827] font-bold">
              {result.shock_parameters?.bond_spread_shift_bps ?? 0} bps
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-white border border-[#ECEDEC]">
            <span className="text-[#9CA3AF] text-[10px] block font-sans">LOAN &Delta;PD</span>
            <span className="text-[#DC2626] font-bold">
              {((result.shock_parameters?.loan_pd_increment ?? 0) * 100).toFixed(2)} pp
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-white border border-[#ECEDEC]">
            <span className="text-[#9CA3AF] text-[10px] block font-sans">BENCHMARK YIELD</span>
            <span className="text-[#111827] font-bold">
              {result.shock_parameters?.benchmark_yield_shift_bps ?? 0} bps
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-white border border-[#ECEDEC]">
            <span className="text-[#9CA3AF] text-[10px] block font-sans">EQUITY SHOCK</span>
            <span className="text-[#DC2626] font-bold">
              {((result.shock_parameters?.equity_shock_pct ?? 0) * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Component Breakdown Bars */}
      <div className="space-y-2" data-testid="component-breakdown">
        <div className="text-[10px] text-[#6B7280] font-semibold uppercase font-mono tracking-wider">
          Loss Component Breakdown
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {Object.entries(COMPONENT_LABELS).map(([key, label]) => {
            const val = comp[key] ?? 0;
            return (
              <div
                key={key}
                data-testid={`component-${key}`}
                className="p-2.5 rounded-xl border bg-white border-[#ECEDEC] flex items-center justify-between font-mono"
              >
                <span className="text-[11px] font-sans font-medium text-[#4B5563]">{label}</span>
                <span className={`font-bold text-xs ${val < 0 ? 'text-[#DC2626]' : val > 0 ? 'text-[#1F6B45]' : 'text-[#9CA3AF]'}`}>
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
          <div className="text-[10px] text-[#6B7280] font-semibold uppercase font-mono tracking-wider">
            Top 5 Impacted Positions &amp; Drivers
          </div>
          <div className="overflow-x-auto rounded-xl border border-[#ECEDEC]">
            <table className="w-full text-left font-mono text-[11px] bg-white">
              <thead className="text-[#6B7280] bg-[#F9FAF9] border-b border-[#ECEDEC]">
                <tr>
                  <th className="py-2 px-3">Position</th>
                  <th className="py-2 px-3">Counterparty</th>
                  <th className="py-2 px-3">Driver</th>
                  <th className="py-2 px-3">Dominant Factor</th>
                  <th className="py-2 px-3 text-right">P&amp;L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#ECEDEC]">
                {topPositions.map((pos) => (
                  <tr key={pos.position_id} className="hover:bg-[#F9FAF9]">
                    <td className="py-2 px-3 text-[#111827] font-bold">{pos.position_id}</td>
                    <td className="py-2 px-3 text-[#374151] font-sans">{pos.counterparty_name} ({pos.entity_id})</td>
                    <td className="py-2 px-3 text-[#6B7280]">{pos.driver || 'direct'}</td>
                    <td className="py-2 px-3 text-[#14532D] uppercase text-[10px] font-bold">{pos.dominant_component}</td>
                    <td className={`py-2 px-3 text-right font-bold ${pos.pnl_usd < 0 ? 'text-[#DC2626]' : 'text-[#1F6B45]'}`}>
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
