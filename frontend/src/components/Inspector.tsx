import React from 'react';
import { CheckCircle, Layers, XCircle } from 'lucide-react';
import { RiskSignal, StressRunResult } from '../api/client';
import { WhyThisLossPanel } from './WhyThisLossPanel';
import { fmt, pct, useMetrics } from '../hooks/useMetrics';

export interface InspectorProps {
  selectedSignal: RiskSignal | null;
  activeStressResult: StressRunResult | null;
  onViewStressPnL: () => void;
  onSelectTopSignal?: () => void;
}

export const Inspector: React.FC<InspectorProps> = ({
  selectedSignal,
  activeStressResult,
  onViewStressPnL,
  onSelectTopSignal,
}) => {
  const m = useMetrics();
  return (
    <div className="col-span-12 lg:col-span-5 flex flex-col bg-zinc-950 border border-zinc-800 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-zinc-800 bg-black/60 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-white" />
          <h2 className="text-sm font-semibold text-zinc-200">Signal Inspector & Audit</h2>
        </div>
        {selectedSignal && (
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">
            ID: {selectedSignal.signal_id.slice(0, 16)}...
          </span>
        )}
      </div>

      {selectedSignal ? (
        <div className="flex-1 p-5 space-y-4 text-xs overflow-y-auto">
          {/* Entity Card */}
          <div className="bg-black p-3.5 rounded border border-zinc-800 space-y-1.5">
            <div className="text-zinc-400 font-medium">Target Entity Resolution</div>
            <div className="text-base font-bold text-white flex items-center justify-between">
              <span>{selectedSignal.entity.name}</span>
              <span className="font-mono text-white font-bold bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-700">
                {selectedSignal.entity.ticker || 'N/A'}
              </span>
            </div>
            <div className="text-[11px] text-zinc-400 flex items-center gap-2">
              <span>Scope: {selectedSignal.entity.scope}</span>
              <span>•</span>
              <span className={selectedSignal.entity.resolved ? 'text-emerald-400' : 'text-zinc-400'}>
                {selectedSignal.entity.resolved ? '✓ Resolved by entity linker (S&P 500 universe)' : '⚠️ Unresolved'}
              </span>
            </div>
          </div>

          {/* Evidence Text Box */}
          <div className="bg-black p-3.5 rounded border border-zinc-800 space-y-2">
            <div className="text-zinc-400 font-medium flex items-center justify-between">
              <span>Audit Evidence Text</span>
              <span className="text-[10px] font-mono text-zinc-500">
                {selectedSignal.evidence.length} highlighted span(s)
              </span>
            </div>
            <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800 text-zinc-200 leading-relaxed font-sans text-xs">
              {selectedSignal.evidence.map((span, idx) => (
                <span key={idx} className="bg-zinc-800 text-white font-medium border-b-2 border-white px-1">
                  {span.text}
                </span>
              ))}
            </div>
          </div>

          {/* 3-Way Sentiment Probabilities */}
          <div className="bg-black p-3.5 rounded border border-zinc-800 space-y-2">
            <div className="text-zinc-400 font-medium flex items-center justify-between">
              <span>Sentiment ({selectedSignal.model_versions?.sentiment ?? 'model'})</span>
              <span className="font-mono text-white font-bold">
                Score: {selectedSignal.sentiment.score.toFixed(3)}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center font-mono">
              <div className="p-2 rounded bg-emerald-950/40 border border-emerald-900/60">
                <div className="text-[10px] text-emerald-400">POSITIVE</div>
                <div className="text-sm font-bold text-emerald-300">
                  {(selectedSignal.sentiment.probabilities.positive * 100).toFixed(1)}%
                </div>
              </div>
              <div className="p-2 rounded bg-zinc-900 border border-zinc-800">
                <div className="text-[10px] text-zinc-400">NEUTRAL</div>
                <div className="text-sm font-bold text-zinc-300">
                  {(selectedSignal.sentiment.probabilities.neutral * 100).toFixed(1)}%
                </div>
              </div>
              <div className="p-2 rounded bg-red-950/40 border border-red-900/60">
                <div className="text-[10px] text-red-400">NEGATIVE</div>
                <div className="text-sm font-bold text-red-300">
                  {(selectedSignal.sentiment.probabilities.negative * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          </div>

          {/* Event & Severity Rubric */}
          <div className="bg-black p-3.5 rounded border border-zinc-800 space-y-2">
            <div className="text-zinc-400 font-medium flex items-center justify-between">
              <span>
                Impact:{' '}
                {selectedSignal.impact.method === 'market_calibrated'
                  ? `market-calibrated decile (pred. |z| ${selectedSignal.impact.market_calibration?.predicted_abs_abnormal_z.toFixed(2)})`
                  : selectedSignal.impact.method === 'floor'
                    ? 'catastrophic-language floor'
                    : 'rubric'}{' '}
                · rubric components below
              </span>
              <span className="font-mono text-white font-bold">
                Final Score: {selectedSignal.impact.score}/10
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center font-mono text-[11px]">
              <div className="p-2 rounded bg-zinc-900 border border-zinc-800">
                <div className="text-[10px] text-zinc-500">EVENT BASE</div>
                <div className="text-sm font-bold text-white">
                  {selectedSignal.impact.components.event_base}
                </div>
              </div>
              <div className="p-2 rounded bg-zinc-900 border border-zinc-800">
                <div className="text-[10px] text-zinc-500">SCOPE MODIFIER</div>
                <div className="text-sm font-bold text-zinc-200">
                  +{selectedSignal.impact.components.scope}
                </div>
              </div>
              <div className="p-2 rounded bg-zinc-900 border border-zinc-800">
                <div className="text-[10px] text-zinc-500">SEVERITY BOOST</div>
                <div className="text-sm font-bold text-zinc-200">
                  +{selectedSignal.impact.components.explicit_severity}
                </div>
              </div>
            </div>
          </div>

          {/* Action Eligibility & Reasons */}
          <div className="bg-black p-3.5 rounded border border-zinc-800 space-y-2">
            <div className="text-zinc-400 font-medium">Policy Action Gate Status</div>
            <div className="flex items-center gap-2">
              {selectedSignal.eligible_for_action ? (
                <div className="p-2 rounded bg-emerald-950/60 border border-emerald-800/70 text-emerald-300 w-full flex items-center justify-between">
                  <span className="flex items-center gap-1.5 font-semibold">
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                    Triggered Module B Wholesale Stress
                  </span>
                  <button
                    onClick={onViewStressPnL}
                    className="px-2.5 py-1 rounded bg-white text-black font-semibold hover:bg-zinc-200 transition-colors"
                  >
                    View Stress PnL →
                  </button>
                </div>
              ) : (
                <div className="p-2 rounded bg-zinc-900 border border-zinc-800 text-zinc-400 w-full">
                  <div className="flex items-center gap-1.5 font-semibold text-zinc-300">
                    <XCircle className="w-4 h-4 text-zinc-500" />
                    Wholesale Stress Trigger Blocked
                  </div>
                  <div className="text-[11px] text-zinc-500 mt-1">
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
        /* Executive Pipeline Architecture Briefing (when no signal is selected) */
        <div className="flex-1 p-5 space-y-4 text-xs overflow-y-auto">
          <div className="space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">Executive Architecture Briefing</div>
            <h3 className="text-sm font-bold text-white">NLP Pipeline &amp; Stress Valuation Cascade</h3>
            <p className="text-zinc-400 leading-relaxed text-[11px]">
              Every incoming financial news item or social post traverses a 5-stage deterministic pipeline before triggering downstream wholesale stress testing.
            </p>
          </div>

          <div className="space-y-2 font-mono text-[11px]">
            <div className="p-3 rounded bg-black border border-zinc-800 space-y-1">
              <div className="font-bold text-white flex items-center justify-between">
                <span>1. Entity Linking &amp; Role Guards</span>
                <span className="text-emerald-400 text-[10px]">P {fmt(m?.entity_polygon?.precision)} / R {fmt(m?.entity_polygon?.recall_mentioned)}</span>
              </div>
              <p className="text-zinc-400 font-sans text-[11px]">
                S&amp;P 500 universe linker with SEC CIK cross-referencing and role guards preventing false broker/rating agency attribution.
              </p>
            </div>

            <div className="p-3 rounded bg-black border border-zinc-800 space-y-1">
              <div className="font-bold text-white flex items-center justify-between">
                <span>2. Continuous Sentiment Engine</span>
                <span className="text-emerald-400 text-[10px]">Macro-F1 {fmt(m?.public_real?.sentiment?.macro_f1)}</span>
              </div>
              <p className="text-zinc-400 font-sans text-[11px]">
                Local FinBERT + character/word n-gram logistic classifier producing directional sentiment calibrated in [-1.00, +1.00].
              </p>
            </div>

            <div className="p-3 rounded bg-black border border-zinc-800 space-y-1">
              <div className="font-bold text-white flex items-center justify-between">
                <span>3. Calibrated Event Classification</span>
                <span className="text-emerald-400 text-[10px]">Macro-F1 {fmt(m?.public_real?.event?.macro_f1_model)}</span>
              </div>
              <p className="text-zinc-400 font-sans text-[11px]">
                Isotonic-calibrated 8-class taxonomy with strict abstention thresholds choosing precision ({fmt(m?.public_real?.event?.precision_when_fired)}) over recall on ambiguous inputs.
              </p>
            </div>

            <div className="p-3 rounded bg-black border border-zinc-800 space-y-1">
              <div className="font-bold text-white flex items-center justify-between">
                <span>4. Market Abnormal Return Impact</span>
                <span className="text-emerald-400 text-[10px]">Spearman ρ {fmt(m?.market_impact?.learned_oof_spearman)}</span>
              </div>
              <p className="text-zinc-400 font-sans text-[11px]">
                Gradient-boosted severity predictor validated against {m?.market_impact?.events?.toLocaleString('en-US') ?? '—'} real market reactions, mapped to an explainable 1-10 severity rubric.
              </p>
            </div>

            <div className="p-3 rounded bg-black border border-zinc-800 space-y-1">
              <div className="font-bold text-white flex items-center justify-between">
                <span>5. Automated Stress Trigger Gates</span>
                <span className="text-emerald-400 text-[10px]">False trigger {pct(m?.pipeline?.false_trigger_rate_max_source)} (max per source)</span>
              </div>
              <p className="text-zinc-400 font-sans text-[11px]">
                Action gates require impact above 7, a supported event class, confidence and novelty before stressing the funded book and re-weighting the index.
              </p>
            </div>
          </div>

          {onSelectTopSignal && (
            <button
              type="button"
              onClick={onSelectTopSignal}
              className="w-full py-2.5 rounded bg-white text-black font-semibold text-xs hover:bg-zinc-200 transition-colors"
            >
              Select Top Critical Signal in Stream →
            </button>
          )}
        </div>
      )}
    </div>
  );
};
