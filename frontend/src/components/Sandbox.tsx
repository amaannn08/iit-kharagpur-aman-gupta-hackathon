import React from 'react';
import { AlertTriangle, CheckCircle, Layers, Sparkles, TrendingDown } from 'lucide-react';
import { AnalyzeResponse } from '../api/client';

export interface SandboxProps {
  playgroundText: string;
  onTextChange: (text: string) => void;
  playgroundSource: string;
  onSourceChange: (source: string) => void;
  playgroundLoading: boolean;
  playgroundResult: AnalyzeResponse | null;
  onAnalyze: () => void;
  onOpenStressTab: () => void;
}

export const Sandbox: React.FC<SandboxProps> = ({
  playgroundText,
  onTextChange,
  playgroundSource,
  onSourceChange,
  playgroundLoading,
  playgroundResult,
  onAnalyze,
  onOpenStressTab,
}) => {
  return (
    <div className="flex-1 grid grid-cols-12 gap-6 overflow-hidden">
      {/* Left 6/12: Text Input & Presets */}
      <div className="col-span-12 lg:col-span-6 flex flex-col bg-[#111827] border border-gray-800 rounded-lg p-5 space-y-4">
        <div className="border-b border-gray-800 pb-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            NLP Pipeline Sandbox & Risk Signal Generator
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Type or paste raw financial text to test entity linking, sentiment, event classification, market-calibrated impact and automated stress triggers.
          </p>
        </div>

        {/* Pre-filled Scenarios */}
        <div className="space-y-1.5">
          <label className="text-xs text-gray-400 font-medium">Test Scenario Presets:</label>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              type="button"
              onClick={() => {
                onTextChange(
                  'Apex Industrial Holdings missed its scheduled $45M coupon payment and syndicates report debt restructuring talks have collapsed, raising imminent Chapter 11 bankruptcy probability.'
                );
                onSourceChange('news');
              }}
              className="p-2 rounded bg-[#0B0F17] border border-gray-800 hover:border-rose-700 text-left text-gray-300 hover:text-white transition-colors"
            >
              <div className="font-bold text-rose-400">1. Severe Credit Default</div>
              <div className="text-[10px] text-gray-500 truncate">$APEX missed $45M coupon</div>
            </button>

            <button
              type="button"
              onClick={() => {
                onTextChange(
                  'Federal Reserve unexpectedly raises benchmark federal funds rate by 75 bps following stubborn headline inflation data, driving SOFR swap yields sharply higher across all maturities.'
                );
                onSourceChange('news');
              }}
              className="p-2 rounded bg-[#0B0F17] border border-gray-800 hover:border-amber-700 text-left text-gray-300 hover:text-white transition-colors"
            >
              <div className="font-bold text-amber-400">2. Macro Rate Shock</div>
              <div className="text-[10px] text-gray-500 truncate">Fed +75bps rate hike</div>
            </button>

            <button
              type="button"
              onClick={() => {
                onTextChange(
                  'A catastrophic fire at a primary microchip foundry halts global automotive component shipments for Vanguard Energy Corp and industrial equipment suppliers.'
                );
                onSourceChange('news');
              }}
              className="p-2 rounded bg-[#0B0F17] border border-gray-800 hover:border-blue-700 text-left text-gray-300 hover:text-white transition-colors"
            >
              <div className="font-bold text-blue-400">3. Supply Disruption</div>
              <div className="text-[10px] text-gray-500 truncate">Semiconductor supply halt</div>
            </button>

            <button
              type="button"
              onClick={() => {
                onTextChange(
                  'Apex Industrial Holdings board of directors concludes routine quarterly administrative committee meeting; ordinary corporate governance procedures reaffirmed with no material changes.'
                );
                onSourceChange('news');
              }}
              className="p-2 rounded bg-[#0B0F17] border border-gray-800 hover:border-gray-600 text-left text-gray-300 hover:text-white transition-colors"
            >
              <div className="font-bold text-gray-400">4. Routine Governance</div>
              <div className="text-[10px] text-gray-500 truncate">Admin meeting (Action Blocked)</div>
            </button>
          </div>
        </div>

        {/* Text Input Area */}
        <div className="flex-1 flex flex-col space-y-2">
          <div className="flex items-center justify-between text-xs">
            <label className="text-gray-400 font-medium">Raw Input Text:</label>
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Source:</span>
              <select
                value={playgroundSource}
                onChange={(e) => onSourceChange(e.target.value)}
                className="bg-[#0B0F17] border border-gray-800 rounded px-2 py-0.5 text-xs text-gray-300"
              >
                <option value="news">News</option>
                <option value="social">Social Media</option>
              </select>
            </div>
          </div>
          <textarea
            value={playgroundText}
            onChange={(e) => onTextChange(e.target.value)}
            rows={6}
            className="w-full flex-1 bg-[#0B0F17] border border-gray-800 rounded p-3 text-xs text-gray-200 placeholder-gray-500 font-sans focus:outline-none focus:border-cyan-500 resize-none"
            placeholder="Enter news article or social post text..."
          />
        </div>

        <button
          type="button"
          onClick={onAnalyze}
          disabled={playgroundLoading}
          className="w-full py-2.5 px-4 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-semibold transition-colors flex items-center justify-center gap-2 disabled:opacity-50 text-xs"
        >
          {playgroundLoading ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Process Through NLP Pipeline & Stress Engine
            </>
          )}
        </button>
      </div>

      {/* Right 6/12: Pipeline Output */}
      <div className="col-span-12 lg:col-span-6 flex flex-col bg-[#111827] border border-gray-800 rounded-lg p-5 space-y-4 overflow-y-auto">
        <div className="border-b border-gray-800 pb-3 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            Structured Risk Signal & Downstream Impact
          </h3>
          {playgroundResult && (
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-gray-800 text-emerald-400">
              200 OK
            </span>
          )}
        </div>

        {playgroundResult ? (
          <div className="space-y-4 text-xs">
            {/* Entity & Event Badges */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-[#0B0F17] p-3 rounded border border-gray-800">
                <div className="text-gray-500 text-[10px]">RESOLVED ENTITY</div>
                <div className="text-sm font-bold text-white mt-0.5">
                  {playgroundResult.signal.entity.name}
                </div>
                <div className="text-[11px] text-cyan-400 font-mono">
                  {playgroundResult.signal.entity.ticker || 'No Ticker'} • {playgroundResult.signal.entity.scope}
                </div>
              </div>

              <div className="bg-[#0B0F17] p-3 rounded border border-gray-800">
                <div className="text-gray-500 text-[10px]">EVENT CLASSIFICATION</div>
                <div className="text-sm font-bold text-amber-400 mt-0.5 uppercase">
                  {playgroundResult.signal.event.label}
                </div>
                <div className="text-[11px] text-gray-400 font-mono">
                  Confidence: {(playgroundResult.signal.event.confidence * 100).toFixed(0)}%
                  {playgroundResult.signal.event.abstained && ' (Abstained)'}
                </div>
              </div>
            </div>

            {/* Sentiment & Impact */}
            <div className="grid grid-cols-2 gap-3 font-mono">
              <div className="bg-[#0B0F17] p-3 rounded border border-gray-800">
                <div className="text-gray-500 text-[10px]">FINBERT SENTIMENT</div>
                <div className="text-lg font-bold text-rose-400 mt-0.5">
                  {playgroundResult.signal.sentiment.score.toFixed(3)}
                </div>
                <div className="text-[11px] text-gray-400">
                  Label: {playgroundResult.signal.sentiment.label}
                </div>
              </div>

              <div className="bg-[#0B0F17] p-3 rounded border border-gray-800">
                <div className="text-gray-500 text-[10px]">IMPACT SEVERITY RUBRIC</div>
                <div className="text-lg font-bold text-cyan-400 mt-0.5">
                  {playgroundResult.signal.impact.score} / 10
                </div>
                <div className="text-[11px] text-gray-400">
                  Base: {playgroundResult.signal.impact.components.event_base} | Scope: +{playgroundResult.signal.impact.components.scope}
                </div>
              </div>
            </div>

            {/* Action Gate Policy */}
            <div className="bg-[#0B0F17] p-3.5 rounded border border-gray-800">
              <div className="text-gray-400 font-medium mb-1">Action Gate Eligibility</div>
              {playgroundResult.signal.eligible_for_action ? (
                <div className="text-emerald-400 font-semibold flex items-center gap-1.5">
                  <CheckCircle className="w-4 h-4" />
                  ELIGIBLE FOR ACTION → Automatically Triggered Wholesale Stress Run
                </div>
              ) : (
                <div className="text-gray-400">
                  <div className="flex items-center gap-1.5 text-amber-400 font-semibold">
                    <AlertTriangle className="w-4 h-4" />
                    ACTION BLOCKED BY POLICY
                  </div>
                  <div className="text-[11px] text-gray-500 mt-1">
                    Reason: {playgroundResult.signal.action_block_reasons.join(', ')}
                  </div>
                </div>
              )}
            </div>

            {/* Triggered Stress Result if present */}
            {playgroundResult.stress_run && (
              <div className="bg-[#0B0F17] p-3.5 rounded border border-cyan-800/60 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="text-cyan-300 font-bold flex items-center gap-1.5">
                    <TrendingDown className="w-4 h-4 text-rose-400" />
                    Triggered Stress Valuation Result
                  </div>
                  <span className="font-mono text-rose-400 font-bold">
                    PnL: -${Math.abs(playgroundResult.stress_run.total_pnl_usd).toLocaleString('en-US')}
                  </span>
                </div>
                <div className="text-[11px] text-gray-400 font-mono">
                  Credit ECL Delta: +${playgroundResult.stress_run.credit_ecl_change_usd.toLocaleString('en-US')} • Market MTM Delta: ${playgroundResult.stress_run.market_mtm_change_usd.toLocaleString('en-US')}
                </div>
                <button
                  onClick={onOpenStressTab}
                  className="w-full mt-2 py-1.5 rounded bg-cyan-900/60 hover:bg-cyan-800 text-cyan-200 text-xs font-semibold transition-colors"
                >
                  Open Full Wholesale Portfolio Breakdown →
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500 text-xs font-mono border border-dashed border-gray-800 rounded">
            Run an analysis to inspect structured signals and stress triggers.
          </div>
        )}
      </div>
    </div>
  );
};
