import React from 'react';
import { CheckCircle, Filter, Search } from 'lucide-react';
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
}) => {
  const filteredSignals = signals.filter((sig) => {
    if (filterEvent !== 'all' && sig.event.label !== filterEvent) return false;
    if (!showDuplicates && sig.duplicate_group_id && sig.action_block_reasons.includes('DUPLICATE_TEXT_SUPPRESSED')) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchEntity = sig.entity.name.toLowerCase().includes(q) || (sig.entity.ticker && sig.entity.ticker.toLowerCase().includes(q));
      const matchEvent = sig.event.label.toLowerCase().includes(q);
      const matchEvidence = sig.evidence.some((e) => e.text.toLowerCase().includes(q));
      if (!matchEntity && !matchEvent && !matchEvidence) return false;
    }
    return true;
  });

  return (
    <div className="col-span-12 lg:col-span-7 flex flex-col bg-[#111827] border border-gray-800 rounded-lg overflow-hidden">
      {/* Stream Toolbar */}
      <div className="p-3.5 border-b border-gray-800 bg-gray-900/60 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-1 min-w-[200px]">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Filter by entity, ticker, or event..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full bg-[#0B0F17] border border-gray-800 rounded pl-8 pr-3 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
          <div className="flex items-center gap-1.5 text-xs">
            <Filter className="w-3.5 h-3.5 text-gray-400" />
            <select
              value={filterEvent}
              onChange={(e) => onFilterEventChange(e.target.value)}
              className="bg-[#0B0F17] border border-gray-800 rounded px-2.5 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Events</option>
              <option value="CREDIT">Credit Event</option>
              <option value="MACRO">Macro</option>
              <option value="CYBER">Cyber Security</option>
              <option value="GEOPOLITICAL">Geopolitical</option>
              <option value="SUPPLY_CHAIN">Supply Chain</option>
              <option value="M_AND_A">M&amp;A</option>
              <option value="EARNINGS">Earnings</option>
              <option value="OTHER">Other / abstained</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <label className="flex items-center gap-1.5 cursor-pointer text-gray-400 select-none">
            <input
              type="checkbox"
              checked={showDuplicates}
              onChange={(e) => onShowDuplicatesChange(e.target.checked)}
              className="rounded bg-gray-800 border-gray-700 text-cyan-500 focus:ring-0"
            />
            <span>Show Duplicates</span>
          </label>
          <span className="font-mono text-cyan-400 text-xs px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800">
            {filteredSignals.length} Signals
          </span>
        </div>
      </div>

      {/* Signals List Scroll Area */}
      <div className="flex-1 p-4 space-y-3 overflow-y-auto">
        {filteredSignals.length === 0 ? (
          <div className="py-16 text-center text-gray-500 font-mono text-xs border border-dashed border-gray-800 rounded">
            No signals matching current filter criteria.
          </div>
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
                    ? 'bg-cyan-950/30 border-cyan-600/70 ring-1 ring-cyan-500/30'
                    : 'bg-[#0B0F17] border-gray-800 hover:border-gray-700'
                }`}
              >
                {/* Top Line: Source, Entity, Timestamp */}
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-1.5 py-0.5 rounded font-semibold uppercase text-[10px] ${
                        sig.source_type === 'news'
                          ? 'bg-blue-900/50 text-blue-300 border border-blue-700/40'
                          : 'bg-purple-900/50 text-purple-300 border border-purple-700/40'
                      }`}
                    >
                      {sig.source_type}
                    </span>
                    <span className="font-semibold text-white">{sig.entity.name}</span>
                    {sig.entity.ticker && (
                      <span className="font-mono text-cyan-400 text-[11px] font-bold">
                        {sig.entity.ticker}
                      </span>
                    )}
                    {isDuplicate && (
                      <span className="px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 text-[10px]">
                        DUPLICATE SUPPRESSED
                      </span>
                    )}
                  </div>
                  <span className="text-gray-500 font-mono text-[11px]">
                    {sig.simulated_at ? sig.simulated_at.replace('T', ' ').slice(0, 19) : sig.processed_at.slice(0, 19)}
                  </span>
                </div>

                {/* Middle Line: Evidence Text Snippet */}
                <p className="text-xs text-gray-300 leading-relaxed font-sans line-clamp-2">
                  {sig.text_excerpt || sig.evidence[0]?.text || 'No text snippet provided.'}
                </p>

                {/* Bottom Line: Classification, Impact, Sentiment */}
                <div className="mt-2.5 pt-2 border-t border-gray-800/60 flex flex-wrap items-center justify-between text-[11px] gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded font-mono font-medium ${
                        sig.event.abstained
                          ? 'bg-gray-800 text-gray-400'
                          : sig.event.label === 'CREDIT'
                          ? 'bg-red-950 text-red-300 border border-red-800/40'
                          : sig.event.label === 'MACRO'
                          ? 'bg-amber-950 text-amber-300 border border-amber-800/40'
                          : 'bg-blue-950 text-blue-300 border border-blue-800/40'
                      }`}
                    >
                      {sig.event.label.toUpperCase()} ({(sig.event.confidence * 100).toFixed(0)}%)
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded font-mono font-bold ${
                        sig.impact.score >= 8
                          ? 'bg-rose-950 text-rose-300 border border-rose-800/50'
                          : sig.impact.score >= 5
                          ? 'bg-amber-950 text-amber-300 border border-amber-800/50'
                          : 'bg-gray-800 text-gray-300'
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
                          : 'text-gray-400'
                      }`}
                    >
                      Sentiment: {sig.sentiment.score.toFixed(2)} ({sig.sentiment.label})
                    </span>
                    {isEligible ? (
                      <span className="text-emerald-400 font-semibold text-[10px] flex items-center gap-1 bg-emerald-950/60 border border-emerald-800/50 px-2 py-0.5 rounded">
                        <CheckCircle className="w-3 h-3" />
                        ACTION ELIGIBLE
                      </span>
                    ) : (
                      <span className="text-gray-500 text-[10px] bg-gray-900 border border-gray-800 px-2 py-0.5 rounded">
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
