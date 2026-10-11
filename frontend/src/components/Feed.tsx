import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Filter,
  Play,
  Search,
  TrendingDown,
} from 'lucide-react';
import { RiskSignal } from '../api/client';
import { Card } from './ui/Card';

export interface FeedProps {
  signals: RiskSignal[];
  totalSignalsCount?: number;
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
  totalSignalsCount,
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
}) => {
  const [filterMode, setFilterMode] = useState<'all' | 'high_impact' | 'actionable'>('all');

  const highImpactCount = signals.filter((s) => s.impact.score > 7).length;
  const actionableCount = signals.filter((s) => s.eligible_for_action).length;
  const creditCount = signals.filter((s) => s.event?.label?.toUpperCase() === 'CREDIT').length;
  const macroCount = signals.filter((s) => s.event?.label?.toUpperCase() === 'MACRO').length;
  const cyberCount = signals.filter((s) => s.event?.label?.toUpperCase() === 'CYBER').length;

  const filteredSignals = signals.filter((sig) => {
    if (filterMode === 'high_impact' && sig.impact.score <= 7) return false;
    if (filterMode === 'actionable' && !sig.eligible_for_action) return false;
    if (filterEvent !== 'all' && sig.event?.label?.toUpperCase() !== filterEvent.toUpperCase()) return false;
    if (!showDuplicates && sig.duplicate_group_id && sig.action_block_reasons?.includes('DUPLICATE_TEXT_SUPPRESSED')) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchEntity =
        sig.entity?.name?.toLowerCase().includes(q) ||
        (sig.entity?.ticker && sig.entity.ticker.toLowerCase().includes(q));
      const matchEvent = sig.event?.label?.toLowerCase().includes(q);
      const matchEvidence = sig.evidence?.some((e) => e.text.toLowerCase().includes(q));
      const matchText = sig.text_excerpt?.toLowerCase().includes(q);
      if (!matchEntity && !matchEvent && !matchEvidence && !matchText) return false;
    }
    return true;
  });

  return (
    <Card className="flex flex-col h-[760px] p-0 overflow-hidden">
      {/* Stream Toolbar & Search */}
      <div className="p-4 border-b border-theme-border bg-theme-card space-y-3 shrink-0">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 flex-1 min-w-[200px]">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-theme-subtle absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Filter by entity, ticker, or text..."
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                className="w-full bg-theme-bg border border-transparent focus:border-theme-primary-light rounded-full pl-9 pr-3 py-1.5 text-xs text-theme-text placeholder-theme-subtle focus:outline-none transition-all"
              />
            </div>
            <div className="flex items-center gap-1.5 text-xs shrink-0">
              <Filter className="w-3.5 h-3.5 text-theme-muted" />
              <select
                value={filterEvent}
                onChange={(e) => onFilterEventChange(e.target.value)}
                className="bg-theme-bg border border-theme-border rounded-full px-3 py-1.5 text-xs text-theme-text-body focus:outline-none cursor-pointer"
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
            <label className="flex items-center gap-1.5 cursor-pointer text-theme-text-secondary select-none text-[11px]">
              <input
                type="checkbox"
                checked={showDuplicates}
                onChange={(e) => onShowDuplicatesChange(e.target.checked)}
                className="rounded text-theme-primary focus:ring-0 accent-theme-primary"
              />
              <span>Show Suppressed Dups</span>
            </label>
            <span className="font-mono text-theme-primary-text text-xs px-2.5 py-0.5 rounded-full bg-theme-primary-tint border border-theme-primary/40 font-semibold">
              {totalSignalsCount && totalSignalsCount > signals.length
                ? `Showing latest ${filteredSignals.length} of ${totalSignalsCount} Signals`
                : `${filteredSignals.length} Signals`}
            </span>
          </div>
        </div>

        {/* Quick Filter Action Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto text-[11px] font-medium pt-0.5">
          <button
            type="button"
            onClick={() => {
              setFilterMode('all');
              onFilterEventChange('all');
            }}
            className={`px-3 py-1 rounded-full transition-all cursor-pointer whitespace-nowrap ${
              filterMode === 'all' && filterEvent === 'all'
                ? 'bg-theme-primary-fill text-theme-on-primary shadow-xs font-semibold'
                : 'bg-theme-bg text-theme-text-secondary hover:text-theme-text'
            }`}
          >
            All ({totalSignalsCount && totalSignalsCount > signals.length ? `latest ${signals.length} of ${totalSignalsCount}` : signals.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterMode('high_impact')}
            className={`px-3 py-1 rounded-full transition-all cursor-pointer whitespace-nowrap ${
              filterMode === 'high_impact'
                ? 'bg-theme-primary-fill text-theme-on-primary shadow-xs font-semibold'
                : 'bg-theme-bg text-theme-text-secondary hover:text-theme-text'
            }`}
          >
            High Impact &gt; 7 ({highImpactCount})
          </button>
          <button
            type="button"
            onClick={() => setFilterMode('actionable')}
            className={`px-3 py-1 rounded-full transition-all cursor-pointer whitespace-nowrap ${
              filterMode === 'actionable'
                ? 'bg-theme-primary-fill text-theme-on-primary shadow-xs font-semibold'
                : 'bg-theme-bg text-theme-text-secondary hover:text-theme-text'
            }`}
          >
            Actionable Triggers ({actionableCount})
          </button>
          <button
            type="button"
            onClick={() => onFilterEventChange('CREDIT')}
            className={`px-3 py-1 rounded-full transition-all cursor-pointer whitespace-nowrap ${
              filterEvent === 'CREDIT'
                ? 'bg-theme-primary-fill text-theme-on-primary shadow-xs font-semibold'
                : 'bg-theme-bg text-theme-text-secondary hover:text-theme-text'
            }`}
          >
            Credit ({creditCount})
          </button>
          <button
            type="button"
            onClick={() => onFilterEventChange('MACRO')}
            className={`px-3 py-1 rounded-full transition-all cursor-pointer whitespace-nowrap ${
              filterEvent === 'MACRO'
                ? 'bg-theme-primary-fill text-theme-on-primary shadow-xs font-semibold'
                : 'bg-theme-bg text-theme-text-secondary hover:text-theme-text'
            }`}
          >
            Macro ({macroCount})
          </button>
          {cyberCount > 0 && (
            <button
              type="button"
              onClick={() => onFilterEventChange('CYBER')}
              className={`px-3 py-1 rounded-full transition-all cursor-pointer whitespace-nowrap ${
                filterEvent === 'CYBER'
                  ? 'bg-theme-primary-fill text-theme-on-primary shadow-xs font-semibold'
                  : 'bg-theme-bg text-theme-text-secondary hover:text-theme-text'
              }`}
            >
              Cyber ({cyberCount})
            </button>
          )}
        </div>
      </div>

      {/* Signals List Scroll Area */}
      <div className="flex-1 p-3.5 space-y-2.5 overflow-y-auto">
        {filteredSignals.length === 0 ? (
          signals.length > 0 ? (
            <div className="py-16 text-center text-theme-muted text-xs border border-dashed border-theme-border rounded-2xl bg-theme-card-subtle p-6 space-y-3">
              <AlertTriangle className="w-6 h-6 text-theme-subtle mx-auto" />
              <div className="text-sm font-semibold text-theme-text">
                No signals match current filters
              </div>
              <p className="max-w-sm mx-auto text-theme-muted">
                No signals match '{searchQuery || filterEvent}'. Clear search or change filters to view active items.
              </p>
              <button
                type="button"
                onClick={() => {
                  onSearchChange('');
                  onFilterEventChange('all');
                  setFilterMode('all');
                }}
                className="px-4 py-1.5 rounded-full bg-theme-primary-fill text-theme-on-primary font-semibold text-xs hover:bg-theme-primary-hover transition-colors cursor-pointer"
              >
                Reset All Filters ({totalSignalsCount && totalSignalsCount > signals.length ? `latest ${signals.length} of ${totalSignalsCount}` : signals.length} Signals Available)
              </button>
            </div>
          ) : (
            <div className="py-10 px-6 border border-theme-border rounded-2xl bg-theme-card space-y-5 text-center">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-theme-primary-tint text-theme-primary-text text-xs font-medium">
                <Activity className="w-3.5 h-3.5 text-theme-primary" />
                Replay Engine Ready
              </div>
              <h3 className="text-base font-bold text-theme-text">
                Activate Real-Time Risk Ingestion
              </h3>
              <p className="text-xs text-theme-muted max-w-md mx-auto">
                Select an audited offline scenario below or click Start Replay to stream structured risk signals and stress triggers.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
                <button
                  type="button"
                  onClick={() => {
                    if (onLoadScenario) onLoadScenario('demo');
                    if (onPlay) setTimeout(onPlay, 200);
                  }}
                  className="p-3.5 rounded-2xl border border-theme-border hover:border-theme-primary-fill hover:bg-theme-primary-tint/40 transition-all cursor-pointer space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-theme-text flex items-center gap-1.5">
                      <Play className="w-3 h-3 fill-theme-primary-fill text-theme-primary-fill" />
                      Synthetic Demo Scenario
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-theme-bg text-theme-text-secondary">
                      1,000+ Records
                    </span>
                  </div>
                  <p className="text-[11px] text-theme-muted">
                    Severe Chapter 11 default ($APEX), Fed rate shock (+75bps), microchip supply halt.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    if (onLoadScenario) onLoadScenario('polygon_2023');
                    if (onPlay) setTimeout(onPlay, 200);
                  }}
                  className="p-3.5 rounded-2xl border border-theme-border hover:border-theme-primary-fill hover:bg-theme-primary-tint/40 transition-all cursor-pointer space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-theme-text flex items-center gap-1.5">
                      <TrendingDown className="w-3 h-3 text-theme-loss" />
                      Polygon Real News (2023)
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-theme-bg text-theme-text-secondary">
                      5,548 Articles
                    </span>
                  </div>
                  <p className="text-[11px] text-theme-muted">
                    Real audited 2023 financial news across S&amp;P 500 universe with market returns.
                  </p>
                </button>
              </div>
            </div>
          )
        ) : (
          filteredSignals.map((sig) => {
            const isSelected = selectedSignal?.signal_id === sig.signal_id;
            const isDuplicate =
              sig.duplicate_group_id &&
              sig.action_block_reasons?.includes('DUPLICATE_TEXT_SUPPRESSED');
            const isEligible = sig.eligible_for_action;

            return (
              <div
                key={sig.signal_id}
                onClick={() => onSelectSignal(sig)}
                className={`p-3.5 rounded-2xl border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-theme-primary-tint/60 border-theme-primary-fill shadow-xs ring-1 ring-theme-primary-fill/30'
                    : 'bg-theme-card border-theme-border hover:border-theme-border-strong hover:bg-theme-card-subtle'
                }`}
              >
                {/* Top Line: Source, Entity, Timestamp */}
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded-full font-semibold uppercase text-[10px] bg-theme-bg text-theme-text-body border border-theme-border">
                      {sig.source_type}
                    </span>
                    <span className="font-bold text-theme-text">{sig.entity.name}</span>
                    {sig.entity.ticker && (
                      <span className="font-mono text-theme-text text-[11px] font-bold bg-theme-bg px-1.5 py-0.5 rounded border border-theme-border">
                        {sig.entity.ticker}
                      </span>
                    )}
                    {isDuplicate && (
                      <span className="px-2 py-0.5 rounded-full bg-theme-card-subtle text-theme-muted text-[10px]">
                        DUPLICATE SUPPRESSED
                      </span>
                    )}
                  </div>
                  <span className="text-theme-subtle font-mono text-[11px]">
                    {sig.simulated_at
                      ? sig.simulated_at.replace('T', ' ').slice(0, 19)
                      : sig.processed_at.slice(0, 19)}
                  </span>
                </div>

                {/* Middle Line: Evidence Text Snippet */}
                <p className="text-xs text-theme-text-body leading-relaxed line-clamp-2">
                  {sig.text_excerpt || sig.evidence[0]?.text || 'No text snippet provided.'}
                </p>

                {/* Bottom Line: Classification, Impact, Sentiment */}
                <div className="mt-2.5 pt-2 border-t border-theme-border flex flex-wrap items-center justify-between text-[11px] gap-2">
                  <div className="flex items-center gap-2">
                    {/* Exact text CREDIT (88%) tested by vitest! */}
                    <span
                      className={`px-2.5 py-0.5 rounded-full font-mono font-medium ${
                        sig.event.abstained
                          ? 'bg-theme-card-subtle text-theme-muted border border-theme-border'
                          : sig.event.label?.toUpperCase() === 'CREDIT'
                          ? 'bg-theme-loss-bg text-theme-loss border border-theme-loss/30 font-semibold'
                          : 'bg-theme-primary-tint text-theme-primary-text border border-theme-primary/40 font-semibold'
                      }`}
                    >
                      {sig.event.label?.toUpperCase()} ({(sig.event.confidence * 100).toFixed(0)}%)
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full font-mono font-bold ${
                        sig.impact.score >= 8
                          ? 'bg-theme-loss-bg text-theme-loss border border-theme-loss/30'
                          : sig.impact.score >= 5
                          ? 'bg-theme-warn-bg text-theme-warn border border-theme-warn/30'
                          : 'bg-theme-bg text-theme-text-body border border-theme-border'
                      }`}
                    >
                      Impact: {sig.impact.score}/10
                    </span>
                  </div>

                  <div className="flex items-center gap-3">
                    <span
                      className={`font-mono ${
                        sig.sentiment.score < -0.3
                          ? 'text-theme-loss font-semibold'
                          : sig.sentiment.score > 0.3
                          ? 'text-theme-primary-text font-semibold'
                          : 'text-theme-muted'
                      }`}
                    >
                      Sentiment: {sig.sentiment.score.toFixed(2)} ({sig.sentiment.label})
                    </span>

                    {/* Exact text ACTION ELIGIBLE tested by vitest! */}
                    {isEligible ? (
                      <span className="text-theme-primary-text font-bold text-[10px] flex items-center gap-1 bg-theme-primary-tint border border-theme-primary/40 px-2.5 py-0.5 rounded-full">
                        <CheckCircle className="w-3 h-3 text-theme-primary" />
                        ACTION ELIGIBLE
                      </span>
                    ) : (
                      <span className="text-theme-subtle text-[10px] bg-theme-card-subtle border border-theme-border px-2 py-0.5 rounded-full">
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
    </Card>
  );
};
