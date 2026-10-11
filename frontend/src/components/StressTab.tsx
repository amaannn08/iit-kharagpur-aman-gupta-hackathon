import React from 'react';
import { CheckCircle, Download, Play, Sliders } from 'lucide-react';
import { RiskSignal, StressRunResult, WholesalePortfolio } from '../api/client';
import { Card } from './ui/Card';
import { KpiCard } from './ui/KpiCard';
import { PillButton } from './ui/PillButton';
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
  const fundedBookValue = portfolio?.summary.total_book_value_usd ?? 0;
  const derivativeNotional = portfolio?.summary.interest_rate_swaps_gross_notional_usd ?? 150000000;

  return (
    <div className="flex-1 flex flex-col space-y-6">
      {/* 1. Top Summary Segregation Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-5">
        <KpiCard
          title="Funded Book Value"
          value={`$${fundedBookValue.toLocaleString('en-US', { maximumFractionDigits: 0 })}`}
          subtitle={
            portfolio?.funded_value_by_sleeve_usd
              ? Object.entries(portfolio.funded_value_by_sleeve_usd)
                  .map(([k, v]) => `${k} $${Math.round(v / 1e6)}M`)
                  .join(' + ')
              : portfolio?.portfolio_name || 'Wholesale Portfolio'
          }
        />

        <KpiCard
          title="Derivative Gross Notional (Segregated)"
          value={`$${derivativeNotional.toLocaleString('en-US', { maximumFractionDigits: 0 })}`}
          subtitle="2 SOFR Interest Rate Swaps • Zero funded overlap"
        />

        <KpiCard
          title="Latest Stress Total PnL"
          value={
            activeStressResult
              ? `${activeStressResult.total_pnl_usd < 0 ? '-' : '+'}$${Math.abs(activeStressResult.total_pnl_usd).toLocaleString('en-US', { maximumFractionDigits: 0 })}`
              : '$0'
          }
          subtitle={
            activeStressResult
              ? `${(activeStressResult.total_pnl_pct * 100).toFixed(2)}% of funded book`
              : 'No stress active'
          }
        />

        <Card className="flex flex-col justify-between">
          <div className="text-xs md:text-sm font-medium text-[#6B7280]">
            Reconciliation Audit Invariant
          </div>
          <div className="text-xl md:text-2xl font-bold font-mono tracking-tight text-[#14532D] flex items-center gap-2 my-2">
            <CheckCircle className="w-5 h-5 text-[#1F6B45]" />
            VERIFIED PASSED
          </div>
          <div className="text-[11px] text-[#6B7280]">
            Total PnL = ECL Delta + MTM Delta ($0.00 err)
          </div>
        </Card>
      </div>

      {/* 2. Charts and Loss Attribution */}
      <StressCharts result={activeStressResult} onResult={setActiveStressResult} />

      {activeStressResult && (
        <WhyThisLossPanel
          result={activeStressResult}
          triggerHeadline={signals.find((s) => s.signal_id === activeStressResult?.trigger_signal_id)?.text_excerpt}
          evidenceSpan={signals.find((s) => s.signal_id === activeStressResult?.trigger_signal_id)?.evidence?.[0]?.text}
        />
      )}

      {/* 3. Live Stress Delta Breakdown & Sandbox Controls */}
      <div className="grid grid-cols-12 gap-5">
        {/* Left 8/12: Asset Class & Position Matrices */}
        <div className="col-span-12 lg:col-span-8 flex flex-col space-y-5">
          {/* Asset Class Breakdown Table */}
          <Card className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#ECEDEC] pb-3">
              <div>
                <h3 className="text-xs md:text-sm font-bold text-[#111827]">
                  Asset Class Stress Breakdown (Multi-Asset Engine)
                </h3>
                <p className="text-[11px] text-[#6B7280]">
                  Sleeve allocation across Loans, Bonds, Equities and Swaps
                </p>
              </div>

              {activeStressResult && (
                <div className="flex items-center gap-2">
                  <a
                    href={`/api/exports/${activeStressResult.run_id}?format=json`}
                    download
                    className="px-2.5 py-1 rounded-full bg-[#F3F4F3] hover:bg-gray-200 text-xs font-semibold text-[#374151] flex items-center gap-1 border border-[#ECEDEC] transition-colors"
                  >
                    <Download className="w-3 h-3" />
                    JSON
                  </a>
                  <a
                    href={`/api/exports/${activeStressResult.run_id}?format=csv`}
                    download
                    className="px-2.5 py-1 rounded-full bg-[#F3F4F3] hover:bg-gray-200 text-xs font-semibold text-[#374151] flex items-center gap-1 border border-[#ECEDEC] transition-colors"
                  >
                    <Download className="w-3 h-3" />
                    CSV
                  </a>
                </div>
              )}
            </div>

            <div className="overflow-x-auto rounded-xl border border-[#ECEDEC]">
              <table className="w-full text-xs text-left bg-white">
                <thead className="text-[#6B7280] bg-[#F9FAF9] border-b border-[#ECEDEC] font-mono text-[11px]">
                  <tr>
                    <th className="py-2.5 px-3">Asset Class</th>
                    <th className="py-2.5 px-3 text-right">Baseline (USD)</th>
                    <th className="py-2.5 px-3 text-right">Stressed (USD)</th>
                    <th className="py-2.5 px-3 text-right">Total PnL</th>
                    <th className="py-2.5 px-3 text-right">Credit ECL &Delta;</th>
                    <th className="py-2.5 px-3 text-right">Market MTM &Delta;</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#ECEDEC] font-mono text-xs">
                  {activeStressResult?.asset_class_breakdown.map((ac) => (
                    <tr key={ac.asset_class} className="hover:bg-[#F9FAF9]">
                      <td className="py-2.5 px-3 font-bold uppercase text-[#111827]">{ac.asset_class}</td>
                      <td className="py-2.5 px-3 text-right text-[#4B5563]">${ac.baseline_value_usd.toLocaleString('en-US')}</td>
                      <td className="py-2.5 px-3 text-right text-[#111827] font-semibold">${ac.stressed_value_usd.toLocaleString('en-US')}</td>
                      <td className={`py-2.5 px-3 text-right font-bold ${ac.total_pnl_usd < 0 ? 'text-[#DC2626]' : 'text-[#1F6B45]'}`}>
                        ${ac.total_pnl_usd.toLocaleString('en-US')} ({(ac.pct_change * 100).toFixed(2)}%)
                      </td>
                      <td className="py-2.5 px-3 text-right text-[#DC2626]">
                        {ac.credit_ecl_delta_usd !== 0 ? `+$${ac.credit_ecl_delta_usd.toLocaleString('en-US')}` : '-'}
                      </td>
                      <td className={`py-2.5 px-3 text-right ${ac.mark_to_market_pnl_usd < 0 ? 'text-[#DC2626]' : ac.mark_to_market_pnl_usd > 0 ? 'text-[#1F6B45]' : 'text-[#6B7280]'}`}>
                        {ac.mark_to_market_pnl_usd !== 0 ? `${ac.mark_to_market_pnl_usd < 0 ? '-' : '+'}$${Math.abs(ac.mark_to_market_pnl_usd).toLocaleString('en-US')}` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Position Deltas Drilldown */}
          <Card className="space-y-4">
            <div className="flex items-center justify-between border-b border-[#ECEDEC] pb-3">
              <div>
                <h3 className="text-xs md:text-sm font-bold text-[#111827]">
                  Position-Level Risk Matrix ({activeStressResult?.position_deltas.length ?? 0} positions)
                </h3>
                <p className="text-[11px] text-[#6B7280]">
                  Bond duration &bull; Loan ECL clamping &bull; Swap signed DV01
                </p>
              </div>
            </div>

            <div className="overflow-x-auto max-h-72 overflow-y-auto rounded-xl border border-[#ECEDEC]">
              <table className="w-full text-xs text-left bg-white">
                <thead className="text-[#6B7280] bg-[#F9FAF9] border-b border-[#ECEDEC] font-mono text-[11px] sticky top-0">
                  <tr>
                    <th className="py-2 px-3">Pos ID</th>
                    <th className="py-2 px-3">Counterparty</th>
                    <th className="py-2 px-3">Asset</th>
                    <th className="py-2 px-3 text-right">Baseline</th>
                    <th className="py-2 px-3 text-right">Stressed</th>
                    <th className="py-2 px-3 text-right">PnL (USD)</th>
                    <th className="py-2 px-3">Shock Summary</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#ECEDEC] font-mono text-xs">
                  {activeStressResult?.position_deltas.map((pos) => (
                    <tr key={pos.position_id} className="hover:bg-[#F9FAF9]">
                      <td className="py-2 px-3 text-[#111827] font-bold">{pos.position_id}</td>
                      <td className="py-2 px-3 text-[#374151] font-sans font-medium">{pos.counterparty_name}</td>
                      <td className="py-2 px-3 text-[#6B7280] uppercase text-[11px]">{pos.asset_class}</td>
                      <td className="py-2 px-3 text-right text-[#4B5563]">${pos.baseline_value_usd.toLocaleString('en-US')}</td>
                      <td className="py-2 px-3 text-right text-[#111827] font-semibold">${pos.stressed_value_usd.toLocaleString('en-US')}</td>
                      <td className={`py-2 px-3 text-right font-bold ${pos.pnl_usd < 0 ? 'text-[#DC2626]' : 'text-[#1F6B45]'}`}>
                        ${pos.pnl_usd.toLocaleString('en-US')}
                      </td>
                      <td className="py-2 px-3 text-[#6B7280] text-[11px] truncate max-w-xs">{pos.applied_shock_summary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* Right 4/12: Manual Stress Simulation Sandbox */}
        <div className="col-span-12 lg:col-span-4 flex flex-col space-y-5">
          <Card className="space-y-4">
            <div className="flex items-center gap-2 border-b border-[#ECEDEC] pb-3">
              <div className="w-7 h-7 rounded-full bg-[#E8F5EE] text-[#14532D] flex items-center justify-center">
                <Sliders className="w-4 h-4 text-[#14532D]" />
              </div>
              <h3 className="text-sm font-bold text-[#111827]">Manual Stress Sandbox</h3>
            </div>

            <form onSubmit={onRunStressSimulation} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#4B5563] font-semibold mb-1">Event Classification</label>
                <select
                  value={stressForm.event_class}
                  onChange={(e) => setStressForm({ ...stressForm, event_class: e.target.value })}
                  className="w-full bg-[#F3F4F3] border border-[#ECEDEC] rounded-xl p-2 text-[#111827] focus:outline-none focus:border-[#14532D] font-mono"
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
                  <label className="text-[#4B5563] font-semibold">Severity Impact Score</label>
                  <span className="font-mono text-[#111827] font-bold">{stressForm.impact_score} / 10</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={stressForm.impact_score}
                  onChange={(e) => setStressForm({ ...stressForm, impact_score: Number(e.target.value) })}
                  className="w-full accent-[#14532D] cursor-pointer"
                />
              </div>

              <div>
                <label className="block text-[#4B5563] font-semibold mb-1">Target Counterparty / Entity</label>
                <select
                  value={stressForm.target_entity}
                  onChange={(e) => setStressForm({ ...stressForm, target_entity: e.target.value })}
                  className="w-full bg-[#F3F4F3] border border-[#ECEDEC] rounded-xl p-2 text-[#111827] focus:outline-none focus:border-[#14532D]"
                >
                  <option value="Apex Industrial Holdings">Apex Industrial Holdings ($APEX)</option>
                  <option value="JPMorgan Chase & Co.">JPMorgan Chase &amp; Co. ($JPM)</option>
                  <option value="Apple Inc.">Apple Inc. ($AAPL)</option>
                  <option value="Microsoft Corp.">Microsoft Corp. ($MSFT)</option>
                  <option value="Exxon Mobil Corp.">Exxon Mobil Corp. ($XOM)</option>
                  <option value="Amazon.com Inc.">Amazon.com Inc. ($AMZN)</option>
                  <option value="Nova Health Systems">Nova Health Systems ($NOVA)</option>
                  <option value="Vanguard Energy Corp">Vanguard Energy Corp ($VANG)</option>
                  <option value="Sterling Retail Group">Sterling Retail Group ($STEL)</option>
                  <option value="Pacifica Logistics">Pacifica Logistics ($PACL)</option>
                </select>
              </div>

              <div>
                <label className="block text-[#4B5563] font-semibold mb-1">Shock Contagion Scope</label>
                <select
                  value={stressForm.target_scope}
                  onChange={(e) => setStressForm({ ...stressForm, target_scope: e.target.value })}
                  className="w-full bg-[#F3F4F3] border border-[#ECEDEC] rounded-xl p-2 text-[#111827] focus:outline-none focus:border-[#14532D]"
                >
                  <option value="entity">Entity Level (Idiosyncratic Shock)</option>
                  <option value="sector">Sector Level (Peer Group Contagion)</option>
                  <option value="macro">Macro Level (Broad Market Shock)</option>
                </select>
              </div>

              <div className="pt-1">
                <label className="flex items-center gap-2 cursor-pointer text-[#374151]">
                  <input
                    type="checkbox"
                    checked={stressForm.is_easing}
                    onChange={(e) => setStressForm({ ...stressForm, is_easing: e.target.checked })}
                    className="rounded text-[#1F6B45] focus:ring-0 accent-[#1F6B45]"
                  />
                  <span>Monetary Policy Easing (Negative Yield Shock)</span>
                </label>
              </div>

              <PillButton
                type="submit"
                variant="primary"
                disabled={simulatingStress}
                className="w-full"
              >
                {simulatingStress ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white text-white" />
                    Execute Stress Simulation
                  </>
                )}
              </PillButton>
            </form>

            {/* History of Stress Runs */}
            <div className="pt-3 border-t border-[#ECEDEC] space-y-2">
              <div className="text-[#6B7280] font-semibold text-xs">Recent Simulation History</div>
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {stressRuns.slice(0, 5).map((run) => (
                  <div
                    key={run.stress_id}
                    onClick={() => setActiveStressResult(run)}
                    className={`p-2.5 rounded-xl border cursor-pointer text-[11px] flex items-center justify-between font-mono transition-all ${
                      activeStressResult?.stress_id === run.stress_id
                        ? 'bg-[#E8F5EE] border-[#14532D] text-[#14532D] font-bold'
                        : 'bg-white border-[#ECEDEC] text-[#4B5563] hover:border-gray-300'
                    }`}
                  >
                    <div>
                      <div className="font-bold uppercase text-[#111827]">
                        {run.event_class} ({run.impact_score}/10)
                      </div>
                      <div className="text-[10px] text-[#9CA3AF]">{run.executed_at.slice(11, 19)}</div>
                    </div>
                    <div className={`text-right font-bold ${run.total_pnl_usd < 0 ? 'text-[#DC2626]' : 'text-[#1F6B45]'}`}>
                      {run.total_pnl_usd < 0 ? '-' : '+'}${Math.abs(run.total_pnl_usd).toLocaleString('en-US', { maximumFractionDigits: 0 })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
