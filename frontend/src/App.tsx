import { useEffect, useState } from 'react';
import {
  analyzeText,
  AnalyzeResponse,
  fetchDatasets,
  fetchHealth,
  fetchPortfolio,
  fetchReplayStatus,
  fetchSignals,
  fetchSignalStats,
  fetchStressRun,
  fetchStressRuns,
  HealthResponse,
  ManifestResponse,
  RiskSignal,
  SignalStats,
  simulateStress,
  StressRunResult,
  WholesalePortfolio,
} from './api/client';
import { DashboardTab } from './components/DashboardTab';
import { DatasetsTab } from './components/DatasetsTab';
import { EvalTab } from './components/EvalTab';
import { TabType } from './types/navigation';
import { IndexPanel } from './components/IndexPanel';
import { Sandbox } from './components/Sandbox';
import { SidebarNav } from './components/SidebarNav';
import { StressTab } from './components/StressTab';
import { TopBar } from './components/TopBar';
import { useLiveStatus } from './hooks/useLiveStatus';
import { useReplay } from './hooks/useReplay';
import { useSSE } from './hooks/useSSE';

export function App() {
  // Navigation & System State
  const [activeTab, setActiveTab] = useState<TabType>('feed');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [manifest, setManifest] = useState<ManifestResponse | null>(null);
  const [portfolio, setPortfolio] = useState<WholesalePortfolio | null>(null);

  // Signals Feed & Selection State
  const [signals, setSignals] = useState<RiskSignal[]>([]);
  const [signalStats, setSignalStats] = useState<SignalStats | null>(null);
  const [selectedSignal, setSelectedSignal] = useState<RiskSignal | null>(null);
  const [filterEvent, setFilterEvent] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showDuplicates, setShowDuplicates] = useState<boolean>(true);

  // Live Tailer Status Hook
  const { liveStatus } = useLiveStatus();

  // Replay Controller Hook
  const {
    replayStatus,
    setReplayStatus,
    selectedScenario,
    replayLoading,
    handleLoadScenario,
    handleAppendLive,
    handleStep,
    handlePlay,
    handlePause,
    handleReset,
    handleSpeed,
  } = useReplay({
    onSignalsUpdated: (sigs) => setSignals(sigs),
    onSignalSelected: (sig) => setSelectedSignal(sig),
  });

  // Stress State
  const [stressRuns, setStressRuns] = useState<StressRunResult[]>([]);
  const [activeStressResult, setActiveStressResult] = useState<StressRunResult | null>(null);
  const [stressForm, setStressForm] = useState({
    event_class: 'CREDIT',
    impact_score: 8,
    target_entity: 'APEX',
    target_scope: 'entity',
    is_easing: false,
  });
  const [simulatingStress, setSimulatingStress] = useState<boolean>(false);

  // Playground State
  const [playgroundText, setPlaygroundText] = useState<string>(
    'Apex Industrial Holdings missed its scheduled $45M coupon payment and syndicates report debt restructuring talks have collapsed, raising imminent Chapter 11 bankruptcy probability.'
  );
  const [playgroundSource, setPlaygroundSource] = useState<string>('news');
  const [playgroundLoading, setPlaygroundLoading] = useState<boolean>(false);
  const [playgroundResult, setPlaygroundResult] = useState<AnalyzeResponse | null>(null);

  // Initial Data Fetch
  useEffect(() => {
    Promise.allSettled([
      fetchHealth(),
      fetchDatasets(),
      fetchPortfolio(),
      fetchReplayStatus(),
      fetchSignals(50),
      fetchStressRuns(10),
      fetchSignalStats(),
    ]).then(([hRes, mRes, pRes, rRes, sRes, strRes, statRes]) => {
      if (hRes.status === 'fulfilled') setHealth(hRes.value);
      if (mRes.status === 'fulfilled') setManifest(mRes.value);
      if (pRes.status === 'fulfilled') setPortfolio(pRes.value);
      if (rRes.status === 'fulfilled') setReplayStatus(rRes.value);
      if (statRes.status === 'fulfilled') setSignalStats(statRes.value);
      if (sRes.status === 'fulfilled') {
        const fetched = sRes.value;
        setSignals(fetched);
        if (fetched.length > 0 && !selectedSignal) {
          setSelectedSignal(fetched[0]);
        } else if (fetched.length === 0) {
          // Cold-start self-healing: automatically prime demo scenario and advance initial records
          handleLoadScenario('demo').then(() => {
            handleStep();
          });
        }
      }
      if (strRes.status === 'fulfilled' && strRes.value.length > 0) {
        // /api/stress/runs returns summaries without breakdowns: load full recent results
        Promise.all(strRes.value.slice(0, 5).map((run: { stress_id: string }) => fetchStressRun(run.stress_id)))
          .then((full) => {
            setStressRuns(full);
            setActiveStressResult(full[0]);
          })
          .catch((err) => console.error(err));
      }
    });
  }, []);

  // SSE Realtime Subscription with Graceful Reconnect
  const { sseConnected } = useSSE({
    onSignal: (sig) => {
      setSignals((prev) => {
        const exists = prev.some((s) => s.signal_id === sig.signal_id);
        if (exists) return prev;
        return [sig, ...prev];
      });
      setSignalStats((prev) => {
        if (!prev) return null;
        const isEligible = Boolean(sig.eligible_for_action);
        const isDup = Boolean(
          sig.duplicate_group_id || sig.action_block_reasons?.includes('DUPLICATE_TEXT_SUPPRESSED')
        );
        const label = (sig.event?.label || 'OTHER').toUpperCase();
        const prevEvent = prev.by_event[label] || { eligible: 0, blocked: 0, total: 0 };
        return {
          total_signals: prev.total_signals + 1,
          actionable_count: prev.actionable_count + (isEligible ? 1 : 0),
          duplicate_count: prev.duplicate_count + (isDup ? 1 : 0),
          blocked_count: prev.blocked_count + (!isEligible ? 1 : 0),
          high_impact_count: prev.high_impact_count + ((sig.impact?.score ?? 0) > 7 ? 1 : 0),
          by_event: {
            ...prev.by_event,
            [label]: {
              eligible: prevEvent.eligible + (isEligible ? 1 : 0),
              blocked: prevEvent.blocked + (!isEligible ? 1 : 0),
              total: prevEvent.total + 1,
            },
          },
        };
      });
    },
    onStressRun: (sRun) => {
      setStressRuns((prev) => [sRun, ...prev.filter((r) => r.stress_id !== sRun.stress_id)]);
      setActiveStressResult(sRun);
    },
    onReplayStatus: (st) => {
      setReplayStatus(st);
    },
  });

  // Manual Stress Simulation
  const handleRunStressSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimulatingStress(true);
    try {
      const result = await simulateStress({
        event_class: stressForm.event_class,
        impact_score: Number(stressForm.impact_score),
        target_entity: stressForm.target_entity,
        target_scope: stressForm.target_scope,
        is_easing: stressForm.is_easing,
      });
      setActiveStressResult(result);
      setStressRuns((prev) => [result, ...prev]);
    } catch (err) {
      console.error(err);
    } finally {
      setSimulatingStress(false);
    }
  };

  // Playground Text Analysis
  const handleAnalyzePlayground = async () => {
    if (!playgroundText.trim()) return;
    setPlaygroundLoading(true);
    try {
      const res = await analyzeText(playgroundText, playgroundSource);
      setPlaygroundResult(res);
      setSelectedSignal(res.signal);
      if (res.stress_run) {
        setActiveStressResult(res.stress_run);
        setStressRuns((prev) => [res.stress_run!, ...prev]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setPlaygroundLoading(false);
    }
  };

  const totalSignalsCount = Math.max(
    signalStats?.total_signals ?? 0,
    replayStatus?.processed_count ?? 0,
    signals.length
  );

  return (
    <div className="h-screen bg-theme-bg text-theme-text flex items-center justify-center p-3 sm:p-5 md:p-7 overflow-hidden box-border">
      {/* Donezo Main Shell: Large Rounded Container with Subtle Shadow */}
      <div className="w-full max-w-[1740px] h-full bg-theme-card rounded-[28px] border border-theme-border shadow-[0_12px_40px_rgba(0,0,0,0.06)] flex overflow-hidden">
        {/* Left Sidebar Navigation */}
        <SidebarNav
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          signalsCount={totalSignalsCount}
          liveStatus={liveStatus}
          replayStatus={replayStatus}
          selectedScenario={selectedScenario}
          onLoadScenario={handleLoadScenario}
          onAppendLive={handleAppendLive}
        />

        {/* Right Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-theme-workspace">
          {/* Top Bar with Search, Honesty Badge, Stream Status, Profile */}
          <TopBar
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            sseConnected={sseConnected}
            replayStatus={replayStatus}
          />

          {/* Main Tab Workspace */}
          <main className="flex-1 p-5 md:p-7 overflow-y-auto min-h-0">
            {activeTab === 'feed' && (
              <DashboardTab
                signals={signals}
                signalStats={signalStats}
                selectedSignal={selectedSignal}
                onSelectSignal={setSelectedSignal}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                filterEvent={filterEvent}
                onFilterEventChange={setFilterEvent}
                showDuplicates={showDuplicates}
                onShowDuplicatesChange={setShowDuplicates}
                activeStressResult={activeStressResult}
                stressRuns={stressRuns}
                replayStatus={replayStatus}
                selectedScenario={selectedScenario}
                replayLoading={replayLoading}
                onLoadScenario={handleLoadScenario}
                onAppendLive={handleAppendLive}
                onPlay={handlePlay}
                onPause={handlePause}
                onStep={handleStep}
                onReset={handleReset}
                onSpeed={handleSpeed}
                setActiveTab={setActiveTab}
              />
            )}

            {activeTab === 'stress' && (
              <StressTab
                portfolio={portfolio}
                activeStressResult={activeStressResult}
                setActiveStressResult={setActiveStressResult}
                stressRuns={stressRuns}
                stressForm={stressForm}
                setStressForm={setStressForm}
                simulatingStress={simulatingStress}
                onRunStressSimulation={handleRunStressSimulation}
                signals={signals}
              />
            )}

            {activeTab === 'index' && <IndexPanel />}

            {activeTab === 'playground' && (
              <Sandbox
                playgroundText={playgroundText}
                onTextChange={setPlaygroundText}
                playgroundSource={playgroundSource}
                onSourceChange={setPlaygroundSource}
                playgroundLoading={playgroundLoading}
                playgroundResult={playgroundResult}
                onAnalyze={handleAnalyzePlayground}
                onOpenStressTab={() => setActiveTab('stress')}
              />
            )}

            {activeTab === 'overview' && (
              <DatasetsTab manifest={manifest} health={health} />
            )}

            {activeTab === 'eval' && <EvalTab />}
          </main>
        </div>
      </div>
    </div>
  );
}

export default App;
