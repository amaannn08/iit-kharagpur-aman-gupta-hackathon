import React, { useEffect, useState } from 'react';
import {
  Clock,
  FileText,
  Play,
  RotateCcw,
  Shield,
  TrendingDown,
  Zap,
} from 'lucide-react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  CrisisDetail,
  CrisisSummary,
  fetchCrises,
  fetchCrisisDetail,
  fetchStressMemo,
  replayCrisis,
} from '../api/client';

export const TimeMachineTab: React.FC = () => {
  const [crises, setCrises] = useState<CrisisSummary[]>([]);
  const [selectedCrisisId, setSelectedCrisisId] = useState<string>('svb');
  const [crisisDetail, setCrisisDetail] = useState<CrisisDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [replaying, setReplaying] = useState<boolean>(false);
  const [replayNotice, setReplayNotice] = useState<string | null>(null);
  const [memoModal, setMemoModal] = useState<string | null>(null);
  const [memoLoading, setMemoLoading] = useState<boolean>(false);

  useEffect(() => {
    fetchCrises()
      .then((data) => {
        setCrises(data);
        if (data.length > 0 && !data.find((c) => c.crisis_id === selectedCrisisId)) {
          setSelectedCrisisId(data[0].crisis_id);
        }
      })
      .catch((err) => console.error('Failed to load crises list:', err));
  }, []);

  useEffect(() => {
    if (!selectedCrisisId) return;
    setLoading(true);
    setReplayNotice(null);
    fetchCrisisDetail(selectedCrisisId)
      .then((detail) => {
        setCrisisDetail(detail);
        setLoading(false);
      })
      .catch((err) => {
        console.error(`Failed to load crisis detail for ${selectedCrisisId}:`, err);
        setLoading(false);
      });
  }, [selectedCrisisId]);

  const handleReplayClick = async () => {
    if (!selectedCrisisId) return;
    setReplaying(true);
    setReplayNotice(null);
    try {
      const res = await replayCrisis(selectedCrisisId);
      setReplayNotice(`Successfully loaded ${res.records_queued} records into Sentinel engine!`);
    } catch (err: any) {
      setReplayNotice(`Replay load failed: ${err.message || 'Unknown error'}`);
    } finally {
      setReplaying(false);
    }
  };

  const handleViewMemo = async () => {
    setMemoLoading(true);
    try {
      const scenarioMap: Record<string, string> = {
        svb: 'HIST-SVB_2023',
        crowdstrike: 'HIST-COVID_2020',
        ukraine: 'HIST-RUSSIA_2022',
      };
      const scId = scenarioMap[selectedCrisisId] || 'HIST-SVB_2023';
      const memo = await fetchStressMemo(scId);
      setMemoModal(memo.markdown);
    } catch (err: any) {
      console.error('Failed to fetch risk memo:', err);
      alert(`Could not load memo: ${err.message}`);
    } finally {
      setMemoLoading(false);
    }
  };

  const chartData = (crisisDetail?.timeline_series || []).map((pt) => {
    const timeLabel = pt.timestamp.includes('T')
      ? pt.timestamp.split('T')[1].slice(0, 5) + ' ' + pt.timestamp.split('T')[0].slice(5)
      : pt.timestamp;
    return {
      timestamp: pt.timestamp,
      displayTime: timeLabel,
      volume: pt.article_volume,
      intensity: pt.story_intensity,
      priceReturn: Math.round(pt.benchmark_return * 1000) / 10, // e.g. -15.4%
      headlines: pt.sample_headlines,
    };
  });

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Banner & Scenario Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-theme-border pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-theme-primary/10 text-theme-primary border border-theme-primary/20">
              WOW MOMENT: LEAD-TIME BENCHMARK
            </span>
            <span className="text-xs text-theme-muted font-mono">2–4h Historical Snapshot Resolution</span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-theme-text mt-1">
            Crisis Time Machine
          </h2>
          <p className="text-sm text-theme-muted mt-0.5">
            Replaying real historical crises with frozen dev thresholds to measure lead time before market panic.
          </p>
        </div>

        {/* Crisis Scenario Selector Tabs */}
        <div className="flex flex-wrap items-center gap-2 bg-theme-card p-1.5 rounded-lg border border-theme-border shadow-sm">
          {crises.map((c) => (
            <button
              key={c.crisis_id}
              onClick={() => setSelectedCrisisId(c.crisis_id)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5 ${
                selectedCrisisId === c.crisis_id
                  ? 'bg-theme-primary text-white shadow'
                  : 'text-theme-muted hover:text-theme-text hover:bg-theme-bg'
              }`}
            >
              {c.crisis_id === 'svb' && '🏦 SVB Collapse'}
              {c.crisis_id === 'crowdstrike' && '🛡️ CrowdStrike Outage'}
              {c.crisis_id === 'ukraine' && '🌍 Russia-Ukraine'}
              <span className="text-[10px] opacity-80 uppercase px-1 py-0.2 rounded bg-black/20">
                {c.event_class}
              </span>
            </button>
          ))}
        </div>
      </div>

      {loading || !crisisDetail ? (
        <div className="p-12 text-center text-theme-muted">
          <Clock className="w-8 h-8 animate-spin mx-auto mb-2 text-theme-primary" />
          Loading crisis timeline and price trajectories...
        </div>
      ) : (
        <>
          {/* Hero Lead Time Callout Banner */}
          <div className={`relative overflow-hidden rounded-xl border p-6 shadow-sm ${
            crisisDetail.lead_time_hours && crisisDetail.lead_time_hours > 0
              ? 'border-emerald-500/30 bg-gradient-to-r from-emerald-950/20 via-theme-card to-theme-card'
              : crisisDetail.lead_time_hours && crisisDetail.lead_time_hours < 0
              ? 'border-amber-500/30 bg-gradient-to-r from-amber-950/20 via-theme-card to-theme-card'
              : 'border-zinc-500/30 bg-gradient-to-r from-zinc-900/20 via-theme-card to-theme-card'
          }`}>
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                    crisisDetail.lead_time_hours && crisisDetail.lead_time_hours > 0
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : crisisDetail.lead_time_hours && crisisDetail.lead_time_hours < 0
                      ? 'bg-amber-500/20 text-amber-400'
                      : 'bg-zinc-500/20 text-zinc-400'
                  }`}>
                    <Zap className="w-4 h-4 fill-current" />
                  </div>
                  <span className={`text-xs font-bold uppercase tracking-wider ${
                    crisisDetail.lead_time_hours && crisisDetail.lead_time_hours > 0
                      ? 'text-emerald-400'
                      : crisisDetail.lead_time_hours && crisisDetail.lead_time_hours < 0
                      ? 'text-amber-400'
                      : 'text-zinc-400'
                  }`}>
                    {crisisDetail.lead_time_hours && crisisDetail.lead_time_hours > 0
                      ? 'Advance Early Warning Achieved'
                      : crisisDetail.lead_time_hours && crisisDetail.lead_time_hours < 0
                      ? 'Post-Event Trigger (Fallout Response)'
                      : 'No Trigger Fired Under Frozen Threshold'}
                  </span>
                </div>
                <h3 className="text-3xl font-extrabold text-theme-text tracking-tight">
                  {crisisDetail.lead_time_display}
                </h3>
                <p className="text-sm text-theme-muted max-w-3xl leading-relaxed">
                  {crisisDetail.triggered
                    ? `Sentinel evaluated stories on ${crisisDetail.primary_entity} under frozen dev thresholds (intensity >= 7.5). When triggered, Module B evaluated capital impact while naive keyword alerts produced false alarms.`
                    : `Under frozen dev thresholds (intensity >= 7.5 calibrated on Polygon dev split), story intensity for ${crisisDetail.primary_entity} did not cross the trigger threshold. The system conservatively abstained rather than firing a false alarm.`}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center gap-3 shrink-0">
                <button
                  onClick={handleReplayClick}
                  disabled={replaying}
                  className="w-full sm:w-auto px-4 py-2.5 rounded-lg bg-theme-primary hover:bg-theme-primary/90 text-white font-medium text-xs flex items-center justify-center gap-2 shadow-sm transition"
                >
                  {replaying ? <RotateCcw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                  Replay in Engine ({crisisDetail.total_articles} records)
                </button>
                <button
                  onClick={handleViewMemo}
                  disabled={memoLoading}
                  className="w-full sm:w-auto px-4 py-2.5 rounded-lg bg-theme-bg hover:bg-theme-card border border-theme-border text-theme-text font-medium text-xs flex items-center justify-center gap-2 shadow-sm transition"
                >
                  <FileText className="w-4 h-4 text-theme-primary" />
                  Committee Risk Memo
                </button>
              </div>
            </div>

            {replayNotice && (
              <div className="mt-4 p-3 rounded-lg bg-theme-bg border border-theme-border text-xs text-theme-text flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                {replayNotice}
              </div>
            )}
          </div>

          {/* Key Milestones Stepper */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {crisisDetail.milestones.map((m, idx) => (
              <div
                key={m.id}
                className="bg-theme-card border border-theme-border rounded-xl p-4 flex flex-col justify-between space-y-3 relative overflow-hidden"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-theme-muted">
                    Milestone {idx + 1}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                      m.id === 'trigger'
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        : m.id === 'first_signal'
                        ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                        : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    }`}
                  >
                    {m.label}
                  </span>
                </div>
                <div>
                  <div className="text-xs font-bold text-theme-text">{m.source}</div>
                  <div className="text-[11px] text-theme-muted mt-1 leading-snug">{m.description}</div>
                </div>
                <div className="text-[10px] font-mono text-theme-muted pt-2 border-t border-theme-border/50">
                  {m.timestamp.replace('T', ' ').replace('Z', ' UTC')}
                </div>
              </div>
            ))}
          </div>

          {/* Dual Axis Chart Card */}
          <div className="bg-theme-card border border-theme-border rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h4 className="text-sm font-bold text-theme-text">
                  Dual-Axis Timeline: Story Velocity, Intensity & Market Reaction
                </h4>
                <p className="text-xs text-theme-muted">
                  Bars: News & Filing Volume · Purple Line: Story Intensity (Threshold = 7.5) · Cyan Line: Benchmark Return ({crisisDetail.benchmark_ticker})
                </p>
              </div>
              <div className="flex items-center gap-4 text-xs font-mono">
                <span className="flex items-center gap-1.5 text-indigo-400">
                  <span className="w-3 h-3 rounded bg-indigo-500/40 inline-block" />
                  Article Volume
                </span>
                <span className="flex items-center gap-1.5 text-amber-400">
                  <span className="w-3 h-0.5 bg-amber-400 inline-block" />
                  Story Intensity
                </span>
                <span className="flex items-center gap-1.5 text-rose-400">
                  <span className="w-3 h-0.5 bg-rose-400 inline-block" />
                  {crisisDetail.benchmark_ticker} Return %
                </span>
              </div>
            </div>

            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#33333333" />
                  <XAxis dataKey="displayTime" tick={{ fontSize: 10, fill: '#888' }} interval={Math.floor(chartData.length / 8)} />
                  {/* Left Axis: Volume & Intensity */}
                  <YAxis yAxisId="left" domain={[0, 'auto']} tick={{ fontSize: 10, fill: '#888' }} />
                  {/* Right Axis: Price Return % */}
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    unit="%"
                    domain={[-35, 10]}
                    tick={{ fontSize: 10, fill: '#888' }}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload || !payload.length) return null;
                      const d = payload[0].payload;
                      return (
                        <div className="bg-theme-card border border-theme-border p-3 rounded-lg shadow-lg text-xs space-y-1.5 max-w-sm">
                          <div className="font-mono text-theme-muted">{d.timestamp}</div>
                          <div className="font-bold text-theme-text flex justify-between">
                            <span>Articles Arrived:</span>
                            <span>{d.volume}</span>
                          </div>
                          <div className="font-bold text-amber-400 flex justify-between">
                            <span>Story Intensity:</span>
                            <span>{d.intensity} / 10</span>
                          </div>
                          <div className="font-bold text-rose-400 flex justify-between">
                            <span>{crisisDetail.benchmark_ticker} Move:</span>
                            <span>{d.priceReturn}%</span>
                          </div>
                          {d.headlines && d.headlines.length > 0 && (
                            <div className="pt-1.5 border-t border-theme-border text-[11px] text-theme-muted italic">
                              "{d.headlines[0]}"
                            </div>
                          )}
                        </div>
                      );
                    }}
                  />
                  <ReferenceLine yAxisId="left" y={7.5} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: 'Trigger Floor (7.5)', fill: '#f59e0b', fontSize: 10 }} />
                  <Bar yAxisId="left" dataKey="volume" fill="#6366f1" opacity={0.35} radius={[3, 3, 0, 0]} />
                  <Line yAxisId="left" type="monotone" dataKey="intensity" stroke="#f59e0b" strokeWidth={2.5} dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="priceReturn" stroke="#f43f5e" strokeWidth={2} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Contrast Card: Sentinel vs Naive Keyword Alerts & Portfolio Impact */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: The Killer Contrast Slide */}
            <div className="bg-theme-card border border-theme-border rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-theme-border pb-3">
                <h4 className="text-sm font-bold text-theme-text flex items-center gap-2">
                  <Shield className="w-4 h-4 text-theme-primary" />
                  Jury Contrast: Sentinel vs. Naive Keyword Alert
                </h4>
                <span className="text-[10px] font-mono text-theme-muted">Out-of-Sample Proof</span>
              </div>

              <div className="space-y-3">
                {/* Naive Rule */}
                <div className="p-3 rounded-lg bg-rose-950/20 border border-rose-500/30 space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-bold text-rose-400">
                    <span>❌ Naive Keyword Alert</span>
                    <span>{crisisDetail.naive_alert_performance.naive_triggers} Triggers ({crisisDetail.naive_alert_performance.naive_false_positives} False Positives)</span>
                  </div>
                  <div className="text-[11px] text-theme-muted">
                    <strong>Rule:</strong> {crisisDetail.naive_alert_performance.naive_rule}
                  </div>
                  <div className="text-[11px] text-rose-300">
                    {crisisDetail.naive_alert_performance.verdict}
                  </div>
                </div>

                {/* Sentinel Story Engine */}
                <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-500/30 space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-bold text-emerald-400">
                    <span>✅ Sentinel Story Clustering Engine</span>
                    <span>{crisisDetail.sentinel_performance.sentinel_triggers} Trigger ({crisisDetail.sentinel_performance.sentinel_false_positives} False Positives)</span>
                  </div>
                  <div className="text-[11px] text-theme-muted">
                    <strong>Rule:</strong> {crisisDetail.sentinel_performance.sentinel_rule}
                  </div>
                  <div className="text-[11px] text-emerald-300">
                    {crisisDetail.sentinel_performance.verdict}
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Portfolio & Capital Damage Prevention */}
            <div className="bg-theme-card border border-theme-border rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-theme-border pb-3">
                <h4 className="text-sm font-bold text-theme-text flex items-center gap-2">
                  <TrendingDown className="w-4 h-4 text-theme-primary" />
                  Projected Book & Capital Impact
                </h4>
                <span className="text-[10px] font-mono text-theme-muted">Pre-calculated at Trigger Time</span>
              </div>

              <div className="grid grid-cols-2 gap-3 text-center">
                <div className="p-3 rounded-lg bg-theme-bg border border-theme-border">
                  <div className="text-xs text-theme-muted">Wholesale Loss</div>
                  <div className="text-xl font-bold text-rose-400 mt-1">
                    ${(crisisDetail.portfolio_impact.portfolio_loss_usd / 1_000_000).toFixed(2)}M
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-theme-bg border border-theme-border">
                  <div className="text-xs text-theme-muted">CET1 Capital Delta</div>
                  <div className="text-xl font-bold text-amber-400 mt-1">
                    {crisisDetail.portfolio_impact.cet1_impact_bps.toFixed(1)} bps
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-theme-bg border border-theme-border">
                  <div className="text-xs text-theme-muted">IFRS 9 SICR Migrations</div>
                  <div className="text-xl font-bold text-theme-text mt-1">
                    {crisisDetail.portfolio_impact.loans_migrated_stage2} Loans (Stage 2)
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-theme-bg border border-theme-border">
                  <div className="text-xs text-theme-muted">Staging Cliff ECL Jump</div>
                  <div className="text-xl font-bold text-rose-400 mt-1">
                    +${(crisisDetail.portfolio_impact.staging_cliff_provision_jump_usd / 1_000_000).toFixed(2)}M
                  </div>
                </div>
              </div>

              <p className="text-[11px] text-theme-muted leading-relaxed">
                {crisisDetail.lead_time_hours && crisisDetail.lead_time_hours > 0
                  ? `By firing ${crisisDetail.lead_time_display}, risk managers can immediately enforce borrower exposure freezes, request collateral top-ups, and execute dynamic hedges before secondary liquidity dries up.`
                  : crisisDetail.lead_time_hours && crisisDetail.lead_time_hours < 0
                  ? `Triggered during post-event contagion fallout. Module B recalculates capital impairment and identifies second-order loan migrations.`
                  : `Conservative triggering prevents portfolio turnover and false hedging costs during routine market noise.`}
              </p>
            </div>
          </div>
        </>
      )}

      {/* Credit Committee Memo Modal */}
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
                  a.download = `risk-memo-${selectedCrisisId}.md`;
                  a.click();
                }}
                className="px-3 py-1.5 rounded bg-theme-primary text-white text-xs font-semibold"
              >
                Download Markdown (.md)
              </button>
              <button
                onClick={() => setMemoModal(null)}
                className="px-3 py-1.5 rounded bg-theme-border text-theme-text text-xs font-semibold"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
