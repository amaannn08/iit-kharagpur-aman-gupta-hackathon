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
      <div className="bg-amber-950/80 border-b border-amber-600/40 px-4 py-1.5 flex items-center justify-between text-xs shrink-0">
        <div className="flex items-center gap-2 text-amber-300 font-semibold tracking-wide">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
          <span className="uppercase px-1.5 py-0.5 rounded bg-amber-500/20 border border-amber-400/30">
            HISTORICAL REPLAY / SYNTHETIC SCENARIO
          </span>
          <span className="text-amber-200/80 font-normal hidden sm:inline">
            100% Offline Localhost Execution • Zero External APIs • Verified Datasets
          </span>
        </div>
        <div className="flex items-center gap-3 text-amber-200/70">
          <span>Candidate: Aman Gupta (IIT Kharagpur)</span>
          <span className="hidden md:inline">•</span>
          <span className="font-mono bg-amber-900/60 px-2 py-0.5 rounded border border-amber-700/40 text-amber-200 hidden md:inline">
            {(replayStatus?.source_badges ?? []).join(' + ') || 'No replay loaded'}
          </span>
        </div>
      </div>

      {/* Main Terminal Header */}
      <header className="bg-[#111827] border-b border-gray-800 px-6 py-3 flex flex-wrap items-center justify-between gap-4 shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${sseConnected ? 'bg-emerald-400 animate-pulse' : 'bg-cyan-400'}`} />
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              S&P Sentinel
              <span className="text-xs px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono">
                RISK TERMINAL
              </span>
            </h1>
          </div>
          <span className="text-gray-600 text-sm hidden sm:inline">|</span>
          <nav className="flex items-center gap-1 overflow-x-auto">
            <button
              onClick={() => setActiveTab('feed')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'feed'
                  ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-700/50'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
              }`}
            >
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              Live Signals Feed
            </button>
            <button
              onClick={() => setActiveTab('stress')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'stress'
                  ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-700/50'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
              }`}
            >
              <TrendingDown className="w-3.5 h-3.5 text-rose-400" />
              Wholesale Stress
            </button>
            <button
              onClick={() => setActiveTab('index')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'index'
                  ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-700/50'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
              }`}
            >
              <LineChart className="w-3.5 h-3.5 text-violet-400" />
              Index Rebalancer (Module A)
            </button>
            <button
              onClick={() => setActiveTab('playground')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'playground'
                  ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-700/50'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              NLP Sandbox
            </button>
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'overview'
                  ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-700/50'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
              }`}
            >
              <Database className="w-3.5 h-3.5 text-blue-400" />
              Datasets & Readiness
            </button>
            <button
              onClick={() => setActiveTab('eval')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === 'eval'
                  ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-700/50'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
              }`}
            >
              <FileCheck className="w-3.5 h-3.5 text-emerald-400" />
              Evaluation & Governance
            </button>
          </nav>
        </div>

        {/* Backend Status & SSE Pill */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs bg-gray-900 border border-gray-800 rounded-full px-3 py-1">
            <span className="text-gray-400">Replay Clock:</span>
            <span className="text-cyan-300 font-mono">
              {replayStatus?.current_simulated_at ? replayStatus.current_simulated_at.replace('T', ' ').slice(0, 19) : 'STANDBY'}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs bg-gray-900 border border-gray-800 rounded-full px-3 py-1">
            <span className="text-gray-400">Stream:</span>
            {sseConnected ? (
              <span className="text-emerald-400 font-medium flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                SSE LIVE
              </span>
            ) : (
              <span className="text-amber-400 font-medium flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                POLLING
              </span>
            )}
          </div>
        </div>
      </header>
    </>
  );
};
