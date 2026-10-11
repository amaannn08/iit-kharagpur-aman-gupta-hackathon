import React, { useEffect, useRef, useState } from 'react';
import {
  Clock,
  Pause,
  Play,
  Plus,
  RotateCcw,
  StepForward,
  TrendingDown,
} from 'lucide-react';
import {
  fetchStressRun,
  ReplayStatus,
  RiskSignal,
  SignalStats,
  StressRunResult,
} from '../api/client';
import { SOURCE_PRESETS } from '../hooks/useReplay';
import { TabType } from '../types/navigation';
import { Feed } from './Feed';
import { Inspector } from './Inspector';
import { Card } from './ui/Card';
import { Gauge } from './ui/Gauge';
import { KpiCard } from './ui/KpiCard';
import { Pill } from './ui/Pill';
import { PillBarChart, PillBarChartDataPoint } from './ui/PillBarChart';
import { PillButton } from './ui/PillButton';

export interface DashboardTabProps {
  signals: RiskSignal[];
  signalStats?: SignalStats | null;
  selectedSignal: RiskSignal | null;
  onSelectSignal: (sig: RiskSignal) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  filterEvent: string;
  onFilterEventChange: (ev: string) => void;
  showDuplicates: boolean;
  onShowDuplicatesChange: (show: boolean) => void;
  activeStressResult: StressRunResult | null;
  stressRuns: StressRunResult[];
  replayStatus: ReplayStatus | null;
  selectedScenario: string;
  replayLoading: boolean;
  onLoadScenario: (scId: string) => void;
  onAppendLive: () => void;
  onPlay: () => void;
  onPause: () => void;
  onStep: () => void;
  onReset: () => void;
  onSpeed: (spd: number) => void;
  setActiveTab: (tab: TabType) => void;
}

