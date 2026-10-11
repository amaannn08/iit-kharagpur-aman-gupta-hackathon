import { Search, ShieldAlert } from 'lucide-react';
import { ReplayStatus } from '../api/client';

export interface TopBarProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  sseConnected: boolean;
  replayStatus: ReplayStatus | null;
}

export const TopBar: React.FC<TopBarProps> = ({
  searchQuery,
  onSearchChange,
  sseConnected,
  replayStatus,
}) => {
  // Derive dynamic current run badge
  const dynamicSourceBadge =
    (replayStatus?.source_badges ?? [])[0] ||
    (replayStatus?.scenario_id ? `SCENARIO: ${replayStatus.scenario_id.toUpperCase()}` : 'SYNTHETIC SCENARIO');

  return (
    <header className="h-18 px-6 border-b border-[#ECEDEC] bg-white flex items-center justify-between gap-4 shrink-0">
      {/* Search Input */}
      <div className="flex-1 max-w-md relative">
        <Search className="w-4 h-4 text-[#9CA3AF] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        <input
          type="text"
          placeholder="Search signals, tickers, events…"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full bg-[#F3F4F3] border border-transparent focus:border-[#7FD1A4] rounded-full pl-10 pr-12 py-2 text-xs md:text-sm text-[#111827] placeholder-[#9CA3AF] focus:outline-none transition-all"
        />
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono font-semibold text-[#9CA3AF] bg-white border border-[#ECEDEC] px-1.5 py-0.5 rounded">
          ⌘F
        </span>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Mandatory Honesty Badge (Static text for test + dynamic pill next to it) */}
        <div className="hidden lg:flex items-center gap-2 bg-[#F3F4F3] border border-[#ECEDEC] px-3 py-1 rounded-full text-xs text-[#4B5563]">
          <ShieldAlert className="w-3.5 h-3.5 text-[#1F6B45]" />
          <span className="font-semibold text-[#111827]">
            HISTORICAL REPLAY / SYNTHETIC SCENARIO
          </span>
          <span className="text-gray-300">•</span>
          <span className="px-2 py-0.5 rounded-full bg-[#E8F5EE] text-[#14532D] font-mono text-[10px] font-bold">
            {dynamicSourceBadge}
          </span>
        </div>

        {/* Stream SSE Status */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#F3F4F3] border border-[#ECEDEC] text-xs font-mono">
          <span
            className={`w-2 h-2 rounded-full ${
              sseConnected ? 'bg-[#10B981] animate-pulse' : 'bg-gray-400'
            }`}
          />
          <span className="font-medium text-[#374151]">
            {sseConnected ? 'SSE LIVE' : 'POLLING'}
          </span>
        </div>

        {/* Candidate Identity */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-[#ECEDEC]">
          <div className="hidden sm:block text-left leading-tight">
            <div className="text-xs font-bold text-[#111827]">
              Candidate: Aman Gupta (IIT Kharagpur)
            </div>
            <div className="text-[10px] text-[#6B7280] font-mono">
              Offline Localhost Evaluator
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
