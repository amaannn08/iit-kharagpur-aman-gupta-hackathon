import { useEffect, useState } from 'react';
import {
  analyzeText,
  AnalyzeResponse,
  fetchDatasets,
  fetchHealth,
  fetchPortfolio,
  fetchReplayStatus,
  fetchSignals,
  fetchStressRun,
  fetchStressRuns,
  HealthResponse,
  ManifestResponse,
  RiskSignal,
  simulateStress,
  StressRunResult,
  WholesalePortfolio,
} from './api/client';
import { DatasetsTab } from './components/DatasetsTab';
import { EvalTab } from './components/EvalTab';
import { Feed } from './components/Feed';
import { Footer } from './components/Footer';
import { Header, TabType } from './components/Header';
import { IndexPanel } from './components/IndexPanel';
import { Inspector } from './components/Inspector';
import { Sandbox } from './components/Sandbox';
import { StressTab } from './components/StressTab';
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
    ]).then(([hRes, mRes, pRes, rRes, sRes, strRes]) => {
      if (hRes.status === 'fulfilled') setHealth(hRes.value);
      if (mRes.status === 'fulfilled') setManifest(mRes.value);
      if (pRes.status === 'fulfilled') setPortfolio(pRes.value);
      if (rRes.status === 'fulfilled') setReplayStatus(rRes.value);
      if (sRes.status === 'fulfilled') {
        setSignals(sRes.value);
        if (sRes.value.length > 0 && !selectedSignal) {
          setSelectedSignal(sRes.value[0]);
        }
      }
      if (strRes.status === 'fulfilled' && strRes.value.length > 0) {
        // /api/stress/runs returns summaries without breakdowns: load the full recent results
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

  return (
    <div className="min-h-screen bg-[#0B0F17] text-[#E5E7EB] flex flex-col font-sans">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        sseConnected={sseConnected}
        replayStatus={replayStatus}
      />

      {/* Main Workspace Area */}
      <main className="flex-1 p-6 overflow-hidden flex flex-col">
        {activeTab === 'feed' && (
          <div className="flex-1 grid grid-cols-12 gap-6 overflow-hidden">
            <Feed
              signals={signals}
              selectedSignal={selectedSignal}
              onSelectSignal={setSelectedSignal}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              filterEvent={filterEvent}
              onFilterEventChange={setFilterEvent}
              showDuplicates={showDuplicates}
              onShowDuplicatesChange={setShowDuplicates}
            />
            <Inspector
              selectedSignal={selectedSignal}
              activeStressResult={activeStressResult}
              onViewStressPnL={() => setActiveTab('stress')}
            />
          </div>
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

        {activeTab === 'overview' && <DatasetsTab manifest={manifest} health={health} />}

        {activeTab === 'eval' && <EvalTab />}
      </main>

      {/* Bottom Replay Control Toolbar */}
      <Footer
        replayStatus={replayStatus}
        liveStatus={liveStatus}
        selectedScenario={selectedScenario}
        replayLoading={replayLoading}
        onLoadScenario={handleLoadScenario}
        onAppendLive={handleAppendLive}
        onPlay={handlePlay}
        onPause={handlePause}
        onStep={handleStep}
        onReset={handleReset}
        onSpeed={handleSpeed}
      />
    </div>
  );
}
export default App;
