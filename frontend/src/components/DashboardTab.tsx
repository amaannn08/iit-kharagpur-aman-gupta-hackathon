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
  StressRunResult,
} from '../api/client';
import { SOURCE_PRESETS } from '../hooks/useReplay';
import { TabType } from './Header';
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
  const totalSignalsCount = signals.length;
  const actionableSignals = signals.filter((s) => s.eligible_for_action);
  const actionableCount = actionableSignals.length;

  const duplicateSignalsCount = signals.filter(
    (s) => s.duplicate_group_id || s.action_block_reasons?.includes('DUPLICATE_TEXT_SUPPRESSED')
  ).length;
  const effectiveDuplicateCount = replayStatus?.duplicate_count ?? duplicateSignalsCount;

  const blockedCount = Math.max(0, totalSignalsCount - actionableCount - effectiveDuplicateCount);

  // High impact signals: STRICTLY impact.score > 7
  const highImpactSignals = signals
    .filter((s) => s.impact.score > 7)
    .slice(0, 5);

  // Event class distribution for pill bar chart
  const eventTaxonomy = ['CREDIT', 'MACRO', 'GEOPOLITICAL', 'M_AND_A', 'CYBER', 'SUPPLY_CHAIN', 'EARNINGS'];
  const eventChartData: PillBarChartDataPoint[] = eventTaxonomy.map((label) => {
    const classSignals = signals.filter(
      (s) => s.event?.label?.toUpperCase() === label
    );
    const eligible = classSignals.filter((s) => s.eligible_for_action).length;
    const blocked = classSignals.length - eligible;
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
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-[#111827]">
            Risk Dashboard
          </h1>
          <p className="text-xs md:text-sm text-[#6B7280] mt-0.5">
            Real-time text &rarr; signals &rarr; stress tests, all offline.
          </p>
        </div>

        {/* Right Action Buttons */}
        <div className="flex items-center gap-3">
          {replayStatus?.state === 'running' ? (
            <PillButton
              variant="secondary"
              onClick={onPause}
              disabled={replayLoading}
            >
              <Pause className="w-4 h-4 fill-[#14532D]" />
              <span>Pause Replay</span>
            </PillButton>
          ) : (
            <PillButton
              variant="primary"
              onClick={onPlay}
              disabled={replayLoading}
            >
              <Play className="w-4 h-4 fill-white" />
              <span>Start Replay</span>
            </PillButton>
          )}

          <PillButton
            variant="secondary"
            onClick={onStep}
            disabled={replayLoading}
          >
            <StepForward className="w-4 h-4 text-[#14532D]" />
            <span>Step Record</span>
          </PillButton>
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
              <h2 className="text-sm md:text-base font-bold text-[#111827]">
                Signals by Event Class
              </h2>
              <p className="text-xs text-[#6B7280]">
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
              <h2 className="text-sm md:text-base font-bold text-[#111827]">
                Replay Control
              </h2>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[#E8F5EE] text-[#14532D] font-bold">
                {replayStatus?.state?.toUpperCase() || 'IDLE'}
              </span>
            </div>

            {/* Replay Source Selector Dropdown */}
            <div className="p-3 rounded-xl bg-[#F3F4F3] border border-[#ECEDEC] space-y-1.5 my-3">
              <label className="text-[10px] text-[#6B7280] font-medium uppercase font-mono block">
                Replay Source Preset
              </label>
              <select
                value={selectedScenario}
                onChange={(e) => onLoadScenario(e.target.value)}
                disabled={replayLoading}
                className="w-full bg-white border border-[#ECEDEC] hover:border-gray-300 rounded-lg px-2.5 py-1.5 text-xs font-bold text-[#111827] cursor-pointer focus:outline-none focus:border-[#14532D]"
              >
                {Object.entries(SOURCE_PRESETS).map(([id, p]) => (
                  <option key={id} value={id}>
                    {p.label}
                  </option>
                ))}
              </select>
              <div className="text-[11px] font-mono text-[#6B7280]">
                {replayStatus?.current_simulated_at
                  ? replayStatus.current_simulated_at.replace('T', ' ').slice(0, 19)
                  : 'STANDBY'}
              </div>
            </div>

            {/* Processed Counter (matches vitest test for '5 / 25'!) */}
            <div className="space-y-1 mb-3">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-[#6B7280]">Progress:</span>
                <span className="font-bold text-[#111827]">
                  {replayStatus ? `${replayStatus.processed_count} / ${replayStatus.total_records}` : '—'}
                </span>
              </div>
              <div className="w-full bg-[#ECEDEC] h-2 rounded-full overflow-hidden">
                <div
                  className="bg-[#1F6B45] h-full transition-all duration-300"
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
              <span className="text-xs text-[#6B7280]">Speed:</span>
              <div className="flex items-center gap-1 font-mono">
                {[1, 5, 20].map((spd) => (
                  <button
                    key={spd}
                    type="button"
                    onClick={() => onSpeed(spd)}
                    className={`px-2.5 py-0.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                      replayStatus?.speed === spd
                        ? 'bg-[#14532D] text-white shadow-xs'
                        : 'bg-[#F3F4F3] text-[#4B5563] hover:bg-gray-200'
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
                  <Pause className="w-4 h-4 fill-white" />
                  <span>Pause</span>
                </PillButton>
              ) : (
                <PillButton
                  variant="primary"
                  onClick={onPlay}
                  disabled={replayLoading}
                  className="flex-1"
                >
                  <Play className="w-4 h-4 fill-white" />
                  <span>Start Replay</span>
                </PillButton>
              )}

              <button
                type="button"
                onClick={onStep}
                disabled={replayLoading}
                aria-label="Step forward 1 record"
                title="Step 1 record forward"
                className="w-9 h-9 rounded-full border border-[#ECEDEC] hover:bg-[#F3F4F3] flex items-center justify-center text-[#111827] cursor-pointer transition-colors"
              >
                <StepForward className="w-4 h-4" />
              </button>

              <button
                type="button"
                onClick={onReset}
                disabled={replayLoading}
                aria-label="Reset replay"
                title="Reset Replay"
                className="w-9 h-9 rounded-full border border-[#ECEDEC] hover:bg-[#F3F4F3] flex items-center justify-center text-[#6B7280] hover:text-[#DC2626] cursor-pointer transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>

            {currentPreset?.live && (
              <button
                type="button"
                onClick={onAppendLive}
                disabled={replayLoading}
                className="w-full py-1.5 px-3 rounded-full text-xs font-semibold bg-[#E8F5EE] text-[#14532D] hover:bg-emerald-100 transition-colors"
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
              <h2 className="text-sm md:text-base font-bold text-[#111827]">
                High-Impact Signals
              </h2>
              <button
                type="button"
                onClick={() => setActiveTab('playground')}
                className="inline-flex items-center gap-1 text-xs font-semibold text-[#14532D] hover:underline cursor-pointer"
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
                          ? 'border-[#14532D] bg-[#E8F5EE]/60'
                          : 'border-[#ECEDEC] hover:border-gray-300 hover:bg-[#F9FAF9]'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <span className="font-mono font-bold text-xs text-[#111827]">
                          {sig.entity.ticker || sig.entity.name.slice(0, 12)}
                        </span>
                        <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-[#FEE2E2] text-[#DC2626]">
                          Score {sig.impact.score}
                        </span>
                      </div>
                      <div className="text-[11px] text-[#4B5563] truncate">
                        {sig.evidence?.[0]?.text || sig.event.label}
                      </div>
                    </button>
                  );
                })
              ) : (
                <div className="p-4 text-center text-xs text-[#9CA3AF]">
                  No signals with impact &gt; 7 in run
                </div>
              )}
            </div>
          </div>

          <div className="pt-2 text-center">
            <span className="text-[11px] text-[#6B7280]">
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
                <h2 className="text-sm md:text-base font-bold text-[#111827]">
                  Recent Stress Runs
                </h2>
                <p className="text-xs text-[#6B7280]">
                  Portfolio reconciliation &amp; shock impacts
                </p>
              </div>
              <button
                type="button"
                onClick={() => setActiveTab('stress')}
                className="text-xs font-semibold text-[#14532D] hover:underline cursor-pointer"
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
                      className="p-2.5 rounded-xl border border-[#ECEDEC] hover:bg-[#F9FAF9] flex items-center justify-between gap-3"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="w-8 h-8 rounded-full bg-[#E8F5EE] text-[#14532D] flex items-center justify-center shrink-0">
                          <TrendingDown className="w-4 h-4 text-[#14532D]" />
                        </div>
                        <div className="min-w-0">
                          <div className="text-xs font-bold text-[#111827] truncate">
                            {targetName}
                          </div>
                          <div className="text-[10px] text-[#6B7280] font-mono truncate">
                            ID: {run.stress_id.slice(0, 10)}
                          </div>
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        <div className="text-xs font-bold font-mono text-[#DC2626]">
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
                <div className="p-4 text-center text-xs text-[#9CA3AF]">
                  No stress simulations executed yet
                </div>
              )}
            </div>
          </div>

          <div className="pt-2">
            <span className="text-[11px] text-[#6B7280]">
              Showing last {hydratedRuns.length} runs with verified loss attribution
            </span>
          </div>
        </Card>

        {/* Project Progress: Signal Funnel Semicircle Gauge (4 cols) */}
        <Card className="lg:col-span-4 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-sm md:text-base font-bold text-[#111827]">
              Signal Funnel
            </h2>
            <span className="text-xs text-[#6B7280] font-mono">
              {totalSignalsCount} total
            </span>
          </div>
          <Gauge
            eligibleCount={actionableCount}
            blockedCount={blockedCount}
            duplicateCount={effectiveDuplicateCount}
            label="Action Eligible"
          />
        </Card>

        {/* Time Tracker: Replay Clock (Hero Accent Card) (3 cols) */}
        <Card
          variant="hero"
          className="lg:col-span-3 flex flex-col justify-between text-white"
        >
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-emerald-100 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-emerald-200" />
                Replay Clock
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-white/20 text-white">
                {replayStatus?.state?.toUpperCase() || 'IDLE'}
              </span>
            </div>

            <div className="my-5 text-center">
              <div className="text-3xl md:text-4xl font-bold font-mono tracking-tight text-white">
                {simulatedTimeFormatted}
              </div>
              <div className="text-[11px] text-emerald-200 mt-1 font-mono">
                {replayStatus?.current_simulated_at?.slice(0, 10) || '2026-03-01'}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-center gap-3 pt-2">
            {replayStatus?.state === 'running' ? (
              <button
                type="button"
                onClick={onPause}
                disabled={replayLoading}
                aria-label="Pause clock"
                className="w-10 h-10 rounded-full bg-white text-[#14532D] hover:bg-emerald-50 flex items-center justify-center shadow-sm cursor-pointer transition-transform active:scale-95"
              >
                <Pause className="w-4 h-4 fill-[#14532D]" />
              </button>
            ) : (
              <button
                type="button"
                onClick={onPlay}
                disabled={replayLoading}
                aria-label="Play clock"
                className="w-10 h-10 rounded-full bg-white text-[#14532D] hover:bg-emerald-50 flex items-center justify-center shadow-sm cursor-pointer transition-transform active:scale-95"
              >
                <Play className="w-4 h-4 fill-[#14532D] translate-x-0.5" />
              </button>
            )}

            <button
              type="button"
              onClick={onReset}
              disabled={replayLoading}
              aria-label="Reset clock"
              className="w-10 h-10 rounded-full bg-[#DC2626] text-white hover:bg-red-700 flex items-center justify-center shadow-sm cursor-pointer transition-transform active:scale-95"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </Card>
      </div>

      {/* 5. Lower Section: Signal Feed & Signal Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-5">
        <div className="lg:col-span-7">
          <Feed
            signals={signals}
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
