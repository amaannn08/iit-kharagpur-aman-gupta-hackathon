import {
  Activity,
  Database,
  FileCheck,
  LineChart,
  Radio,
  Shield,
  Sparkles,
  TrendingDown,
} from 'lucide-react';
import { LiveStatusResponse, ReplayStatus } from '../api/client';
import { TabType } from '../types/navigation';

export interface SidebarNavProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  signalsCount: number;
  liveStatus: LiveStatusResponse | null;
  replayStatus: ReplayStatus | null;
  selectedScenario: string;
  onLoadScenario: (scId: string) => void;
  onAppendLive?: () => void;
}

export const SidebarNav: React.FC<SidebarNavProps> = ({
  activeTab,
  setActiveTab,
  signalsCount,
  liveStatus,
  replayStatus,
  selectedScenario,
  onLoadScenario,
  onAppendLive,
}) => {
  const navItems: { id: TabType; name: string; icon: React.ElementType; badge?: number }[] = [
    { id: 'feed', name: 'Live Signals Feed', icon: Activity, badge: signalsCount },
    { id: 'stress', name: 'Wholesale Stress', icon: TrendingDown },
    { id: 'index', name: 'Index Rebalancer', icon: LineChart },
    { id: 'playground', name: 'NLP Sandbox', icon: Sparkles },
    { id: 'overview', name: 'Datasets & Readiness', icon: Database },
    { id: 'eval', name: 'Evaluation & Governance', icon: FileCheck },
  ];

  // Derive dynamic live badge status
  const isLiveScenario = Boolean(
    selectedScenario === 'live' ||
      (replayStatus?.source_badges ?? []).includes('LIVE CAPTURE') ||
      liveStatus?.mode === 'LIVE'
  );
  const isSynthetic = Boolean(
    (replayStatus?.source_badges ?? []).includes('SYNTHETIC SCENARIO') ||
      selectedScenario === 'demo' ||
      liveStatus?.mode === 'SYNTHETIC'
  );

  let liveBadge = 'REPLAY';
  let badgeColor = 'bg-theme-bg text-theme-muted border-theme-border';

  if (isLiveScenario) {
    const lag = liveStatus?.lag_seconds;
    const alive = liveStatus?.recorder_alive ?? false;
    if (lag !== null && lag !== undefined && lag < 600 && alive) {
      liveBadge = 'LIVE';
      badgeColor = 'bg-theme-primary-tint text-theme-primary-dark border-theme-primary/40';
    } else {
      liveBadge = 'STALE';
      badgeColor = 'bg-theme-warn-bg text-theme-warn border-theme-warn/40';
    }
  } else if (isSynthetic) {
    liveBadge = 'SYNTHETIC';
    badgeColor = 'bg-theme-primary-tint text-theme-primary-dark border-theme-primary/40';
  }

  const lagText = (() => {
    if (!liveStatus?.last_fetch_at) return null;
    const lagSec = liveStatus.lag_seconds ?? 0;
    if (lagSec < 60) return 'last fetch just now';
    return `last fetch ${Math.round(lagSec / 60)} min ago`;
  })();

  return (
    <aside className="w-[268px] h-full bg-theme-card border-r border-theme-border flex flex-col justify-between p-5 select-none shrink-0 min-h-0">
      <div className="flex-1 flex flex-col space-y-6 min-h-0 overflow-hidden">
        {/* Brand / Logo */}
        <div className="flex items-center gap-3 px-2 shrink-0">
          <div className="w-9 h-9 rounded-full bg-theme-primary-fill flex items-center justify-center text-theme-on-primary shadow-sm">
            <Shield className="w-5 h-5 fill-current/20 stroke-current" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-theme-text leading-none">
              S&P Sentinel
            </h1>
            <span className="text-[10px] font-medium text-theme-muted">
              Financial Risk Dashboard
            </span>
          </div>
        </div>

        {/* MENU Section */}
        <div className="flex-1 flex flex-col space-y-1 min-h-0">
          <div className="text-[10px] font-bold tracking-wider text-theme-subtle uppercase px-3 mb-2 font-mono shrink-0">
            MENU
          </div>
          <nav className="space-y-1 overflow-y-auto flex-1 min-h-0 pr-0.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-start text-left gap-3 px-3 py-2.5 rounded-xl text-xs md:text-sm font-medium transition-all group relative cursor-pointer ${
                    isActive
                      ? 'bg-theme-primary-tint text-theme-primary-text font-bold'
                      : 'text-theme-muted hover:text-theme-text hover:bg-theme-card-hover'
                  }`}
                >
                  {/* Left indicator bar for active item */}
                  {isActive && (
                    <span className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-theme-primary-fill rounded-r" />
                  )}

                  <Icon
                    className={`w-4 h-4 shrink-0 transition-colors ${
                      isActive
                        ? 'text-theme-primary-text'
                        : 'text-theme-muted group-hover:text-theme-text'
                    }`}
                  />
                  <span className="truncate whitespace-nowrap text-left">{item.name}</span>

                  {/* Count pill on Live Signals Feed */}
                  {item.badge !== undefined && (
                    <span
                      className={`ml-auto shrink-0 px-2 py-0.5 rounded-full text-[11px] font-mono font-semibold ${
                        isActive
                          ? 'bg-theme-primary-fill text-theme-on-primary'
                          : 'bg-theme-primary-tint text-theme-primary-text'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Bottom Promo Card: "Live capture" */}
      <div className="mt-4 shrink-0 rounded-2xl bg-gradient-to-br from-theme-hero-from to-theme-hero-to text-theme-hero-text p-4 relative overflow-hidden shadow-sm">
        <svg
          className="absolute -right-6 -bottom-6 w-28 h-28 opacity-15 pointer-events-none select-none text-current"
          viewBox="0 0 100 100"
          fill="none"
        >
          <circle cx="50" cy="50" r="40" stroke="currentColor" strokeWidth="8" />
          <path d="M20 50h60" stroke="currentColor" strokeWidth="6" />
        </svg>

        <div className="relative z-10 space-y-2.5">
          <div className="flex items-center justify-between" data-testid="live-status-container">
            <span className="text-xs font-semibold text-theme-hero-subtle flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 animate-pulse text-current" />
              Live Tailer
            </span>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border ${badgeColor}`}
              data-testid="live-status-badge"
            >
              {liveBadge}
            </span>
          </div>

          <div className="text-[11px] text-theme-hero-subtle leading-tight">
            GDELT + SEC 8-K streaming ingest adapter.
          </div>

          {lagText && (
            <div
              className="text-[10px] font-mono text-theme-hero-subtle/80"
              data-testid="live-lag-text"
            >
              {lagText}
            </div>
          )}

          <button
            type="button"
            onClick={() => {
              if (isLiveScenario && onAppendLive) {
                onAppendLive();
              } else {
                onLoadScenario('live');
              }
            }}
            className="w-full mt-1 py-1.5 px-3 bg-theme-hero-btn-bg hover:bg-theme-hero-btn-hover text-theme-hero-btn-text text-xs font-semibold rounded-full shadow-sm transition-all text-center cursor-pointer"
          >
            {isLiveScenario ? 'Pull New Records' : 'Load Live Capture'}
          </button>
        </div>
      </div>
    </aside>
  );
};
