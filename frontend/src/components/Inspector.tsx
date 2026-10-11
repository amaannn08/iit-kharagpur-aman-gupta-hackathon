import React from 'react';
import { CheckCircle, Layers, XCircle } from 'lucide-react';
import { RiskSignal, StressRunResult } from '../api/client';
import { WhyThisLossPanel } from './WhyThisLossPanel';
import { fmt, pct, useMetrics } from '../hooks/useMetrics';
import { Card } from './ui/Card';

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
    <Card className="flex flex-col h-[760px] p-0 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-[#ECEDEC] bg-white flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-[#E8F5EE] text-[#14532D] flex items-center justify-center">
            <Layers className="w-4 h-4 text-[#14532D]" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-[#111827]">Signal Inspector &amp; Audit</h2>
            <p className="text-[11px] text-[#6B7280]">Detailed NLP stage breakdown</p>
          </div>
        </div>
        {selectedSignal && (
          <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-[#F3F4F3] border border-[#ECEDEC] text-[#4B5563]">
            ID: {selectedSignal.signal_id.slice(0, 14)}...
          </span>
        )}
      </div>

      {selectedSignal ? (
        <div className="flex-1 p-5 space-y-4 text-xs overflow-y-auto">
          {/* Target Entity Resolution Card */}
          <div className="p-4 rounded-2xl bg-[#F9FAF9] border border-[#ECEDEC] space-y-1.5">
            <div className="text-[#6B7280] font-medium text-[11px] uppercase font-mono">
              Target Entity Resolution
            </div>
            <div className="text-base font-bold text-[#111827] flex items-center justify-between">
              <span>{selectedSignal.entity.name}</span>
              <span className="font-mono text-[#111827] font-bold bg-white px-2 py-0.5 rounded-md border border-[#ECEDEC] shadow-xs">
                {selectedSignal.entity.ticker || 'N/A'}
              </span>
            </div>
            <div className="text-[11px] text-[#6B7280] flex items-center gap-2 pt-0.5">
              <span>Scope: {selectedSignal.entity.scope}</span>
              <span>&bull;</span>
              <span className={selectedSignal.entity.resolved ? 'text-[#1F6B45] font-semibold' : 'text-[#6B7280]'}>
                {selectedSignal.entity.resolved ? '✓ Resolved by entity linker (S&P 500 universe)' : '⚠️ Unresolved'}
              </span>
            </div>
          </div>

          {/* Audit Evidence Text Box */}
          <div className="p-4 rounded-2xl bg-[#F9FAF9] border border-[#ECEDEC] space-y-2">
            <div className="text-[#6B7280] font-medium flex items-center justify-between text-[11px] uppercase font-mono">
              <span>Audit Evidence Text</span>
              <span className="font-mono text-[#9CA3AF]">
                {selectedSignal.evidence.length} highlighted span(s)
              </span>
            </div>
            <div className="p-3 rounded-xl bg-white border border-[#ECEDEC] text-[#1F2937] leading-relaxed text-xs">
              {selectedSignal.evidence.map((span, idx) => (
                <span key={idx} className="bg-[#FEF3C7] text-[#92400E] font-medium border-b-2 border-amber-400 px-1 py-0.5 rounded">
                  {span.text}
                </span>
              ))}
            </div>
          </div>

          {/* 3-Way Sentiment Probabilities */}
          <div className="p-4 rounded-2xl bg-[#F9FAF9] border border-[#ECEDEC] space-y-2">
            <div className="text-[#6B7280] font-medium flex items-center justify-between text-[11px] uppercase font-mono">
              <span>Sentiment ({selectedSignal.model_versions?.sentiment ?? 'model'})</span>
              <span className="font-mono font-bold text-[#111827]">
                Score: {selectedSignal.sentiment.score.toFixed(3)}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center font-mono">
              <div className="p-2.5 rounded-xl bg-[#E8F5EE] border border-[#7FD1A4]/40">
                <div className="text-[10px] text-[#14532D] font-bold">POSITIVE</div>
                <div className="text-sm font-bold text-[#1F6B45]">
                  {(selectedSignal.sentiment.probabilities.positive * 100).toFixed(1)}%
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-white border border-[#ECEDEC]">
                <div className="text-[10px] text-[#6B7280] font-bold">NEUTRAL</div>
                <div className="text-sm font-bold text-[#374151]">
                  {(selectedSignal.sentiment.probabilities.neutral * 100).toFixed(1)}%
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#FEE2E2] border border-red-200">
                <div className="text-[10px] text-[#DC2626] font-bold">NEGATIVE</div>
                <div className="text-sm font-bold text-[#DC2626]">
                  {(selectedSignal.sentiment.probabilities.negative * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          </div>

          {/* Event & Severity Rubric */}
          <div className="p-4 rounded-2xl bg-[#F9FAF9] border border-[#ECEDEC] space-y-2">
            <div className="text-[#6B7280] font-medium flex items-center justify-between text-[11px] uppercase font-mono">
              <span>
                Impact:{' '}
                {selectedSignal.impact.method === 'market_calibrated'
                  ? `market-calibrated decile (pred. |z| ${selectedSignal.impact.market_calibration?.predicted_abs_abnormal_z.toFixed(2)})`
                  : selectedSignal.impact.method === 'floor'
                  ? 'catastrophic-language floor'
                  : 'rubric'}
              </span>
              <span className="font-mono font-bold text-[#111827]">
                Score: {selectedSignal.impact.score}/10
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center font-mono text-[11px]">
              <div className="p-2.5 rounded-xl bg-white border border-[#ECEDEC]">
                <div className="text-[10px] text-[#9CA3AF]">EVENT BASE</div>
                <div className="text-sm font-bold text-[#111827]">
                  {selectedSignal.impact.components.event_base}
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-white border border-[#ECEDEC]">
                <div className="text-[10px] text-[#9CA3AF]">SCOPE MODIFIER</div>
                <div className="text-sm font-bold text-[#374151]">
                  +{selectedSignal.impact.components.scope}
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-white border border-[#ECEDEC]">
                <div className="text-[10px] text-[#9CA3AF]">SEVERITY BOOST</div>
                <div className="text-sm font-bold text-[#374151]">
                  +{selectedSignal.impact.components.explicit_severity}
                </div>
              </div>
            </div>
          </div>

          {/* Policy Action Gate Status */}
          <div className="p-4 rounded-2xl bg-[#F9FAF9] border border-[#ECEDEC] space-y-2">
            <div className="text-[#6B7280] font-medium text-[11px] uppercase font-mono">
              Policy Action Gate Status
            </div>
            <div>
              {selectedSignal.eligible_for_action ? (
                <div className="p-3 rounded-xl bg-[#E8F5EE] border border-[#7FD1A4] text-[#14532D] flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 font-bold text-xs">
                    <CheckCircle className="w-4 h-4 text-[#1F6B45]" />
                    Triggered Module B Wholesale Stress
                  </span>
                  <button
                    type="button"
                    onClick={onViewStressPnL}
                    className="px-3 py-1 rounded-full bg-[#14532D] text-white font-semibold text-xs hover:bg-[#1F6B45] transition-colors cursor-pointer shrink-0"
                  >
                    View Stress PnL &rarr;
                  </button>
                </div>
              ) : (
                <div className="p-3 rounded-xl bg-white border border-[#ECEDEC] text-[#4B5563]">
                  <div className="flex items-center gap-1.5 font-semibold text-xs text-[#374151]">
                    <XCircle className="w-4 h-4 text-[#9CA3AF]" />
                    Wholesale Stress Trigger Blocked
                  </div>
                  <div className="text-[11px] text-[#6B7280] mt-1">
                    Block Reasons: {selectedSignal.action_block_reasons?.join(', ') || 'Policy criteria not met.'}
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
            <div className="text-[10px] font-mono uppercase tracking-wider text-[#9CA3AF]">
              Executive Architecture Briefing
            </div>
            <h3 className="text-sm font-bold text-[#111827]">
              NLP Pipeline &amp; Stress Valuation Cascade
            </h3>
            <p className="text-[#6B7280] leading-relaxed text-[11px]">
              Every incoming financial news item or social post traverses a 5-stage deterministic pipeline before triggering downstream wholesale stress testing.
            </p>
          </div>

          <div className="space-y-2 font-mono text-[11px]">
            <div className="p-3 rounded-xl bg-[#F9FAF9] border border-[#ECEDEC] space-y-1">
              <div className="font-bold text-[#111827] flex items-center justify-between">
                <span>1. Entity Linking &amp; Role Guards</span>
                <span className="text-[#1F6B45] text-[10px]">
                  P {fmt(m?.entity_polygon?.precision)} / R {fmt(m?.entity_polygon?.recall_mentioned)}
                </span>
              </div>
              <p className="text-[#6B7280] font-sans text-[11px]">
                S&amp;P 500 universe linker with SEC CIK cross-referencing and role guards preventing false broker/rating agency attribution.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-[#F9FAF9] border border-[#ECEDEC] space-y-1">
              <div className="font-bold text-[#111827] flex items-center justify-between">
                <span>2. Continuous Sentiment Engine</span>
                <span className="text-[#1F6B45] text-[10px]">
                  Macro-F1 {fmt(m?.public_real?.sentiment?.macro_f1)}
                </span>
              </div>
              <p className="text-[#6B7280] font-sans text-[11px]">
                Local FinBERT + character/word n-gram logistic classifier producing directional sentiment calibrated in [-1.00, +1.00].
              </p>
            </div>

            <div className="p-3 rounded-xl bg-[#F9FAF9] border border-[#ECEDEC] space-y-1">
              <div className="font-bold text-[#111827] flex items-center justify-between">
                <span>3. Calibrated Event Classification</span>
                <span className="text-[#1F6B45] text-[10px]">
                  Macro-F1 {fmt(m?.public_real?.event?.macro_f1_model)}
                </span>
              </div>
              <p className="text-[#6B7280] font-sans text-[11px]">
                Isotonic-calibrated 8-class taxonomy with strict abstention thresholds choosing precision ({fmt(m?.public_real?.event?.precision_when_fired)}) over recall.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-[#F9FAF9] border border-[#ECEDEC] space-y-1">
              <div className="font-bold text-[#111827] flex items-center justify-between">
                <span>4. Market Abnormal Return Impact</span>
                <span className="text-[#1F6B45] text-[10px]">
                  Spearman &rho; {fmt(m?.market_impact?.learned_oof_spearman)}
                </span>
              </div>
              <p className="text-[#6B7280] font-sans text-[11px]">
                Gradient-boosted severity predictor validated against {m?.market_impact?.events?.toLocaleString('en-US') ?? '—'} real market reactions.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-[#F9FAF9] border border-[#ECEDEC] space-y-1">
              <div className="font-bold text-[#111827] flex items-center justify-between">
                <span>5. Automated Stress Trigger Gates</span>
                <span className="text-[#1F6B45] text-[10px]">
                  False trigger {pct(m?.pipeline?.false_trigger_rate_max_source)} (max per source)
                </span>
              </div>
              <p className="text-[#6B7280] font-sans text-[11px]">
                Action gates require impact above 7, a supported event class, confidence and novelty before stressing the funded book.
              </p>
            </div>
          </div>

          {onSelectTopSignal && (
            <button
              type="button"
              onClick={onSelectTopSignal}
              className="w-full py-2.5 rounded-full bg-[#14532D] text-white font-semibold text-xs hover:bg-[#1F6B45] transition-colors cursor-pointer shadow-sm"
            >
              Select Top Critical Signal in Stream &rarr;
            </button>
          )}
        </div>
      )}
    </Card>
  );
};
