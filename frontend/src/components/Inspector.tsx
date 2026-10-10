import React from 'react';
import { CheckCircle, Layers, XCircle } from 'lucide-react';
import { RiskSignal, StressRunResult } from '../api/client';
import { WhyThisLossPanel } from './WhyThisLossPanel';

export interface InspectorProps {
  selectedSignal: RiskSignal | null;
  activeStressResult: StressRunResult | null;
  onViewStressPnL: () => void;
}

export const Inspector: React.FC<InspectorProps> = ({
  selectedSignal,
  activeStressResult,
  onViewStressPnL,
}) => {
  return (
    <div className="col-span-12 lg:col-span-5 flex flex-col bg-[#111827] border border-gray-800 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-800 bg-gray-900/60 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-semibold text-gray-200">Signal Inspector & Audit</h2>
        </div>
        {selectedSignal && (
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-gray-800 text-gray-400">
            ID: {selectedSignal.signal_id.slice(0, 16)}...
          </span>
        )}
      </div>

      {selectedSignal ? (
        <div className="flex-1 p-5 space-y-4 text-xs overflow-y-auto">
          {/* Entity Card */}
          <div className="bg-[#0B0F17] p-3.5 rounded border border-gray-800 space-y-1.5">
            <div className="text-gray-400 font-medium">Target Entity Resolution</div>
            <div className="text-base font-bold text-white flex items-center justify-between">
              <span>{selectedSignal.entity.name}</span>
              <span className="font-mono text-cyan-400 font-bold">
                {selectedSignal.entity.ticker || 'N/A'}
              </span>
            </div>
            <div className="text-[11px] text-gray-400 flex items-center gap-2">
              <span>Scope: {selectedSignal.entity.scope}</span>
              <span>•</span>
              <span className={selectedSignal.entity.resolved ? 'text-emerald-400' : 'text-amber-400'}>
                {selectedSignal.entity.resolved ? '✓ Resolved by entity linker (S&P 500 universe)' : '⚠️ Unresolved'}
              </span>
            </div>
          </div>

          {/* Evidence Text Box */}
          <div className="bg-[#0B0F17] p-3.5 rounded border border-gray-800 space-y-2">
            <div className="text-gray-400 font-medium flex items-center justify-between">
              <span>Audit Evidence Text</span>
              <span className="text-[10px] font-mono text-gray-500">
                {selectedSignal.evidence.length} highlighted span(s)
              </span>
            </div>
            <div className="p-2.5 rounded bg-black/40 border border-gray-800 text-gray-200 leading-relaxed font-sans text-xs">
              {selectedSignal.evidence.map((span, idx) => (
                <span key={idx} className="bg-cyan-950/80 text-cyan-200 border-b border-cyan-500 px-0.5">
                  {span.text}
                </span>
              ))}
            </div>
          </div>

          {/* 3-Way Sentiment Probabilities */}
          <div className="bg-[#0B0F17] p-3.5 rounded border border-gray-800 space-y-2">
            <div className="text-gray-400 font-medium flex items-center justify-between">
              <span>Sentiment ({selectedSignal.model_versions?.sentiment ?? 'model'})</span>
              <span className="font-mono text-white font-bold">
                Score: {selectedSignal.sentiment.score.toFixed(3)}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center font-mono">
              <div className="p-2 rounded bg-emerald-950/30 border border-emerald-900/50">
                <div className="text-[10px] text-emerald-400">POSITIVE</div>
                <div className="text-sm font-bold text-emerald-300">
                  {(selectedSignal.sentiment.probabilities.positive * 100).toFixed(1)}%
                </div>
              </div>
              <div className="p-2 rounded bg-gray-900 border border-gray-800">
                <div className="text-[10px] text-gray-400">NEUTRAL</div>
                <div className="text-sm font-bold text-gray-300">
                  {(selectedSignal.sentiment.probabilities.neutral * 100).toFixed(1)}%
                </div>
              </div>
              <div className="p-2 rounded bg-rose-950/30 border border-rose-900/50">
                <div className="text-[10px] text-rose-400">NEGATIVE</div>
                <div className="text-sm font-bold text-rose-300">
                  {(selectedSignal.sentiment.probabilities.negative * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          </div>

          {/* Event & Severity Rubric */}
          <div className="bg-[#0B0F17] p-3.5 rounded border border-gray-800 space-y-2">
            <div className="text-gray-400 font-medium flex items-center justify-between">
              <span>
                Impact:{' '}
                {selectedSignal.impact.method === 'market_calibrated'
                  ? `market-calibrated decile (pred. |z| ${selectedSignal.impact.market_calibration?.predicted_abs_abnormal_z.toFixed(2)})`
                  : selectedSignal.impact.method === 'floor'
                    ? 'catastrophic-language floor'
                    : 'rubric'}{' '}
                · rubric components below
              </span>
              <span className="font-mono text-cyan-400 font-bold">
                Final Score: {selectedSignal.impact.score}/10
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center font-mono text-[11px]">
              <div className="p-2 rounded bg-gray-900 border border-gray-800">
                <div className="text-[10px] text-gray-500">EVENT BASE</div>
                <div className="text-sm font-bold text-white">
                  {selectedSignal.impact.components.event_base}
                </div>
              </div>
              <div className="p-2 rounded bg-gray-900 border border-gray-800">
                <div className="text-[10px] text-gray-500">SCOPE MODIFIER</div>
                <div className="text-sm font-bold text-cyan-400">
                  +{selectedSignal.impact.components.scope}
                </div>
              </div>
              <div className="p-2 rounded bg-gray-900 border border-gray-800">
                <div className="text-[10px] text-gray-500">SEVERITY BOOST</div>
                <div className="text-sm font-bold text-amber-400">
                  +{selectedSignal.impact.components.explicit_severity}
                </div>
              </div>
            </div>
          </div>

          {/* Action Eligibility & Reasons */}
          <div className="bg-[#0B0F17] p-3.5 rounded border border-gray-800 space-y-2">
            <div className="text-gray-400 font-medium">Policy Action Gate Status</div>
            <div className="flex items-center gap-2">
              {selectedSignal.eligible_for_action ? (
                <div className="p-2 rounded bg-emerald-950/60 border border-emerald-800/70 text-emerald-300 w-full flex items-center justify-between">
                  <span className="flex items-center gap-1.5 font-semibold">
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                    Triggered Module B Wholesale Stress
                  </span>
                  <button
                    onClick={onViewStressPnL}
                    className="px-2 py-1 rounded bg-emerald-800 text-white font-medium hover:bg-emerald-700 transition-colors"
                  >
                    View Stress PnL →
                  </button>
                </div>
              ) : (
                <div className="p-2 rounded bg-gray-900 border border-gray-800 text-gray-400 w-full">
                  <div className="flex items-center gap-1.5 font-semibold text-gray-300">
                    <XCircle className="w-4 h-4 text-gray-500" />
                    Wholesale Stress Trigger Blocked
                  </div>
                  <div className="text-[11px] text-gray-500 mt-1">
                    Block Reasons: {selectedSignal.action_block_reasons.join(', ') || 'Policy criteria not met.'}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Why this loss Inspector panel */}
          {activeStressResult && (
            <WhyThisLossPanel
              result={activeStressResult}
              triggerHeadline={selectedSignal.text_excerpt}
              evidenceSpan={selectedSignal.evidence?.[0]?.text}
            />
          )}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-gray-500 text-xs font-mono">
          Select a signal from the feed to inspect contract details.
        </div>
      )}
    </div>
  );
};
