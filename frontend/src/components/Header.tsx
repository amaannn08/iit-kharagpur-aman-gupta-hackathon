import React from 'react';
import {
  Activity,
  Database,
  FileCheck,
  LineChart,
  ShieldAlert,
  Sparkles,
  TrendingDown,
} from 'lucide-react';
import { ReplayStatus } from '../api/client';

export type TabType = 'feed' | 'stress' | 'index' | 'playground' | 'overview' | 'eval';

export interface HeaderProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  sseConnected: boolean;
  replayStatus: ReplayStatus | null;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  sseConnected,
  replayStatus,
}) => {
  return (
    <>
      {/* Top Warning Banner: Mandatory Honesty & Provenance Badge */}
      <div className="bg-zinc-950 border-b border-zinc-800 px-4 py-1.5 flex items-center justify-between text-xs shrink-0 text-zinc-400">
        <div className="flex items-center gap-2 tracking-wide">
          <ShieldAlert className="w-4 h-4 text-zinc-400 shrink-0" />
          <span className="uppercase px-2 py-0.5 rounded bg-zinc-900 border border-zinc-700 text-zinc-200 font-mono text-[10px] font-semibold">
            HISTORICAL REPLAY / SYNTHETIC SCENARIO
          </span>
          <span className="text-zinc-400 font-normal hidden sm:inline text-[11px]">
            100% Offline Localhost Execution • Zero External APIs • Verified Datasets
          </span>
        </div>
        <div className="flex items-center gap-3 text-zinc-400 text-[11px]">
          <span>Candidate: Aman Gupta (IIT Kharagpur)</span>
          <span className="hidden md:inline">•</span>
          <span className="font-mono bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800 text-zinc-300 hidden md:inline">
            {(replayStatus?.source_badges ?? []).join(' + ') || (replayStatus?.scenario_id ? `Scenario: ${replayStatus.scenario_id}` : 'Audited Scenarios Loaded')}
          </span>
        </div>
      </div>

      {/* Main Terminal Header */}
      <header className="bg-black border-b border-zinc-800 px-6 py-2.5 flex flex-wrap items-center justify-between gap-4 shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={`w-2.5 h-2.5 rounded-full ${sseConnected ? 'bg-emerald-500' : 'bg-zinc-600'}`} />
            <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
              S&P Sentinel
              <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-900 text-zinc-300 border border-zinc-700 font-mono font-semibold">
                RISK TERMINAL
              </span>
            </h1>
          </div>
          <span className="text-zinc-700 text-sm hidden sm:inline">|</span>
          <nav className="flex items-center gap-1.5 overflow-x-auto">
            <button
              onClick={() => setActiveTab('feed')}
              className={`px-3 py-1.5 rounded text-xs transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'feed'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-900 font-medium'
              }`}
            >
              <Activity className={`w-3.5 h-3.5 ${activeTab === 'feed' ? 'text-black' : 'text-zinc-400'}`} />
              Live Signals Feed
            </button>
            <button
              onClick={() => setActiveTab('stress')}
              className={`px-3 py-1.5 rounded text-xs transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'stress'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-900 font-medium'
              }`}
            >
              <TrendingDown className={`w-3.5 h-3.5 ${activeTab === 'stress' ? 'text-black' : 'text-red-400'}`} />
              Wholesale Stress
            </button>
            <button
              onClick={() => setActiveTab('index')}
              className={`px-3 py-1.5 rounded text-xs transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'index'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-900 font-medium'
              }`}
            >
              <LineChart className={`w-3.5 h-3.5 ${activeTab === 'index' ? 'text-black' : 'text-zinc-400'}`} />
              Index Rebalancer (Module A)
            </button>
            <button
              onClick={() => setActiveTab('playground')}
              className={`px-3 py-1.5 rounded text-xs transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'playground'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-900 font-medium'
              }`}
            >
              <Sparkles className={`w-3.5 h-3.5 ${activeTab === 'playground' ? 'text-black' : 'text-zinc-400'}`} />
              NLP Sandbox
            </button>
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-3 py-1.5 rounded text-xs transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'overview'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-900 font-medium'
              }`}
            >
              <Database className={`w-3.5 h-3.5 ${activeTab === 'overview' ? 'text-black' : 'text-zinc-400'}`} />
              Datasets & Readiness
            </button>
            <button
              onClick={() => setActiveTab('eval')}
              className={`px-3 py-1.5 rounded text-xs transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'eval'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-900 font-medium'
              }`}
            >
              <FileCheck className={`w-3.5 h-3.5 ${activeTab === 'eval' ? 'text-black' : 'text-emerald-400'}`} />
              Evaluation & Governance
            </button>
          </nav>
        </div>

        {/* Backend Status & SSE Pill */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs bg-zinc-950 border border-zinc-800 rounded px-3 py-1">
            <span className="text-zinc-400">Replay Clock:</span>
            <span className="text-white font-mono font-medium">
              {replayStatus?.current_simulated_at ? replayStatus.current_simulated_at.replace('T', ' ').slice(0, 19) : 'STANDBY'}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs bg-zinc-950 border border-zinc-800 rounded px-3 py-1">
            <span className="text-zinc-400">Stream:</span>
            {sseConnected ? (
              <span className="text-emerald-400 font-medium flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                SSE LIVE
              </span>
            ) : (
              <span className="text-zinc-400 font-medium flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-500" />
                POLLING
              </span>
            )}
          </div>
        </div>
      </header>
    </>
  );
};
