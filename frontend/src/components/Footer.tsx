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
    <footer className="bg-[#111827] border-t border-gray-800 px-6 py-3 flex flex-wrap items-center justify-between gap-4 text-xs shrink-0">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-gray-400 font-medium">Replay source:</span>
          <select
            value={selectedScenario}
            onChange={(e) => onLoadScenario(e.target.value)}
            disabled={replayLoading}
            className="bg-[#0B0F17] border border-gray-800 rounded px-2.5 py-1 text-xs text-cyan-300 font-mono focus:outline-none focus:border-cyan-500"
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
            let badgeCls = 'border-gray-700 bg-gray-800 text-gray-300';

            if (isLive) {
              const lag = liveStatus?.lag_seconds;
              const alive = liveStatus?.recorder_alive ?? false;
              if (lag !== null && lag !== undefined && lag < 600 && alive) {
                badge = 'LIVE';
                badgeCls = 'border-emerald-600 bg-emerald-950/80 text-emerald-300 animate-pulse';
              } else {
                badge = 'STALE';
                badgeCls = 'border-amber-600 bg-amber-950/80 text-amber-300';
              }
            } else if (isSynthetic) {
              badge = 'SYNTHETIC';
              badgeCls = 'border-purple-700 bg-purple-950/80 text-purple-300';
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
                  <span className="text-gray-400 font-mono text-[10px] hidden sm:inline" data-testid="live-lag-text">
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
              className="px-2 py-1 rounded border border-cyan-700 text-cyan-300 hover:bg-cyan-950"
              title="Queue records the live recorder appended since loading"
            >
              Pull new live records
            </button>
          )}
        </div>

        <div className="flex items-center gap-1 bg-gray-900 border border-gray-800 rounded p-1">
          {replayStatus?.state === 'running' ? (
            <button
              onClick={onPause}
              disabled={replayLoading}
              className="p-1.5 rounded hover:bg-gray-800 text-amber-400 transition-colors"
              title="Pause Replay"
            >
              <Pause className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={onPlay}
              disabled={replayLoading}
              className="p-1.5 rounded hover:bg-gray-800 text-emerald-400 transition-colors"
              title="Play Replay"
            >
              <Play className="w-3.5 h-3.5 fill-emerald-400" />
            </button>
          )}

          <button
            onClick={onStep}
            disabled={replayLoading}
            className="p-1.5 rounded hover:bg-gray-800 text-cyan-400 transition-colors"
            title="Step 1 Record Forward"
          >
            <StepForward className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onReset}
            disabled={replayLoading}
            className="p-1.5 rounded hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
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
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-700'
                  : 'bg-gray-900 text-gray-400 hover:text-gray-200'
              }`}
            >
              {spd}x
            </button>
          ))}
        </div>

        <span className="font-mono text-gray-400 text-xs">
          State: <span className="text-white uppercase font-bold">{replayStatus?.state || 'IDLE'}</span>
        </span>
      </div>

      {/* Progress & Counters */}
      <div className="flex items-center gap-4 font-mono text-xs">
        <div className="flex items-center gap-2">
          <span className="text-gray-500">Processed:</span>
          <span className="text-white font-bold">
            {replayStatus?.processed_count || 0} / {replayStatus?.total_records || 0}
          </span>
        </div>
        <div className="w-24 bg-gray-800 h-1.5 rounded-full overflow-hidden">
          <div
            className="bg-cyan-500 h-full transition-all duration-300"
            style={{
              width: `${
                replayStatus && replayStatus.total_records > 0
                  ? Math.round((replayStatus.processed_count / replayStatus.total_records) * 100)
                  : 0
              }%`,
            }}
          />
        </div>
        <div className="text-gray-500">
          Dups: <span className="text-amber-400">{replayStatus?.duplicate_count || 0}</span>
        </div>
      </div>
    </footer>
  );
};
