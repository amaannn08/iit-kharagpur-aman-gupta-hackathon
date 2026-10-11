import { useEffect, useState } from 'react';
import {
  appendReplaySource,
  fetchReplayPresets,
  fetchReplayStatus,
  fetchSignals,
  loadReplayScenario,
  pauseReplay,
  ReplayPresetItem,
  ReplayStatus,
  resetReplay,
  resumeReplay,
  RiskSignal,
  setReplaySpeed,
  stepReplay,
} from '../api/client';

export const SOURCE_PRESETS: Record<string, { label: string; sources: string[]; live?: boolean }> = {
  demo: { label: 'Synthetic demo scenario (news + social)', sources: ['news_demo', 'social_demo'] },
  polygon_2023: { label: 'Real news: Polygon 2023 (5,548 articles)', sources: ['polygon_2023'] },
  gdelt_snapshot: { label: 'Real news: GDELT 2-hour snapshot', sources: ['gdelt_snapshot'] },
  gdelt_svb_2023: { label: 'Real replay: SVB weekend bank run 2023', sources: ['gdelt_svb_2023'] },
  stock_tweets: { label: 'Real social: stock tweets 2017-18 sample', sources: ['stock_tweets'] },
  live: { label: 'Live capture: GDELT + SEC 8-K', sources: ['gdelt_live', 'sec_8k_live'], live: true },
};

/**
 * Matches a ReplayStatus from GET /api/replay/status against preset configurations.
 * Checks sources first, then scenario_id; if neither matches, returns the real source list.
 */
export function matchPresetFromStatus(
  status: ReplayStatus | null,
  presets: Record<string, { label: string; sources: string[]; live?: boolean }> = SOURCE_PRESETS,
  serverPresets?: ReplayPresetItem[]
): string {
  if (!status) return 'demo';
  const statusSources = status.sources && status.sources.length > 0 ? status.sources : [];
  const statusScenario = status.scenario_id || '';

  // 1. Match by sources against presets
  if (statusSources.length > 0) {
    const sortedStatus = [...statusSources].sort().join(',');
    for (const [key, preset] of Object.entries(presets)) {
      if ([...preset.sources].sort().join(',') === sortedStatus) {
        return key;
      }
    }
    if (serverPresets) {
      for (const sp of serverPresets) {
        if ([...sp.sources].sort().join(',') === sortedStatus) {
          for (const [key, preset] of Object.entries(presets)) {
            if ([...preset.sources].sort().join(',') === sortedStatus) return key;
          }
          return sp.id;
        }
      }
    }
  }

  // 2. Match by scenario_id
  if (statusScenario) {
    if (presets[statusScenario]) return statusScenario;
    for (const [key, preset] of Object.entries(presets)) {
      if (preset.sources.includes(statusScenario)) {
        return key;
      }
    }
    if (serverPresets) {
      for (const sp of serverPresets) {
        if (sp.id === statusScenario || sp.sources.includes(statusScenario)) {
          for (const [key, preset] of Object.entries(presets)) {
            if ([...preset.sources].sort().join(',') === [...sp.sources].sort().join(',')) return key;
          }
          return sp.id;
        }
      }
    }
  }

  // 3. Fallback: show the real source list, not "demo"
  if (statusSources.length > 0) {
    return statusSources.join(', ');
  }
  if (statusScenario) {
    return statusScenario;
  }

  return 'demo';
}

export interface UseReplayOptions {
  onSignalsUpdated?: (signals: RiskSignal[]) => void;
  onSignalSelected?: (signal: RiskSignal) => void;
}

export function useReplay(options: UseReplayOptions = {}) {
  const [replayStatus, setReplayStatusState] = useState<ReplayStatus | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<string>('demo');
  const [replayLoading, setReplayLoading] = useState(false);

  const setReplayStatus = (st: ReplayStatus | null) => {
    setReplayStatusState(st);
    if (st) {
      setSelectedScenario(matchPresetFromStatus(st));
    }
  };

  useEffect(() => {
    Promise.allSettled([fetchReplayStatus(), fetchReplayPresets()])
      .then(([statusRes, presetsRes]) => {
        const st = statusRes.status === 'fulfilled' ? statusRes.value : null;
        const sp = presetsRes.status === 'fulfilled' ? presetsRes.value : undefined;
        if (st) {
          setReplayStatusState(st);
          setSelectedScenario(matchPresetFromStatus(st, SOURCE_PRESETS, sp));
        }
      })
      .catch(() => {});
  }, []);

  const handleLoadScenario = async (scId: string) => {
    setReplayLoading(true);
    try {
      setSelectedScenario(scId);
      const sources =
        SOURCE_PRESETS[scId]?.sources ??
        (scId.includes(',') ? scId.split(',').map((s) => s.trim()) : [scId]);
      const st = await loadReplayScenario(scId, sources);
      setReplayStatusState(st);
      if (st.processed_count === 0 && st.pending_records > 0) {
        await stepReplay();
        const updated = await fetchReplayStatus();
        setReplayStatusState(updated);
      }
      const sigs = await fetchSignals(50);
      options.onSignalsUpdated?.(sigs);
      if (sigs.length > 0) options.onSignalSelected?.(sigs[0]);
    } catch (err) {
      console.error(err);
    } finally {
      setReplayLoading(false);
    }
  };

  const handleAppendLive = async () => {
    setReplayLoading(true);
    try {
      let st: ReplayStatus | null = null;
      for (const src of SOURCE_PRESETS[selectedScenario]?.sources ?? []) st = await appendReplaySource(src);
      if (st) setReplayStatusState(st);
    } catch (err) {
      console.error(err);
    } finally {
      setReplayLoading(false);
    }
  };

  const handleStep = async () => {
    setReplayLoading(true);
    try {
      await stepReplay();
      const st = await fetchReplayStatus();
      setReplayStatusState(st);
      const sigs = await fetchSignals(50);
      options.onSignalsUpdated?.(sigs);
    } catch (err) {
      console.error(err);
    } finally {
      setReplayLoading(false);
    }
  };

  const handlePlay = async () => {
    try {
      const st = await resumeReplay();
      setReplayStatusState(st);
    } catch (err) {
      console.error(err);
    }
  };

  const handlePause = async () => {
    try {
      const st = await pauseReplay();
      setReplayStatusState(st);
    } catch (err) {
      console.error(err);
    }
  };

  const handleReset = async () => {
    try {
      const st = await resetReplay();
      setReplayStatusState(st);
      const sigs = await fetchSignals(50);
      options.onSignalsUpdated?.(sigs);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSpeed = async (spd: number) => {
    try {
      const st = await setReplaySpeed(spd);
      setReplayStatusState(st);
    } catch (err) {
      console.error(err);
    }
  };

  return {
    replayStatus,
    setReplayStatus,
    selectedScenario,
    setSelectedScenario,
    replayLoading,
    setReplayLoading,
    handleLoadScenario,
    handleAppendLive,
    handleStep,
    handlePlay,
    handlePause,
    handleReset,
    handleSpeed,
  };
}