export const DashboardTab: React.FC<DashboardTabProps> = ({
  signals,
  signalStats,
  selectedSignal,
  onSelectSignal,
  searchQuery,
  onSearchChange,
  filterEvent,
  onFilterEventChange,
  showDuplicates,
  onShowDuplicatesChange,
  activeStressResult,
  stressRuns,
  replayStatus,
  selectedScenario,
  replayLoading,
  onLoadScenario,
  onAppendLive,
  onPlay,
  onPause,
  onStep,
  onReset,
  onSpeed,
  setActiveTab,
}) => {
  const inspectorRef = useRef<HTMLDivElement>(null);

  // Hydrate top 4 recent stress runs with full details if not already populated
  const [hydratedRuns, setHydratedRuns] = useState<StressRunResult[]>([]);

  useEffect(() => {
    const top4 = stressRuns.slice(0, 4);
    if (top4.length === 0) {
      setHydratedRuns([]);
      return;
    }

    // Check if runs already have full details (target_entity or reconciliation_passed)
    const needsFetch = top4.some(
      (r) => r.target_entity === undefined && r.reconciliation_passed === undefined
    );

    if (needsFetch) {
      Promise.all(top4.map((r) => fetchStressRun(r.stress_id).catch(() => r)))
        .then((full) => setHydratedRuns(full))
        .catch(() => setHydratedRuns(top4));
    } else {
      setHydratedRuns(top4);
    }
  }, [stressRuns]);

  // Quantitative signal metrics (Strictly no made-up numbers)
  const totalSignalsCount = Math.max(
    signalStats?.total_signals ?? 0,
    replayStatus?.processed_count ?? 0,
    signals.length
  );
  const actionableCount =
    signalStats?.actionable_count ?? signals.filter((s) => s.eligible_for_action).length;

  const duplicateSignalsCount = signals.filter(
    (s) => s.duplicate_group_id || s.action_block_reasons?.includes('DUPLICATE_TEXT_SUPPRESSED')
  ).length;
  const effectiveDuplicateCount =
    signalStats?.duplicate_count ?? replayStatus?.duplicate_count ?? duplicateSignalsCount;

  const blockedCount =
    signalStats?.blocked_count ??
    Math.max(0, totalSignalsCount - actionableCount - effectiveDuplicateCount);

  // High impact signals: STRICTLY impact.score > 7
  const highImpactSignals = signals
    .filter((s) => s.impact.score > 7)
    .slice(0, 5);

  // Event class distribution for pill bar chart
  const eventTaxonomy = ['CREDIT', 'MACRO', 'GEOPOLITICAL', 'M_AND_A', 'CYBER', 'SUPPLY_CHAIN', 'EARNINGS'];
  const eventChartData: PillBarChartDataPoint[] = eventTaxonomy.map((label) => {
    let eligible = 0;
    let blocked = 0;
    if (signalStats?.by_event && signalStats.by_event[label]) {
      eligible = signalStats.by_event[label].eligible;
      blocked = signalStats.by_event[label].blocked;
    } else {
      const classSignals = signals.filter(
        (s) => s.event?.label?.toUpperCase() === label
      );
      eligible = classSignals.filter((s) => s.eligible_for_action).length;
      blocked = classSignals.length - eligible;
    }
    return {
      name: label === 'GEOPOLITICAL' ? 'GEO' : label === 'SUPPLY_CHAIN' ? 'SUPPLY' : label,
      eligible,
      blocked,
    };
  });

  const handleSelectHighImpact = (sig: RiskSignal) => {
    onSelectSignal(sig);
    if (inspectorRef.current) {
      inspectorRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Replay clock time extraction
  const simulatedTimeFormatted = (() => {
    if (!replayStatus?.current_simulated_at) return '00:00:00';
    try {
      const date = new Date(replayStatus.current_simulated_at);
      return date.toTimeString().slice(0, 8);
    } catch {
      return replayStatus.current_simulated_at.slice(11, 19) || '00:00:00';
    }
  })();

  const currentPreset = SOURCE_PRESETS[selectedScenario];

  return (
    <div className="space-y-6 pb-8">
      {/* 1. Page Header matching Donezo */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-theme-text">
            Risk Dashboard
          </h1>
          <p className="text-xs md:text-sm text-theme-muted mt-0.5">
            Real-time text &rarr; signals &rarr; stress tests, all offline.
          </p>
        </div>
      </div>

      {/* 2. Donezo 4 KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-5">
        {/* Card 1: Signals Emitted (Hero Variant) */}
        <KpiCard
          variant="hero"
          title="Signals Emitted"
          value={totalSignalsCount}
          subtitle={`of ${replayStatus?.total_records ?? '—'} processed`}
          onNavigate={() => setActiveTab('feed')}
        />

        {/* Card 2: Action Eligible */}
        <KpiCard
          variant="default"
          title="Action Eligible"
          value={actionableCount}
          subtitle={
            totalSignalsCount > 0
              ? `${Math.round((actionableCount / totalSignalsCount) * 100)}% of signals`
              : 'of — in run'
          }
          onNavigate={() => setActiveTab('feed')}
        />

        {/* Card 3: Stress Runs Triggered */}
        <KpiCard
          variant="default"
          title="Stress Runs Triggered"
          value={stressRuns.length}
          subtitle={
            activeStressResult?.total_pnl_usd !== undefined
              ? `latest -$${Math.abs(activeStressResult.total_pnl_usd / 1e6).toFixed(1)}M`
              : `from ${stressRuns.length} triggers`
          }
          onNavigate={() => setActiveTab('stress')}
        />

        {/* Card 4: Duplicates Suppressed */}
        <KpiCard
          variant="default"
          title="Duplicates Suppressed"
          value={effectiveDuplicateCount}
          subtitle={`of ${replayStatus?.total_records ?? '—'} processed`}
          onNavigate={() => setActiveTab('feed')}
        />
      </div>

      {/* 3. Donezo Middle Row: Analytics Chart + Replay Control + Latest Signals */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-5">
        {/* Project Analytics: Signals by Event Class (5 cols) */}
        <Card className="lg:col-span-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h2 className="text-sm md:text-base font-bold text-theme-text">
                Signals by Event Class
              </h2>
              <p className="text-xs text-theme-muted">
                Action-eligible vs blocked across taxonomy
              </p>
            </div>
          </div>
          <PillBarChart data={eventChartData} height={200} />
        </Card>

        {/* Reminders: Replay Control Card (4 cols) */}
        <Card className="lg:col-span-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm md:text-base font-bold text-theme-text">
                Replay Control
              </h2>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-theme-primary-tint text-theme-primary-text font-bold">
                {replayStatus?.state?.toUpperCase() || 'IDLE'}
              </span>
            </div>

            {/* Replay Source Selector Dropdown */}
            <div className="p-3 rounded-xl bg-theme-bg border border-theme-border space-y-1.5 my-3">
              <label className="text-[10px] text-theme-muted font-medium uppercase font-mono block">
                Replay Source Preset
              </label>
              <select
                value={selectedScenario}
                onChange={(e) => onLoadScenario(e.target.value)}
                disabled={replayLoading}
                className="w-full bg-theme-card border border-theme-border hover:border-theme-muted rounded-lg px-2.5 py-1.5 text-xs font-bold text-theme-text cursor-pointer focus:outline-none focus:border-theme-primary"
              >
                {Object.entries(SOURCE_PRESETS).map(([id, p]) => (
                  <option key={id} value={id}>
                    {p.label}
                  </option>
                ))}
                {!SOURCE_PRESETS[selectedScenario] && (
                  <option value={selectedScenario}>
                    {selectedScenario}
                  </option>
                )}
              </select>
              <div className="text-[11px] font-mono text-theme-muted">
                {replayStatus?.current_simulated_at
                  ? replayStatus.current_simulated_at.replace('T', ' ').slice(0, 19)
                  : 'STANDBY'}
              </div>
            </div>

            {/* Processed Counter (matches vitest test for '5 / 25'!) */}
            <div className="space-y-1 mb-3">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-theme-muted">Progress:</span>
                <span className="font-bold text-theme-text">
                  {replayStatus ? `${replayStatus.processed_count} / ${replayStatus.total_records}` : '—'}
                </span>
              </div>
              <div className="w-full bg-theme-border h-2 rounded-full overflow-hidden">
                <div
                  className="bg-theme-primary h-full transition-all duration-300"
                  style={{
                    width: `${
                      replayStatus && replayStatus.total_records > 0
                        ? Math.round((replayStatus.processed_count / replayStatus.total_records) * 100)
                        : 0
                    }%`,
                  }}
                />
              </div>
            </div>
          </div>

          <div className="space-y-3 pt-2">
            {/* Speed Selector (existing options: 1, 5, 20) */}
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-theme-muted">Speed:</span>
              <div className="flex items-center gap-1 font-mono">
                {[1, 5, 20].map((spd) => (
                  <button
                    key={spd}
                    type="button"
                    onClick={() => onSpeed(spd)}
                    className={`px-2.5 py-0.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                      replayStatus?.speed === spd
                        ? 'bg-theme-primary-fill text-theme-on-primary shadow-xs'
                        : 'bg-theme-bg text-theme-text hover:bg-theme-border'
                    }`}
                  >
                    {spd}x
                  </button>
                ))}
              </div>
            </div>

            {/* Play/Pause/Step/Reset Buttons */}
            <div className="flex items-center gap-2">
              {replayStatus?.state === 'running' ? (
                <PillButton
                  variant="primary"
                  onClick={onPause}
                  disabled={replayLoading}
                  className="flex-1"
                >
                  <Pause className="w-4 h-4 fill-current" />
                  <span>Pause</span>
                </PillButton>
              ) : (
                <PillButton
                  variant="primary"
                  onClick={onPlay}
                  disabled={replayLoading}
                  className="flex-1"
                >
                  <Play className="w-4 h-4 fill-current" />
                  <span>Start Replay</span>
                </PillButton>
              )}

              <button
                type="button"
                onClick={onStep}
                disabled={replayLoading}
                aria-label="Step forward 1 record"
                title="Step 1 record forward"
                className="w-9 h-9 rounded-full border border-theme-border hover:bg-theme-bg flex items-center justify-center text-theme-text cursor-pointer transition-colors"
              >
                <StepForward className="w-4 h-4" />
              </button>

              <button
                type="button"
                onClick={onReset}
                disabled={replayLoading}
                aria-label="Reset replay"
                title="Reset Replay"
                className="w-9 h-9 rounded-full border border-theme-border hover:bg-theme-bg flex items-center justify-center text-theme-muted hover:text-theme-loss cursor-pointer transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>

            {currentPreset?.live && (
              <button
                type="button"
                onClick={onAppendLive}
                disabled={replayLoading}
                className="w-full py-1.5 px-3 rounded-full text-xs font-semibold bg-theme-primary-tint text-theme-primary-text hover:opacity-90 transition-colors"
              >
                Pull new live records
              </button>
            )}
          </div>
        </Card>

        {/* Project List: Latest High-Impact Signals (3 cols) */}
        <Card className="lg:col-span-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm md:text-base font-bold text-theme-text">
                High-Impact Signals
              </h2>
              <button
                type="button"
                onClick={() => setActiveTab('playground')}
                className="inline-flex items-center gap-1 text-xs font-semibold text-theme-primary-text hover:underline cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>New</span>
              </button>
            </div>

            <div className="space-y-2">
              {highImpactSignals.length > 0 ? (
                highImpactSignals.map((sig) => {
                  const isSelected = selectedSignal?.signal_id === sig.signal_id;
                  return (
                    <button
                      key={sig.signal_id}
                      type="button"
                      onClick={() => handleSelectHighImpact(sig)}
                      className={`w-full p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                        isSelected
                          ? 'border-theme-primary-fill bg-theme-primary-tint/60'
                          : 'border-theme-border hover:border-theme-border-strong hover:bg-theme-card-subtle'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <span className="font-mono font-bold text-xs text-theme-text">
                          {sig.entity.ticker || sig.entity.name.slice(0, 12)}
                        </span>
                        <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-theme-loss-bg text-theme-loss">
                          Score {sig.impact.score}
                        </span>
                      </div>
                      <div className="text-[11px] text-theme-text-secondary truncate">
                        {sig.evidence?.[0]?.text || sig.event.label}
                      </div>
                    </button>
                  );
                })
              ) : (
                <div className="p-4 text-center text-xs text-theme-subtle">
                  No signals with impact &gt; 7 in run
                </div>
              )}
            </div>
          </div>

          <div className="pt-2 text-center">
            <span className="text-[11px] text-theme-muted">
              Filter threshold: impact &gt; 7
            </span>
          </div>
        </Card>
      </div>

      {/* 4. Donezo Bottom Row: Team Collaboration (Stress Runs) + Gauge + Time Tracker */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-5">
        {/* Team Collaboration: Recent Stress Runs (5 cols) */}
        <Card className="lg:col-span-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-sm md:text-base font-bold text-theme-text">
                  Recent Stress Runs
                </h2>
                <p className="text-xs text-theme-muted">
                  Portfolio reconciliation &amp; shock impacts
                </p>
              </div>
              <button
                type="button"
                onClick={() => setActiveTab('stress')}
                className="text-xs font-semibold text-theme-primary-text hover:underline cursor-pointer"
              >
                View all &rarr;
              </button>
            </div>

            <div className="space-y-2">
              {hydratedRuns.length > 0 ? (
                hydratedRuns.map((run: StressRunResult) => {
                  const lossM =
                    run.total_pnl_usd !== undefined
                      ? Math.abs(run.total_pnl_usd / 1e6).toFixed(2)
                      : '—';
                  const isLargeLoss = run.total_pnl_usd !== undefined && Math.abs(run.total_pnl_usd) > 10e6;
                  const targetName = run.target_entity || run.event_class || 'Systemic Shock';

                  let statusText = '—';
                  let pillVariant: 'success' | 'warning' | 'loss' | 'neutral' = 'neutral';

                  if (run.reconciliation_passed !== undefined) {
                    if (run.total_pnl_usd === 0) {
                      statusText = 'No Exposure';
                      pillVariant = 'warning';
                    } else if (isLargeLoss) {
                      statusText = 'Large Loss';
                      pillVariant = 'loss';
                    } else {
                      statusText = 'Reconciled';
                      pillVariant = 'success';
                    }
                  }

                  return (
                    <div
                      key={run.stress_id}
                      className="p-2.5 rounded-xl border border-theme-border hover:bg-theme-card-subtle flex items-center justify-between gap-3"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="w-8 h-8 rounded-full bg-theme-primary-tint text-theme-primary-text flex items-center justify-center shrink-0">
                          <TrendingDown className="w-4 h-4 text-theme-primary-text" />
                        </div>
                        <div className="min-w-0">
                          <div className="text-xs font-bold text-theme-text truncate">
                            {targetName}
                          </div>
                          <div className="text-[10px] text-theme-muted font-mono truncate">
                            ID: {run.stress_id.slice(0, 10)}
                          </div>
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        <div className="text-xs font-bold font-mono text-theme-loss">
                          -${lossM}M
                        </div>
                        {statusText !== '—' && (
                          <Pill variant={pillVariant} size="sm">
                            {statusText}
                          </Pill>
                        )}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="p-4 text-center text-xs text-theme-subtle">
                  No stress simulations executed yet
                </div>
              )}
            </div>
          </div>

          <div className="pt-2">
            <span className="text-[11px] text-theme-muted">
              Showing last {hydratedRuns.length} runs with verified loss attribution
            </span>
          </div>
        </Card>

        {/* Project Progress: Signal Funnel Semicircle Gauge (4 cols) */}
        <Card className="lg:col-span-4 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-sm md:text-base font-bold text-theme-text">
              Signal Funnel
            </h2>
            <span className="text-xs text-theme-muted font-mono">
              {totalSignalsCount} total
            </span>
          </div>
          <div className="flex-1 flex flex-col items-center justify-center py-1">
            <Gauge
              eligibleCount={actionableCount}
              blockedCount={blockedCount}
              duplicateCount={effectiveDuplicateCount}
              label="Action Eligible"
            />
          </div>
        </Card>

        {/* Time Tracker: Replay Clock (Hero Accent Card) (3 cols) */}
        <Card
          variant="hero"
          className="lg:col-span-3 flex flex-col justify-between text-theme-hero-text"
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-theme-hero-subtle flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-theme-hero-subtle" />
              Replay Clock
            </span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-theme-hero-text/20 text-theme-hero-text">
              {replayStatus?.state?.toUpperCase() || 'IDLE'}
            </span>
          </div>

          <div className="flex-1 flex flex-col items-center justify-center my-auto py-2 text-center">
            <div className="text-3xl md:text-4xl font-bold font-mono tracking-tight text-theme-hero-text">
              {simulatedTimeFormatted}
            </div>
            <div className="text-[11px] text-theme-hero-subtle mt-1 font-mono">
              {replayStatus?.current_simulated_at?.slice(0, 10) || '—'}
            </div>
          </div>

          <div className="pt-2 text-center">
            <span className="text-[11px] text-theme-hero-subtle/90 font-mono">
              Controlled via Replay Control panel
            </span>
          </div>
        </Card>
      </div>

      {/* 5. Lower Section: Signal Feed & Signal Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-5">
        <div className="lg:col-span-7">
          <Feed
            signals={signals}
            totalSignalsCount={totalSignalsCount}
            selectedSignal={selectedSignal}
            onSelectSignal={onSelectSignal}
            searchQuery={searchQuery}
            onSearchChange={onSearchChange}
            filterEvent={filterEvent}
            onFilterEventChange={onFilterEventChange}
            showDuplicates={showDuplicates}
            onShowDuplicatesChange={onShowDuplicatesChange}
          />
        </div>
        <div className="lg:col-span-5" ref={inspectorRef}>
          <Inspector
            selectedSignal={selectedSignal}
            activeStressResult={activeStressResult}
            onViewStressPnL={() => setActiveTab('stress')}
            onSelectTopSignal={() => {
              if (signals.length > 0) {
                const top = [...signals].sort((a, b) => b.impact.score - a.impact.score)[0];
                onSelectSignal(top);
              }
            }}
          />
        </div>
      </div>
    </div>
  );
};
