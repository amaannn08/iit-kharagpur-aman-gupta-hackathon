import { useState } from 'react';
import {
  appendReplaySource,
  fetchReplayStatus,
  fetchSignals,
  loadReplayScenario,
  pauseReplay,
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

export interface UseReplayOptions {
  onSignalsUpdated?: (signals: RiskSignal[]) => void;
  onSignalSelected?: (signal: RiskSignal) => void;
}

export function useReplay(options: UseReplayOptions = {}) {
  const [replayStatus, setReplayStatus] = useState<ReplayStatus | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<string>('demo');
  const [replayLoading, setReplayLoading] = useState(false);

  const handleLoadScenario = async (scId: string) => {
    setReplayLoading(true);
    try {
      setSelectedScenario(scId);
      const st = await loadReplayScenario(scId, SOURCE_PRESETS[scId]?.sources ?? ['news_demo', 'social_demo']);
      setReplayStatus(st);
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
      if (st) setReplayStatus(st);
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
      setReplayStatus(st);
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
      setReplayStatus(st);
    } catch (err) {
      console.error(err);
    }
  };

  const handlePause = async () => {
    try {
      const st = await pauseReplay();
      setReplayStatus(st);
    } catch (err) {
      console.error(err);
    }
  };

  const handleReset = async () => {
    try {
      const st = await resetReplay();
      setReplayStatus(st);
      const sigs = await fetchSignals(50);
      options.onSignalsUpdated?.(sigs);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSpeed = async (spd: number) => {
    try {
      const st = await setReplaySpeed(spd);
      setReplayStatus(st);
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
