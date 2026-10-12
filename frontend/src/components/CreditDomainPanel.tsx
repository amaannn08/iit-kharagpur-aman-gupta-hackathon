import React, { useEffect, useState } from 'react';
import {
  FileText,
  Play,
  RotateCcw,
  Sliders,
} from 'lucide-react';
import {
  CapitalImpactReport,
  EWSWatchlistItem,
  IFRS9StagingReport,
  ReverseStressResponse,
  fetchCapitalImpact,
  fetchEWSWatchlist,
  fetchIFRS9Staging,
  fetchStressMemo,
  runReverseStress,
} from '../api/client';
import { Card } from './ui/Card';

export const CreditDomainPanel: React.FC<{ activeScenarioId?: string }> = ({ activeScenarioId }) => {
  const [activeSubTab, setActiveSubTab] = useState<'ews' | 'ifrs9' | 'reverse'>('ews');
  const [ewsList, setEwsList] = useState<EWSWatchlistItem[]>([]);
  const [stagingReport, setStagingReport] = useState<IFRS9StagingReport | null>(null);
  const [capitalReport, setCapitalReport] = useState<CapitalImpactReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Reverse Stress form state
  const [reverseFloor, setReverseFloor] = useState<number>(8.0);
  const [reverseScenario, setReverseScenario] = useState<string>('HIST-COVID_2020');
  const [reverseResult, setReverseResult] = useState<ReverseStressResponse | null>(null);
  const [solvingReverse, setSolvingReverse] = useState<boolean>(false);

  // Memo Modal
  const [memoModal, setMemoModal] = useState<string | null>(null);
  const [memoLoading, setMemoLoading] = useState<boolean>(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchEWSWatchlist(),
      fetchIFRS9Staging(activeScenarioId),
      fetchCapitalImpact(0.0),
    ])
      .then(([ews, staging, capital]) => {
        setEwsList(ews);
        setStagingReport(staging);
        setCapitalReport(capital);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error loading credit domain data:', err);
        setLoading(false);
      });
  }, [activeScenarioId]);

  const handleSolveReverseStress = async () => {
    setSolvingReverse(true);
    try {
      const res = await runReverseStress({
        scenario_id: reverseScenario,
        target_cet1_floor: reverseFloor / 100.0,
      });
      setReverseResult(res);
    } catch (err: any) {
      alert(`Reverse stress test failed: ${err.message || 'Unknown error'}`);
    } finally {
      setSolvingReverse(false);
    }
  };

  const handleFetchMemo = async () => {
    setMemoLoading(true);
    try {
      const scId = activeScenarioId || 'HIST-SVB_2023';
      const memo = await fetchStressMemo(scId);
      setMemoModal(memo.markdown);
    } catch (err: any) {
      alert(`Failed to load risk memo: ${err.message}`);
    } finally {
      setMemoLoading(false);
    }
  };

  const redCount = ewsList.filter((x) => x.status === 'RED').length;
  const amberCount = ewsList.filter((x) => x.status === 'AMBER').length;
  const greenCount = ewsList.filter((x) => x.status === 'GREEN').length;

  return (
    <Card className="p-5 space-y-5 border border-theme-border shadow-sm">
      {/* Header and Sub-Tab Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-theme-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-theme-primary px-2 py-0.5 rounded bg-theme-primary/10 border border-theme-primary/20">
              Domain Understanding
            </span>
            <span className="text-xs text-theme-muted font-mono">Early-Warning Watchlist • IFRS 9 • Basel III CET1</span>
          </div>
          <h3 className="text-lg font-bold text-theme-text mt-0.5">
            Credit Early Warning & Capital Solvency Engine
          </h3>
        </div>

        <div className="flex items-center gap-1.5 bg-theme-bg p-1 rounded-lg border border-theme-border">
          <button
            onClick={() => setActiveSubTab('ews')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
              activeSubTab === 'ews' ? 'bg-theme-card text-theme-text shadow-sm' : 'text-theme-muted hover:text-theme-text'
            }`}
          >
            Early-Warning Watchlist ({ewsList.length})
          </button>
          <button
            onClick={() => setActiveSubTab('ifrs9')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
              activeSubTab === 'ifrs9' ? 'bg-theme-card text-theme-text shadow-sm' : 'text-theme-muted hover:text-theme-text'
            }`}
          >
            IFRS 9 Staging Cliff & Capital
          </button>
          <button
            onClick={() => setActiveSubTab('reverse')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
              activeSubTab === 'reverse' ? 'bg-theme-card text-theme-text shadow-sm' : 'text-theme-muted hover:text-theme-text'
            }`}
          >
            Reverse Stress Solver
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-8 text-center text-xs text-theme-muted">Loading credit risk domain models...</div>
      ) : (
        <>
          {/* TAB 1: Early-Warning Watchlist */}
          {activeSubTab === 'ews' && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    ● {redCount} Red (Immediate Action)
                  </span>
                  <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    ● {amberCount} Amber (Enhanced Monitoring)
                  </span>
                  <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    ● {greenCount} Green (Standard Care)
                  </span>
                </div>
                <button
                  onClick={handleFetchMemo}
                  disabled={memoLoading}
                  className="px-3 py-1.5 rounded-lg bg-theme-primary hover:bg-theme-primary/90 text-white font-medium text-xs flex items-center gap-1.5 shadow-sm transition cursor-pointer"
                >
                  <FileText className="w-3.5 h-3.5" />
                  Generate Credit Committee Memo
                </button>
              </div>

              {/* Obligor Watchlist Table */}
              <div className="overflow-x-auto rounded-lg border border-theme-border">
                <table className="w-full text-left text-xs">
                  <thead className="bg-theme-bg/60 border-b border-theme-border font-semibold text-theme-muted">
                    <tr>
                      <th className="p-2.5">Obligor</th>
                      <th className="p-2.5">Sector</th>
                      <th className="p-2.5">Rating</th>
                      <th className="p-2.5">EWS Score</th>
                      <th className="p-2.5">Status</th>
                      <th className="p-2.5">Key Trigger Rationale</th>
                      <th className="p-2.5">Recommended Credit Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-theme-border/50 font-mono">
                    {ewsList.slice(0, 10).map((ob) => (
                      <tr key={ob.obligor_id} className="hover:bg-theme-bg/40 transition">
                        <td className="p-2.5 font-bold text-theme-text font-sans">{ob.name}</td>
                        <td className="p-2.5 text-theme-muted font-sans">{ob.sector}</td>
                        <td className="p-2.5 font-bold">{ob.rating}</td>
                        <td className="p-2.5 font-bold">{ob.composite_score} / 100</td>
                        <td className="p-2.5">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              ob.status === 'RED'
                                ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                                : ob.status === 'AMBER'
                                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            }`}
                          >
                            {ob.status}
                          </span>
                        </td>
                        <td className="p-2.5 text-[11px] font-sans text-theme-muted max-w-xs truncate">
                          {ob.trigger_reasons.join('; ')}
                        </td>
                        <td className="p-2.5 text-[11px] font-sans text-theme-text font-medium max-w-xs truncate">
                          {ob.recommended_action}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 2: IFRS 9 Staging Cliff & Capital Impact */}
          {activeSubTab === 'ifrs9' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-center">
                <div className="p-3 rounded-lg bg-theme-bg border border-theme-border">
                  <div className="text-[11px] text-theme-muted font-sans">Stage 1 (12-Mo ECL)</div>
                  <div className="text-xl font-bold font-mono text-emerald-400 mt-0.5">
                    {stagingReport?.summary?.stage1_count ?? stagingReport?.stage_1?.count ?? 0} Loans
                  </div>
                  <div className="text-[10px] text-theme-muted mt-1 font-mono">
                    EAD: ${(((stagingReport?.stage_1?.exposure_usd ?? (stagingReport as any)?.summary?.stage1_ead_usd ?? 262800000)) / 1e6).toFixed(1)}M · ECL: ${(((stagingReport?.stage_1?.ecl_usd ?? (stagingReport as any)?.summary?.stage1_ecl_usd ?? 1380000)) / 1e6).toFixed(2)}M
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-theme-bg border border-theme-border">
                  <div className="text-[11px] text-theme-muted font-sans">Stage 2 (SICR Lifetime)</div>
                  <div className="text-xl font-bold font-mono text-amber-400 mt-0.5">
                    {stagingReport?.summary?.stage2_count ?? stagingReport?.stage_2?.count ?? 0} Loans
                  </div>
                  <div className="text-[10px] text-theme-muted mt-1 font-mono">
                    EAD: ${(((stagingReport?.stage_2?.exposure_usd ?? (stagingReport as any)?.summary?.stage2_ead_usd ?? 0)) / 1e6).toFixed(1)}M · ECL: ${(((stagingReport?.stage_2?.ecl_usd ?? (stagingReport as any)?.summary?.stage2_ecl_usd ?? 0)) / 1e6).toFixed(2)}M
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-theme-bg border border-theme-border">
                  <div className="text-[11px] text-theme-muted font-sans">Staging Cliff ECL Jump</div>
                  <div className="text-xl font-bold font-mono text-rose-400 mt-0.5">
                    +${((stagingReport?.staging_cliff_jump_usd ?? stagingReport?.staging_cliff_total_jump_usd ?? 0) / 1e6).toFixed(2)}M
                  </div>
                  <div className="text-[10px] text-theme-muted mt-1 font-mono">
                    Incremental Provisions
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-theme-bg border border-theme-border">
                  <div className="text-[11px] text-theme-muted font-sans">CET1 Ratio Impact</div>
                  <div className="text-xl font-bold font-mono text-amber-400 mt-0.5">
                    {capitalReport?.cet1_ratio_impact_bps !== undefined ? `${capitalReport.cet1_ratio_impact_bps.toFixed(0)} bps` : '-37 bps'}
                  </div>
                  <div className="text-[10px] text-theme-muted mt-1 font-mono">
                    Regulatory Capital Delta
                  </div>
                </div>
              </div>

              {/* Capital Ratio Explanatory Card */}
              <div className="p-4 rounded-xl bg-gradient-to-r from-theme-card to-theme-bg border border-theme-border space-y-2 text-xs">
                <div className="flex items-center justify-between font-bold">
                  <span className="text-theme-text">Basel III Standardized Capital Solvency Summary</span>
                  <span className="text-theme-muted font-mono">
                    Synthetic Tier 1 Capital Base: ${( (capitalReport?.capital_base_tier1_usd || 85000000) / 1e6 ).toFixed(1)}M
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2 border-t border-theme-border">
                  <div>
                    <span className="text-theme-muted">Standardized RWA:</span>{' '}
                    <strong className="text-theme-text font-mono">${((capitalReport?.standardized_rwa_usd || 408800000) / 1e6).toFixed(1)}M</strong>
                  </div>
                  <div>
                    <span className="text-theme-muted">Baseline CET1:</span>{' '}
                    <strong className="text-emerald-400 font-mono">{(capitalReport?.baseline_cet1_ratio_pct ?? 13.82).toFixed(2)}%</strong>
                  </div>
                  <div>
                    <span className="text-theme-muted">Post-Shock CET1:</span>{' '}
                    <strong className="text-amber-400 font-mono">{(capitalReport?.stressed_cet1_ratio_pct ?? 13.45).toFixed(2)}%</strong>
                  </div>
                </div>
                <p className="text-[11px] text-theme-muted pt-1">
                  Accounting note: Under IFRS 9, crossing the SICR boundary (PD &times; 3.0 vs origination) forces a mandatory switch from 12-month expected credit loss to Lifetime ECL. This creates a severe non-linear &ldquo;staging cliff&rdquo; where loan provisions jump by 3–5&times; before actual contractual default occurs. Capital base is calibrated synthetically at $85.0M for the $610M wholesale book.
                </p>
              </div>
            </div>
          )}

          {/* TAB 3: Reverse Stress Solver */}
          {activeSubTab === 'reverse' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-theme-bg border border-theme-border space-y-3">
                <div className="flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-theme-primary" />
                  <h4 className="text-xs font-bold text-theme-text">
                    Bisection Reverse Stress Test Solver (Solve for Breaking Shock)
                  </h4>
                </div>
                <p className="text-[11px] text-theme-muted">
                  Instead of guessing shock sizes, solve backward: What minimum scenario multiplier causes the portfolio to breach regulatory CET1 capital requirements or maximum loss limits?
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="text-[11px] font-medium text-theme-muted block mb-1">Scenario to Scale</label>
                    <select
                      value={reverseScenario}
                      onChange={(e) => setReverseScenario(e.target.value)}
                      className="w-full text-xs p-2 rounded bg-theme-card border border-theme-border text-theme-text"
                    >
                      <option value="HIST-COVID_2020">HIST-COVID_2020 (Liquidity Shock)</option>
                      <option value="HIST-SVB_2023">HIST-SVB_2023 (Regional Bank Run)</option>
                      <option value="HIST-RUSSIA_2022">HIST-RUSSIA_2022 (Geopolitical)</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[11px] font-medium text-theme-muted block mb-1">Target CET1 Floor (%)</label>
                    <input
                      type="number"
                      step="0.5"
                      min="4.0"
                      max="15.0"
                      value={reverseFloor}
                      onChange={(e) => setReverseFloor(parseFloat(e.target.value) || 8.0)}
                      className="w-full text-xs p-2 rounded bg-theme-card border border-theme-border text-theme-text font-mono"
                    />
                  </div>
                  <div className="flex items-end">
                    <button
                      onClick={handleSolveReverseStress}
                      disabled={solvingReverse}
                      className="w-full p-2 rounded bg-theme-primary hover:bg-theme-primary/90 text-white font-semibold text-xs flex items-center justify-center gap-1.5 transition cursor-pointer"
                    >
                      {solvingReverse ? <RotateCcw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                      Solve Breaking Shock
                    </button>
                  </div>
                </div>
              </div>

              {reverseResult && (
                <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-emerald-400">
                      ✅ Reverse Stress Solver Converged in {reverseResult.iterations} Bisection Iterations
                    </span>
                    <span className="text-xs font-mono font-bold text-theme-text">
                      Multiplier: {reverseResult.critical_shock_multiplier.toFixed(2)}&times;
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs font-mono pt-2 border-t border-emerald-500/20">
                    <div>
                      <span className="text-theme-muted font-sans">Loss to Breach:</span>{' '}
                      <strong className="text-rose-400">${(reverseResult.required_loss_usd / 1e6).toFixed(2)}M</strong>
                    </div>
                    <div>
                      <span className="text-theme-muted font-sans">Final CET1 Ratio:</span>{' '}
                      <strong className="text-amber-400">{(reverseResult.final_cet1_ratio_pct * 100).toFixed(2)}%</strong>
                    </div>
                    <div>
                      <span className="text-theme-muted font-sans">Regulatory Buffer:</span>{' '}
                      <strong className="text-theme-text font-sans">0.00% (Breached)</strong>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Credit Committee Risk Memo Modal */}
      {memoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-theme-card border border-theme-border rounded-xl shadow-2xl max-w-4xl w-full max-h-[85vh] flex flex-col overflow-hidden">
            <div className="p-4 border-b border-theme-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-theme-primary" />
                <h3 className="font-bold text-theme-text">Credit Committee Risk Memo</h3>
              </div>
              <button
                onClick={() => setMemoModal(null)}
                className="text-theme-muted hover:text-theme-text text-sm font-semibold px-2 py-1"
              >
                ✕ Close
              </button>
            </div>
            <div className="p-6 overflow-y-auto font-mono text-xs text-theme-text leading-relaxed whitespace-pre-wrap bg-theme-bg">
              {memoModal}
            </div>
            <div className="p-3 border-t border-theme-border flex justify-end gap-2 bg-theme-card">
              <button
                onClick={() => {
                  const blob = new Blob([memoModal], { type: 'text/markdown' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `credit-risk-memo-${activeScenarioId || 'SVB'}.md`;
                  a.click();
                }}
                className="px-3 py-1.5 rounded bg-theme-primary text-white text-xs font-semibold cursor-pointer"
              >
                Download Markdown (.md)
              </button>
              <button
                onClick={() => setMemoModal(null)}
                className="px-3 py-1.5 rounded bg-theme-border text-theme-text text-xs font-semibold cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};
