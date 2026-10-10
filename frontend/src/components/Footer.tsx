import React from 'react';
import { Pause, Play, RotateCcw, StepForward } from 'lucide-react';
import { LiveStatusResponse, ReplayStatus } from '../api/client';
import { SOURCE_PRESETS } from '../hooks/useReplay';

export interface FooterProps {
  replayStatus: ReplayStatus | null;
  liveStatus: LiveStatusResponse | null;
  selectedScenario: string;
  replayLoading: boolean;
  onLoadScenario: (scId: string) => void;
  onAppendLive: () => void;
  onPlay: () => void;
  onPause: () => void;
  onStep: () => void;
  onReset: () => void;
  onSpeed: (spd: number) => void;
}

export const Footer: React.FC<FooterProps> = ({
  replayStatus,
  liveStatus,
  selectedScenario,
  replayLoading,
  onLoadScenario,
  onAppendLive,
  onPlay,
  onPause,
  onStep,
  onReset,
  onSpeed,
}) => {
  return (
    <footer className="bg-black border-t border-zinc-800 px-6 py-2.5 flex flex-wrap items-center justify-between gap-4 text-xs shrink-0">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-zinc-400 font-medium">Replay source:</span>
          <select
            value={selectedScenario}
            onChange={(e) => onLoadScenario(e.target.value)}
            disabled={replayLoading}
            className="bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1 text-xs text-white font-mono focus:outline-none focus:border-zinc-500"
          >
            {Object.entries(SOURCE_PRESETS).map(([id, p]) => (
              <option key={id} value={id}>
                {p.label}
              </option>
            ))}
          </select>
          {(() => {
            const isLive = Boolean(
              SOURCE_PRESETS[selectedScenario]?.live ||
                (replayStatus?.source_badges ?? []).includes('LIVE CAPTURE') ||
                liveStatus?.mode === 'LIVE'
            );
            const isSynthetic = Boolean(
              (replayStatus?.source_badges ?? []).includes('SYNTHETIC SCENARIO') ||
                selectedScenario === 'demo' ||
                liveStatus?.mode === 'SYNTHETIC'
            );
            let badge = 'REPLAY';
            let badgeCls = 'border-zinc-700 bg-zinc-900 text-zinc-300';

            if (isLive) {
              const lag = liveStatus?.lag_seconds;
              const alive = liveStatus?.recorder_alive ?? false;
              if (lag !== null && lag !== undefined && lag < 600 && alive) {
                badge = 'LIVE';
                badgeCls = 'border-emerald-700 bg-emerald-950/60 text-emerald-400';
              } else {
                badge = 'STALE';
                badgeCls = 'border-zinc-700 bg-zinc-900 text-zinc-400';
              }
            } else if (isSynthetic) {
              badge = 'SYNTHETIC';
              badgeCls = 'border-zinc-700 bg-zinc-900 text-zinc-300';
            }

            const lagText = (() => {
              if (!liveStatus?.last_fetch_at) return null;
              const lagSec = liveStatus.lag_seconds ?? 0;
              if (lagSec < 60) return 'last fetch just now';
              return `last fetch ${Math.round(lagSec / 60)} min ago`;
            })();

            return (
              <div className="flex items-center gap-1.5" data-testid="live-status-container">
                <span
                  className={`px-1.5 py-0.5 rounded border font-mono text-[10px] font-bold ${badgeCls}`}
                  data-testid="live-status-badge"
                >
                  {badge}
                </span>
                {isLive && lagText && (
                  <span className="text-zinc-500 font-mono text-[10px] hidden sm:inline" data-testid="live-lag-text">
                    {lagText}
                  </span>
                )}
              </div>
            );
          })()}
          {SOURCE_PRESETS[selectedScenario]?.live && (
            <button
              onClick={onAppendLive}
              disabled={replayLoading}
              className="px-2.5 py-1 rounded bg-zinc-900 border border-zinc-700 text-zinc-200 hover:bg-zinc-800 transition-colors"
              title="Queue records the live recorder appended since loading"
            >
              Pull new live records
            </button>
          )}
        </div>

        <div className="flex items-center gap-1 bg-zinc-950 border border-zinc-800 rounded p-1">
          {replayStatus?.state === 'running' ? (
            <button
              onClick={onPause}
              disabled={replayLoading}
              className="p-1.5 rounded hover:bg-zinc-900 text-zinc-200 transition-colors"
              title="Pause Replay"
            >
              <Pause className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={onPlay}
              disabled={replayLoading}
              className="p-1.5 rounded hover:bg-zinc-900 text-emerald-400 transition-colors"
              title="Play Replay"
            >
              <Play className="w-3.5 h-3.5 fill-emerald-400" />
            </button>
          )}

          <button
            onClick={onStep}
            disabled={replayLoading}
            className="p-1.5 rounded hover:bg-zinc-900 text-zinc-300 hover:text-white transition-colors"
            title="Step 1 Record Forward"
          >
            <StepForward className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onReset}
            disabled={replayLoading}
            className="p-1.5 rounded hover:bg-zinc-900 text-zinc-400 hover:text-white transition-colors"
            title="Reset Replay"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Speed Selector */}
        <div className="flex items-center gap-1 font-mono">
          {[1, 5, 20].map((spd) => (
            <button
              key={spd}
              onClick={() => onSpeed(spd)}
              className={`px-2 py-0.5 rounded text-[11px] transition-colors ${
                replayStatus?.speed === spd
                  ? 'bg-white text-black font-bold border border-white'
                  : 'bg-zinc-950 text-zinc-400 hover:text-zinc-200 border border-zinc-800'
              }`}
            >
              {spd}x
            </button>
          ))}
        </div>

        <span className="font-mono text-zinc-400 text-xs">
          State: <span className="text-white uppercase font-bold">{replayStatus?.state || 'IDLE'}</span>
        </span>
      </div>

      {/* Progress & Counters */}
      <div className="flex items-center gap-4 font-mono text-xs">
        <div className="flex items-center gap-2">
          <span className="text-zinc-500">Processed:</span>
          <span className="text-white font-bold">
            {replayStatus?.processed_count || 0} / {replayStatus?.total_records || 0}
          </span>
        </div>
        <div className="w-24 bg-zinc-800 h-1.5 rounded-full overflow-hidden">
          <div
            className="bg-emerald-500 h-full transition-all duration-300"
            style={{
              width: `${
                replayStatus && replayStatus.total_records > 0
                  ? Math.round((replayStatus.processed_count / replayStatus.total_records) * 100)
                  : 0
              }%`,
            }}
          />
        </div>
        <div className="text-zinc-500">
          Dups: <span className="text-zinc-300 font-medium">{replayStatus?.duplicate_count || 0}</span>
        </div>
      </div>
    </footer>
  );
};
