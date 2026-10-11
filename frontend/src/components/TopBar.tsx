import { Moon, Search, ShieldAlert, Sun } from 'lucide-react';
import { ReplayStatus } from '../api/client';
import { useTheme } from '../hooks/useTheme';

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
  const { theme, toggleTheme } = useTheme();

  // Derive dynamic current run badge
  const dynamicSourceBadge =
    (replayStatus?.source_badges ?? [])[0] ||
    (replayStatus?.scenario_id ? `SCENARIO: ${replayStatus.scenario_id.toUpperCase()}` : 'SYNTHETIC SCENARIO');

  return (
    <header className="h-18 px-6 border-b border-theme-border bg-theme-card flex items-center justify-between gap-4 shrink-0">
      {/* Search Input */}
      <div className="flex-1 max-w-md relative">
        <Search className="w-4 h-4 text-theme-subtle absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        <input
          type="text"
          placeholder="Search signals, tickers, events…"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full bg-theme-bg border border-transparent focus:border-theme-primary rounded-full pl-10 pr-12 py-2 text-xs md:text-sm text-theme-text placeholder-theme-subtle focus:outline-none transition-all"
        />
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono font-semibold text-theme-subtle bg-theme-card border border-theme-border px-1.5 py-0.5 rounded">
          ⌘F
        </span>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Mandatory Honesty Badge (Static text for test + dynamic pill next to it) */}
        <div className="hidden lg:flex items-center gap-2 bg-theme-bg border border-theme-border px-3 py-1 rounded-full text-xs text-theme-text-secondary">
          <ShieldAlert className="w-3.5 h-3.5 text-theme-primary" />
          <span className="font-semibold text-theme-text">
            HISTORICAL REPLAY / SYNTHETIC SCENARIO
          </span>
          <span className="text-theme-border">•</span>
          <span className="px-2 py-0.5 rounded-full bg-theme-primary-tint text-theme-primary-text font-mono text-[10px] font-bold">
            {dynamicSourceBadge}
          </span>
        </div>

        {/* Stream SSE Status */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-theme-bg border border-theme-border text-xs font-mono">
          <span
            className={`w-2 h-2 rounded-full ${
              sseConnected ? 'bg-theme-success animate-pulse' : 'bg-theme-subtle'
            }`}
          />
          <span className="font-medium text-theme-text-body">
            {sseConnected ? 'SSE LIVE' : 'POLLING'}
          </span>
        </div>

        {/* Theme Toggle Button */}
        <button
          type="button"
          onClick={toggleTheme}
          aria-label="Toggle theme"
          className="p-1.5 rounded-full bg-theme-bg border border-theme-border text-theme-text-body hover:text-theme-text hover:border-theme-border-strong transition-colors cursor-pointer flex items-center justify-center"
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-theme-warn" />
          ) : (
            <Moon className="w-4 h-4 text-theme-text-body" />
          )}
        </button>

        {/* Candidate Identity */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-theme-border">
          <div className="hidden sm:block text-left leading-tight">
            <div className="text-xs font-bold text-theme-text">
              Candidate: Aman Gupta (IIT Kharagpur)
            </div>
            <div className="text-[10px] text-theme-muted font-mono">
              Offline Localhost Evaluator
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
