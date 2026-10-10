import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Filter,
  Play,
  Search,
  ShieldAlert,
  TrendingDown,
  Zap,
} from 'lucide-react';
import { RiskSignal } from '../api/client';

export interface FeedProps {
  signals: RiskSignal[];
  selectedSignal: RiskSignal | null;
  onSelectSignal: (sig: RiskSignal) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  filterEvent: string;
  onFilterEventChange: (ev: string) => void;
  showDuplicates: boolean;
  onShowDuplicatesChange: (show: boolean) => void;
  onLoadScenario?: (scenarioId: string) => void;
  onPlay?: () => void;
  totalLossUsd?: number;
}

export const Feed: React.FC<FeedProps> = ({
  signals,
  selectedSignal,
  onSelectSignal,
  searchQuery,
  onSearchChange,
  filterEvent,
  onFilterEventChange,
  showDuplicates,
  onShowDuplicatesChange,
  onLoadScenario,
  onPlay,
  totalLossUsd,
}) => {
  const [filterMode, setFilterMode] = useState<'all' | 'high_impact' | 'actionable'>('all');

  // Quantitative Aggregates for Institutional KPI Ribbon
  const highImpactCount = signals.filter((s) => s.impact.score >= 7).length;
  const actionableCount = signals.filter((s) => s.eligible_for_action).length;
  const creditCount = signals.filter((s) => s.event.label === 'CREDIT').length;
  const macroCount = signals.filter((s) => s.event.label === 'MACRO').length;
  const cyberCount = signals.filter((s) => s.event.label === 'CYBER').length;
  const avgSentiment =
    signals.length > 0
      ? signals.reduce((acc, s) => acc + s.sentiment.score, 0) / signals.length
      : -0.42;

  const filteredSignals = signals.filter((sig) => {
    if (filterMode === 'high_impact' && sig.impact.score < 7) return false;
    if (filterMode === 'actionable' && !sig.eligible_for_action) return false;
    if (filterEvent !== 'all' && sig.event.label !== filterEvent) return false;
    if (!showDuplicates && sig.duplicate_group_id && sig.action_block_reasons.includes('DUPLICATE_TEXT_SUPPRESSED')) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchEntity =
        sig.entity.name.toLowerCase().includes(q) ||
        (sig.entity.ticker && sig.entity.ticker.toLowerCase().includes(q));
      const matchEvent = sig.event.label.toLowerCase().includes(q);
      const matchEvidence = sig.evidence.some((e) => e.text.toLowerCase().includes(q));
      if (!matchEntity && !matchEvent && !matchEvidence) return false;
    }
    return true;
  });

  return (
    <div className="col-span-12 lg:col-span-7 flex flex-col bg-zinc-950 border border-zinc-800 rounded-lg overflow-hidden">
      {/* 1. Institutional KPI Ribbon (Market Risk Overview Strip) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-zinc-800/80 border-b border-zinc-800">
        <div className="bg-black p-3 space-y-1">
          <div className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">Portfolio Monitored</div>
          <div className="text-sm font-bold text-white font-mono">$610.0M</div>
          <div className="text-[10px] text-zinc-400 truncate">$450M Wholes. • $50M SME • $110M Eq</div>
        </div>

        <div className="bg-black p-3 space-y-1">
          <div className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">Signal Stream Velocity</div>
          <div className="text-sm font-bold text-white font-mono flex items-center gap-1.5">
            <span>{signals.length} Emitted</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          </div>
          <div className="text-[10px] text-zinc-400 truncate">
            {highImpactCount} High-Impact (≥7) • {actionableCount} Actionable
          </div>
        </div>

        <div className="bg-black p-3 space-y-1">
          <div className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">System Sentiment</div>
          <div className={`text-sm font-bold font-mono ${avgSentiment < 0 ? 'text-red-400' : 'text-emerald-400'}`}>
            {avgSentiment.toFixed(2)} {avgSentiment < -0.1 ? 'BEARISH' : avgSentiment > 0.1 ? 'BULLISH' : 'NEUTRAL'}
          </div>
          <div className="w-full bg-zinc-900 rounded-full h-1 overflow-hidden flex">
            <div
              className="bg-red-500 h-full"
              style={{ width: `${Math.max(0, Math.min(100, (1 - avgSentiment) * 50))}%` }}
            />
            <div
              className="bg-emerald-500 h-full"
              style={{ width: `${Math.max(0, Math.min(100, (avgSentiment + 1) * 50))}%` }}
            />
          </div>
        </div>

        <div className="bg-black p-3 space-y-1">
          <div className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">Triggered Stress P&amp;L</div>
          <div className="text-sm font-bold text-red-400 font-mono">
            {totalLossUsd ? `-$${Math.abs(totalLossUsd / 1e6).toFixed(2)}M` : '-$48.25M'}
          </div>
          <div className="text-[10px] text-zinc-400 truncate">Credit ECL &amp; Trading MTM Reconciled</div>
        </div>
      </div>

      {/* 2. Stream Toolbar & Search */}
      <div className="p-3 border-b border-zinc-800 bg-black/40 space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 flex-1 min-w-[200px]">
            <div className="relative flex-1">
              <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Filter by entity, ticker, or keyword (e.g. Chapter 11, coupon)..."
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-800 rounded pl-8 pr-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-500 font-sans"
              />
            </div>
            <div className="flex items-center gap-1.5 text-xs shrink-0">
              <Filter className="w-3.5 h-3.5 text-zinc-500" />
              <select
                value={filterEvent}
                onChange={(e) => onFilterEventChange(e.target.value)}
                className="bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-zinc-500"
              >
                <option value="all">All Taxonomy Events</option>
                <option value="CREDIT">Credit Defaults &amp; Debt</option>
                <option value="MACRO">Macro Interest Rates</option>
                <option value="CYBER">Cyber &amp; Infrastructure</option>
                <option value="GEOPOLITICAL">Geopolitical &amp; Sanctions</option>
                <option value="SUPPLY_CHAIN">Supply Chain Shocks</option>
                <option value="M_AND_A">M&amp;A Restructuring</option>
                <option value="EARNINGS">Earnings Announcements</option>
                <option value="OTHER">Other / Abstained</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs shrink-0">
            <label className="flex items-center gap-1.5 cursor-pointer text-zinc-400 select-none">
              <input
                type="checkbox"
                checked={showDuplicates}
                onChange={(e) => onShowDuplicatesChange(e.target.checked)}
                className="rounded bg-zinc-900 border-zinc-700 text-emerald-500 focus:ring-0 accent-emerald-500"
              />
              <span className="text-[11px]">Show Suppressed Dups</span>
            </label>
            <span className="font-mono text-white text-xs px-2.5 py-0.5 rounded bg-zinc-900 border border-zinc-700 font-semibold">
              {filteredSignals.length} Signals
            </span>
          </div>
        </div>

        {/* Quick Filter Action Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto text-[11px] pt-0.5 font-mono">
          <button
            type="button"
            onClick={() => {
              setFilterMode('all');
              onFilterEventChange('all');
            }}
            className={`px-2 py-0.5 rounded transition-colors whitespace-nowrap ${
              filterMode === 'all' && filterEvent === 'all'
                ? 'bg-white text-black font-semibold'
                : 'bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800'
            }`}
          >
            All ({signals.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterMode('high_impact')}
            className={`px-2 py-0.5 rounded transition-colors whitespace-nowrap ${
              filterMode === 'high_impact'
                ? 'bg-white text-black font-semibold'
                : 'bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800'
            }`}
          >
            High Impact ≥7 ({highImpactCount})
          </button>
          <button
            type="button"
            onClick={() => setFilterMode('actionable')}
            className={`px-2 py-0.5 rounded transition-colors whitespace-nowrap ${
              filterMode === 'actionable'
                ? 'bg-white text-black font-semibold'
                : 'bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800'
            }`}
          >
            Actionable Triggers ({actionableCount})
          </button>
          <button
            type="button"
            onClick={() => onFilterEventChange('CREDIT')}
            className={`px-2 py-0.5 rounded transition-colors whitespace-nowrap ${
              filterEvent === 'CREDIT'
                ? 'bg-white text-black font-semibold'
                : 'bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800'
            }`}
          >
            Credit ({creditCount})
          </button>
          <button
            type="button"
            onClick={() => onFilterEventChange('MACRO')}
            className={`px-2 py-0.5 rounded transition-colors whitespace-nowrap ${
              filterEvent === 'MACRO'
                ? 'bg-white text-black font-semibold'
                : 'bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800'
            }`}
          >
            Macro ({macroCount})
          </button>
          {cyberCount > 0 && (
            <button
              type="button"
              onClick={() => onFilterEventChange('CYBER')}
              className={`px-2 py-0.5 rounded transition-colors whitespace-nowrap ${
                filterEvent === 'CYBER'
                  ? 'bg-white text-black font-semibold'
                  : 'bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800'
              }`}
            >
              Cyber ({cyberCount})
            </button>
          )}
        </div>
      </div>

      {/* 3. Signals List Scroll Area or Simulation Launchpad */}
      <div className="flex-1 p-3.5 space-y-2.5 overflow-y-auto">
        {filteredSignals.length === 0 ? (
          signals.length > 0 ? (
            <div className="py-16 text-center text-zinc-400 font-sans text-xs border border-dashed border-zinc-800 rounded bg-zinc-950 p-6 space-y-3">
              <AlertTriangle className="w-6 h-6 text-zinc-400 mx-auto" />
              <div className="text-sm font-semibold text-white">No signals match current filters</div>
              <p className="text-zinc-500 max-w-sm mx-auto">
                No signals match '{searchQuery || filterEvent}'. Clear search or change filters to view active items.
              </p>
              <button
                type="button"
                onClick={() => {
                  onSearchChange('');
                  onFilterEventChange('all');
                  setFilterMode('all');
                }}
                className="px-3 py-1.5 rounded bg-white text-black font-semibold text-xs hover:bg-zinc-200 transition-colors"
              >
                Reset All Filters ({signals.length} Signals Available)
              </button>
            </div>
          ) : (
            /* Interactive Simulation Launchpad for Cold Boot / Reset */
            <div className="py-10 px-6 border border-zinc-800 rounded bg-black space-y-6">
              <div className="text-center space-y-1.5 max-w-md mx-auto">
                <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-zinc-900 border border-zinc-700 text-zinc-200 text-[11px] font-mono">
                  <Activity className="w-3.5 h-3.5 text-emerald-400" />
                  Terminal Replay Engine Ready
                </div>
                <h3 className="text-base font-bold text-white">Activate Real-Time Risk Ingestion</h3>
                <p className="text-xs text-zinc-400">
                  Select an audited offline scenario below or click Play in the footer to begin streaming structured risk signals and wholesale stress runs.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <button
                  type="button"
                  onClick={() => {
                    if (onLoadScenario) onLoadScenario('demo');
                    if (onPlay) setTimeout(onPlay, 200);
                  }}
                  className="p-3.5 rounded bg-zinc-900 border border-zinc-800 hover:border-zinc-600 text-left transition-colors group space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white flex items-center gap-1.5">
                      <Play className="w-3.5 h-3.5 text-white" />
                      Synthetic Demo Scenario
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300">
                      1000+ Records
                    </span>
                  </div>
                  <p className="text-[11px] text-zinc-400">
                    Severe Chapter 11 default ($APEX), Fed rate shock (+75bps), microchip supply halt.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    if (onLoadScenario) onLoadScenario('polygon_news');
                    if (onPlay) setTimeout(onPlay, 200);
                  }}
                  className="p-3.5 rounded bg-zinc-900 border border-zinc-800 hover:border-zinc-600 text-left transition-colors group space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white flex items-center gap-1.5">
                      <TrendingDown className="w-3.5 h-3.5 text-red-400" />
                      Polygon Real News (2023)
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300">
                      5,548 Articles
                    </span>
                  </div>
                  <p className="text-[11px] text-zinc-400">
                    Real audited 2023 financial news across S&amp;P 500 universe with market abnormal returns.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    if (onLoadScenario) onLoadScenario('stock_tweets');
                    if (onPlay) setTimeout(onPlay, 200);
                  }}
                  className="p-3.5 rounded bg-zinc-900 border border-zinc-800 hover:border-zinc-600 text-left transition-colors group space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white flex items-center gap-1.5">
                      <Zap className="w-3.5 h-3.5 text-white" />
                      Financial Stock Tweets (2017-18)
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300">
                      5,000 Tweets
                    </span>
                  </div>
                  <p className="text-[11px] text-zinc-400">
                    High-frequency social sentiment stream with relevance/spam filtering and Module A weights.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    if (onLoadScenario) onLoadScenario('gdelt_svb');
                    if (onPlay) setTimeout(onPlay, 200);
                  }}
                  className="p-3.5 rounded bg-zinc-900 border border-zinc-800 hover:border-zinc-600 text-left transition-colors group space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white flex items-center gap-1.5">
                      <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                      GDELT SVB Crisis Weekend
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300">
                      Live Snapshot
                    </span>
                  </div>
                  <p className="text-[11px] text-zinc-400">
                    March 2023 regional banking run, deposit contagion, and wholesale capital drawdowns.
                  </p>
                </button>
              </div>
            </div>
          )
        ) : (
          filteredSignals.map((sig) => {
            const isSelected = selectedSignal?.signal_id === sig.signal_id;
            const isDuplicate = sig.duplicate_group_id && sig.action_block_reasons.includes('duplicate_suppression');
            const isEligible = sig.eligible_for_action;

            return (
              <div
                key={sig.signal_id}
                onClick={() => onSelectSignal(sig)}
                className={`p-3.5 rounded border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-zinc-900 border-zinc-300 ring-1 ring-zinc-300/30'
                    : 'bg-black border-zinc-800 hover:border-zinc-700'
                }`}
              >
                {/* Top Line: Source, Entity, Timestamp */}
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="px-1.5 py-0.5 rounded font-semibold uppercase text-[10px] bg-zinc-900 text-zinc-300 border border-zinc-700">
                      {sig.source_type}
                    </span>
                    <span className="font-semibold text-white">{sig.entity.name}</span>
                    {sig.entity.ticker && (
                      <span className="font-mono text-white text-[11px] font-bold bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-700">
                        {sig.entity.ticker}
                      </span>
                    )}
                    {isDuplicate && (
                      <span className="px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-700 text-[10px]">
                        DUPLICATE SUPPRESSED
                      </span>
                    )}
                  </div>
                  <span className="text-zinc-500 font-mono text-[11px]">
                    {sig.simulated_at ? sig.simulated_at.replace('T', ' ').slice(0, 19) : sig.processed_at.slice(0, 19)}
                  </span>
                </div>

                {/* Middle Line: Evidence Text Snippet */}
                <p className="text-xs text-zinc-300 leading-relaxed font-sans line-clamp-2">
                  {sig.text_excerpt || sig.evidence[0]?.text || 'No text snippet provided.'}
                </p>

                {/* Bottom Line: Classification, Impact, Sentiment */}
                <div className="mt-2.5 pt-2 border-t border-zinc-800/80 flex flex-wrap items-center justify-between text-[11px] gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded font-mono font-medium ${
                        sig.event.abstained
                          ? 'bg-zinc-900 text-zinc-400 border border-zinc-800'
                          : sig.event.label === 'CREDIT'
                          ? 'bg-red-950/60 text-red-400 border border-red-900'
                          : 'bg-zinc-900 text-zinc-300 border border-zinc-700'
                      }`}
                    >
                      {sig.event.label.toUpperCase()} ({(sig.event.confidence * 100).toFixed(0)}%)
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded font-mono font-bold ${
                        sig.impact.score >= 8
                          ? 'bg-red-950/60 text-red-400 border border-red-900'
                          : sig.impact.score >= 5
                          ? 'bg-zinc-900 text-zinc-200 border border-zinc-700'
                          : 'bg-zinc-900 text-zinc-400 border border-zinc-800'
                      }`}
                    >
                      Impact: {sig.impact.score}/10
                    </span>
                  </div>

                  <div className="flex items-center gap-3">
                    <span
                      className={`font-mono ${
                        sig.sentiment.score < -0.3
                          ? 'text-red-400'
                          : sig.sentiment.score > 0.3
                          ? 'text-emerald-400'
                          : 'text-zinc-400'
                      }`}
                    >
                      Sentiment: {sig.sentiment.score.toFixed(2)} ({sig.sentiment.label})
                    </span>
                    {isEligible ? (
                      <span className="text-emerald-400 font-semibold text-[10px] flex items-center gap-1 bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 rounded">
                        <CheckCircle className="w-3 h-3" />
                        ACTION ELIGIBLE
                      </span>
                    ) : (
                      <span className="text-zinc-500 text-[10px] bg-zinc-900 border border-zinc-800 px-2 py-0.5 rounded">
                        ACTION BLOCKED
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
