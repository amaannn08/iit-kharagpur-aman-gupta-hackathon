import React from 'react';
import {
  Activity,
  Database,
  FileCheck,
  HelpCircle,
  LineChart,
  Radio,
  Settings,
  Shield,
  Sparkles,
  TrendingDown,
} from 'lucide-react';
import { LiveStatusResponse, ReplayStatus } from '../api/client';
import { TabType } from './Header';

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
  let badgeColor = 'bg-gray-100 text-gray-700 border-gray-200';

  if (isLiveScenario) {
    const lag = liveStatus?.lag_seconds;
    const alive = liveStatus?.recorder_alive ?? false;
    if (lag !== null && lag !== undefined && lag < 600 && alive) {
      liveBadge = 'LIVE';
      badgeColor = 'bg-[#E8F5EE] text-[#14532D] border-[#7FD1A4]';
    } else {
      liveBadge = 'STALE';
      badgeColor = 'bg-amber-100 text-amber-800 border-amber-200';
    }
  } else if (isSynthetic) {
    liveBadge = 'SYNTHETIC';
    badgeColor = 'bg-[#E8F5EE] text-[#14532D] border-[#7FD1A4]';
  }

  const lagText = (() => {
    if (!liveStatus?.last_fetch_at) return null;
    const lagSec = liveStatus.lag_seconds ?? 0;
    if (lagSec < 60) return 'last fetch just now';
    return `last fetch ${Math.round(lagSec / 60)} min ago`;
  })();

  return (
    <aside className="w-64 bg-white border-r border-[#ECEDEC] flex flex-col justify-between p-5 select-none shrink-0">
      <div className="space-y-6">
        {/* Brand / Logo */}
        <div className="flex items-center gap-3 px-2">
          <div className="w-9 h-9 rounded-full bg-[#14532D] flex items-center justify-center text-white shadow-sm">
            <Shield className="w-5 h-5 fill-white/20 stroke-white" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-[#111827] leading-none">
              S&P Sentinel
            </h1>
            <span className="text-[10px] font-medium text-[#6B7280]">
              Financial Risk Dashboard
            </span>
          </div>
        </div>

        {/* MENU Section */}
        <div className="space-y-1">
          <div className="text-[10px] font-bold tracking-wider text-[#9CA3AF] uppercase px-3 mb-2 font-mono">
            MENU
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs md:text-sm font-medium transition-all group relative cursor-pointer ${
                    isActive
                      ? 'bg-[#E8F5EE] text-[#14532D] font-bold'
                      : 'text-[#4B5563] hover:text-[#111827] hover:bg-[#F9FAF9]'
                  }`}
                >
                  {/* Left indicator bar for active item */}
                  {isActive && (
                    <span className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-[#14532D] rounded-r" />
                  )}

                  <div className="flex items-center gap-3 pl-1">
                    <Icon
                      className={`w-4 h-4 transition-colors ${
                        isActive
                          ? 'text-[#14532D]'
                          : 'text-[#6B7280] group-hover:text-[#111827]'
                      }`}
                    />
                    <span>{item.name}</span>
                  </div>

                  {/* Count pill on Live Signals Feed */}
                  {item.badge !== undefined && (
                    <span
                      className={`px-2 py-0.5 rounded-full text-[11px] font-mono font-semibold ${
                        isActive
                          ? 'bg-[#14532D] text-white'
                          : 'bg-[#E8F5EE] text-[#14532D]'
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

        {/* GENERAL Section */}
        <div className="space-y-1 pt-2">
          <div className="text-[10px] font-bold tracking-wider text-[#9CA3AF] uppercase px-3 mb-2 font-mono">
            GENERAL
          </div>
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-[#4B5563] hover:text-[#111827] hover:bg-[#F9FAF9] transition-colors"
          >
            <Settings className="w-4 h-4 text-[#6B7280]" />
            <span>Environment Specs</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('eval')}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-[#4B5563] hover:text-[#111827] hover:bg-[#F9FAF9] transition-colors"
          >
            <HelpCircle className="w-4 h-4 text-[#6B7280]" />
            <span>Audit &amp; Methodology</span>
          </button>
        </div>
      </div>

      {/* Bottom Promo Card: "Live capture" */}
      <div className="mt-6 rounded-2xl bg-gradient-to-br from-[#14532D] to-[#1F6B45] text-white p-4 relative overflow-hidden shadow-sm">
        <svg
          className="absolute -right-6 -bottom-6 w-28 h-28 opacity-15 pointer-events-none select-none text-white"
          viewBox="0 0 100 100"
          fill="none"
        >
          <circle cx="50" cy="50" r="40" stroke="currentColor" strokeWidth="8" />
          <path d="M20 50h60" stroke="currentColor" strokeWidth="6" />
        </svg>

        <div className="relative z-10 space-y-2.5">
          <div className="flex items-center justify-between" data-testid="live-status-container">
            <span className="text-xs font-semibold text-emerald-100 flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 animate-pulse text-emerald-300" />
              Live Tailer
            </span>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border ${badgeColor}`}
              data-testid="live-status-badge"
            >
              {liveBadge}
            </span>
          </div>

          <div className="text-[11px] text-emerald-100/90 leading-tight">
            GDELT + SEC 8-K streaming ingest adapter.
          </div>

          {lagText && (
            <div
              className="text-[10px] font-mono text-emerald-200/80"
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
            className="w-full mt-1 py-1.5 px-3 bg-white hover:bg-emerald-50 text-[#14532D] text-xs font-semibold rounded-full shadow-sm transition-all text-center cursor-pointer"
          >
            {isLiveScenario ? 'Pull New Records' : 'Load Live Capture'}
          </button>
        </div>
      </div>
    </aside>
  );
};
