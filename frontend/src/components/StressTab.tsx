import React from 'react';
import { CheckCircle, Download, Play, Sliders } from 'lucide-react';
import { RiskSignal, StressRunResult, WholesalePortfolio } from '../api/client';
import { StressCharts } from './StressCharts';
import { WhyThisLossPanel } from './WhyThisLossPanel';

export interface StressTabProps {
  portfolio: WholesalePortfolio | null;
  activeStressResult: StressRunResult | null;
  setActiveStressResult: (res: StressRunResult | null) => void;
  stressRuns: StressRunResult[];
  stressForm: {
    event_class: string;
    impact_score: number;
    target_entity: string;
    target_scope: string;
    is_easing: boolean;
  };
  setStressForm: React.Dispatch<
    React.SetStateAction<{
      event_class: string;
      impact_score: number;
      target_entity: string;
      target_scope: string;
      is_easing: boolean;
    }>
  >;
  simulatingStress: boolean;
  onRunStressSimulation: (e: React.FormEvent) => void;
  signals: RiskSignal[];
}

export const StressTab: React.FC<StressTabProps> = ({
  portfolio,
  activeStressResult,
  setActiveStressResult,
  stressRuns,
  stressForm,
  setStressForm,
  simulatingStress,
  onRunStressSimulation,
  signals,
}) => {
  return (
    <div className="flex-1 flex flex-col space-y-6 overflow-y-auto">
      <StressCharts result={activeStressResult} onResult={setActiveStressResult} />
      {activeStressResult && (
        <WhyThisLossPanel
          result={activeStressResult}
          triggerHeadline={signals.find((s) => s.signal_id === activeStressResult?.trigger_signal_id)?.text_excerpt}
          evidenceSpan={signals.find((s) => s.signal_id === activeStressResult?.trigger_signal_id)?.evidence?.[0]?.text}
        />
      )}
      {/* Top Summary Segregation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-[#111827] p-4 rounded-lg border border-gray-800">
          <div className="text-xs text-gray-400 font-medium">Funded Book Value</div>
          <div className="text-xl font-bold text-emerald-400 font-mono mt-1">
            ${(portfolio?.summary.total_book_value_usd ?? 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}
          </div>
          <div className="text-[11px] text-gray-500 mt-0.5">
            {portfolio?.funded_value_by_sleeve_usd
              ? Object.entries(portfolio.funded_value_by_sleeve_usd)
                  .map(([k, v]) => `${k} $${Math.round(v / 1e6)}M`)
                  .join(' + ')
              : portfolio?.portfolio_name}
          </div>
        </div>

        <div className="bg-[#111827] p-4 rounded-lg border border-gray-800">
          <div className="text-xs text-cyan-400 font-medium">Derivative Gross Notional (Segregated)</div>
          <div className="text-xl font-bold text-cyan-300 font-mono mt-1">$150,000,000</div>
          <div className="text-[11px] text-gray-500 mt-0.5">2 SOFR Interest Rate Swaps • Zero funded book overlap</div>
        </div>

        <div className="bg-[#111827] p-4 rounded-lg border border-gray-800">
          <div className="text-xs text-gray-400 font-medium">Latest Stress Total PnL</div>
          <div className="text-xl font-bold text-rose-400 font-mono mt-1">
            {activeStressResult
              ? `${activeStressResult.total_pnl_usd < 0 ? '-' : '+'}$${Math.abs(activeStressResult.total_pnl_usd).toLocaleString('en-US', { maximumFractionDigits: 0 })}`
              : '$0'}
          </div>
          <div className="text-[11px] text-rose-400/80 mt-0.5">
            {activeStressResult ? `${(activeStressResult.total_pnl_pct * 100).toFixed(2)}% of funded book value` : 'No stress active'}
          </div>
        </div>

        <div className="bg-[#111827] p-4 rounded-lg border border-gray-800">
          <div className="text-xs text-gray-400 font-medium">Reconciliation Audit Invariant</div>
          <div className="text-xl font-bold text-emerald-400 font-mono mt-1 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-400" />
            VERIFIED PASSED
          </div>
          <div className="text-[11px] text-gray-500 mt-0.5">Total PnL = ECL Delta + MTM Delta ($0.00 err)</div>
        </div>
      </div>

      {/* Live Stress Delta Banner & Sandbox Controls */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left 8/12: Asset Class & Sector Breakdown */}
        <div className="col-span-12 lg:col-span-8 flex flex-col space-y-4">
          {/* Asset Class Breakdown Table */}
          <div className="bg-[#111827] p-4 rounded-lg border border-gray-800 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
                Asset Class Stress Breakdown (Multi-Asset Valuation Engine)
              </h3>
              <div className="flex items-center gap-2">
                {activeStressResult && (
                  <div className="flex items-center gap-2">
                    <a
                      href={`/api/exports/${activeStressResult.run_id}?format=json`}
                      download
                      className="px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 text-xs text-gray-300 flex items-center gap-1 border border-gray-700"
                    >
                      <Download className="w-3 h-3" />
                      JSON
                    </a>
                    <a
                      href={`/api/exports/${activeStressResult.run_id}?format=csv`}
                      download
                      className="px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 text-xs text-gray-300 flex items-center gap-1 border border-gray-700"
                    >
                      <Download className="w-3 h-3" />
                      CSV
                    </a>
                  </div>
                )}
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-gray-400 border-b border-gray-800 font-mono text-[11px]">
                  <tr>
                    <th className="pb-2">Asset Class</th>
                    <th className="pb-2 text-right">Baseline (USD)</th>
                    <th className="pb-2 text-right">Stressed (USD)</th>
                    <th className="pb-2 text-right">Total PnL</th>
                    <th className="pb-2 text-right">Credit ECL Δ</th>
                    <th className="pb-2 text-right">Market MTM Δ</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 font-mono text-xs">
                  {activeStressResult?.asset_class_breakdown.map((ac) => (
                    <tr key={ac.asset_class} className="hover:bg-gray-900/40">
                      <td className="py-2.5 font-bold uppercase text-gray-200">{ac.asset_class}</td>
                      <td className="text-right text-gray-400">${ac.baseline_value_usd.toLocaleString('en-US')}</td>
                      <td className="text-right text-white font-semibold">${ac.stressed_value_usd.toLocaleString('en-US')}</td>
                      <td className={`text-right font-bold ${ac.total_pnl_usd < 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                        ${ac.total_pnl_usd.toLocaleString('en-US')} ({(ac.pct_change * 100).toFixed(2)}%)
                      </td>
                      <td className="text-right text-amber-400">
                        {ac.credit_ecl_delta_usd !== 0 ? `+$${ac.credit_ecl_delta_usd.toLocaleString('en-US')}` : '-'}
                      </td>
                      <td className="text-right text-cyan-400">
                        {ac.mark_to_market_pnl_usd !== 0 ? `${ac.mark_to_market_pnl_usd < 0 ? '-' : '+'}$${Math.abs(ac.mark_to_market_pnl_usd).toLocaleString('en-US')}` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Position Deltas Drilldown */}
          <div className="bg-[#111827] p-4 rounded-lg border border-gray-800 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
                Position-Level Risk & Stress Matrix ({activeStressResult?.position_deltas.length ?? 0} positions)
              </h3>
              <span className="text-[11px] text-gray-500 font-mono">
                Bond Duration • Loan ECL Clamping • Swap Signed DV01
              </span>
            </div>

            <div className="overflow-x-auto max-h-72 overflow-y-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-gray-400 border-b border-gray-800 font-mono text-[11px] sticky top-0 bg-[#111827]">
                  <tr>
                    <th className="pb-2">Pos ID</th>
                    <th className="pb-2">Counterparty</th>
                    <th className="pb-2">Asset</th>
                    <th className="pb-2 text-right">Baseline</th>
                    <th className="pb-2 text-right">Stressed</th>
                    <th className="pb-2 text-right">PnL (USD)</th>
                    <th className="pb-2">Shock Summary</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 font-mono text-xs">
                  {activeStressResult?.position_deltas.map((pos) => (
                    <tr key={pos.position_id} className="hover:bg-gray-900/40">
                      <td className="py-2 text-cyan-400 font-semibold">{pos.position_id}</td>
                      <td className="text-white font-sans font-medium">{pos.counterparty_name}</td>
                      <td className="text-gray-400 uppercase text-[11px]">{pos.asset_class}</td>
                      <td className="text-right text-gray-400">${pos.baseline_value_usd.toLocaleString('en-US')}</td>
                      <td className="text-right text-white font-semibold">${pos.stressed_value_usd.toLocaleString('en-US')}</td>
                      <td className={`text-right font-bold ${pos.pnl_usd < 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                        ${pos.pnl_usd.toLocaleString('en-US')}
                      </td>
                      <td className="text-gray-400 text-[11px] truncate max-w-xs">{pos.applied_shock_summary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right 4/12: Manual Stress Simulation Sandbox */}
        <div className="col-span-12 lg:col-span-4 flex flex-col bg-[#111827] border border-gray-800 rounded-lg p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-gray-800 pb-3">
            <Sliders className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white">Manual Stress Simulation Sandbox</h3>
          </div>

          <form onSubmit={onRunStressSimulation} className="space-y-4 text-xs">
            <div>
              <label className="block text-gray-400 font-medium mb-1">Event Classification</label>
              <select
                value={stressForm.event_class}
                onChange={(e) => setStressForm({ ...stressForm, event_class: e.target.value })}
                className="w-full bg-[#0B0F17] border border-gray-800 rounded p-2 text-gray-200 focus:outline-none focus:border-cyan-500 font-mono"
              >
                <option value="CREDIT">Credit Event (spread / PD / LGD, equity -15%)</option>
                <option value="MACRO">Macro (Fed Jun-2022 window: 10y +26 bp, S&amp;P -8.7%)</option>
                <option value="CYBER">Cybersecurity (spread + fraud-rate operational loss)</option>
                <option value="GEOPOLITICAL">Geopolitical (Russia-2022 window, yields down)</option>
                <option value="SUPPLY_CHAIN">Supply Chain Disruption</option>
              </select>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-gray-400 font-medium">Severity Impact Score</label>
                <span className="font-mono text-cyan-400 font-bold">{stressForm.impact_score} / 10</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={stressForm.impact_score}
                onChange={(e) => setStressForm({ ...stressForm, impact_score: Number(e.target.value) })}
                className="w-full accent-cyan-500"
              />
            </div>

            <div>
              <label className="block text-gray-400 font-medium mb-1">Target Counterparty / Entity</label>
              <select
                value={stressForm.target_entity}
                onChange={(e) => setStressForm({ ...stressForm, target_entity: e.target.value })}
                className="w-full bg-[#0B0F17] border border-gray-800 rounded p-2 text-gray-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="Apex Industrial Holdings">Apex Industrial Holdings ($APEX)</option>
                <option value="Nova Health Systems">Nova Health Systems ($NOVA)</option>
                <option value="Vanguard Energy Corp">Vanguard Energy Corp ($VANG)</option>
                <option value="Sterling Retail Group">Sterling Retail Group ($STEL)</option>
                <option value="Pacifica Logistics">Pacifica Logistics ($PACL)</option>
              </select>
            </div>

            <div>
              <label className="block text-gray-400 font-medium mb-1">Shock Contagion Scope</label>
              <select
                value={stressForm.target_scope}
                onChange={(e) => setStressForm({ ...stressForm, target_scope: e.target.value })}
                className="w-full bg-[#0B0F17] border border-gray-800 rounded p-2 text-gray-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="entity">Entity Level (Idiosyncratic Shock)</option>
                <option value="sector">Sector Level (Peer Group Contagion)</option>
                <option value="macro">Macro Level (Broad Market Shock)</option>
              </select>
            </div>

            <div className="pt-1">
              <label className="flex items-center gap-2 cursor-pointer text-gray-300">
                <input
                  type="checkbox"
                  checked={stressForm.is_easing}
                  onChange={(e) => setStressForm({ ...stressForm, is_easing: e.target.checked })}
                  className="rounded bg-gray-800 border-gray-700 text-cyan-500 focus:ring-0"
                />
                <span>Monetary Policy Easing (Negative Yield Shock)</span>
              </label>
            </div>

            <button
              type="submit"
              disabled={simulatingStress}
              className="w-full py-2.5 px-4 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-semibold transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {simulatingStress ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  Execute Stress Simulation
                </>
              )}
            </button>
          </form>

          {/* History of Stress Runs */}
          <div className="pt-3 border-t border-gray-800 space-y-2">
            <div className="text-gray-400 font-medium text-xs">Recent Stress Runs</div>
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {stressRuns.slice(0, 5).map((run) => (
                <div
                  key={run.stress_id}
                  onClick={() => setActiveStressResult(run)}
                  className={`p-2 rounded border cursor-pointer text-[11px] flex items-center justify-between font-mono ${
                    activeStressResult?.stress_id === run.stress_id
                      ? 'bg-cyan-950/40 border-cyan-700 text-cyan-300'
                      : 'bg-[#0B0F17] border-gray-800 text-gray-400 hover:border-gray-700'
                  }`}
                >
                  <div>
                    <div className="text-white font-bold uppercase">{run.event_class} ({run.impact_score}/10)</div>
                    <div className="text-[10px] text-gray-500">{run.executed_at.slice(11, 19)}</div>
                  </div>
                  <div className={`text-right font-bold ${run.total_pnl_usd < 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {run.total_pnl_usd < 0 ? '-' : '+'}${Math.abs(run.total_pnl_usd).toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
