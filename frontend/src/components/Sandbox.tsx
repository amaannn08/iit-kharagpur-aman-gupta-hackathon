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
      <div className="col-span-12 lg:col-span-6 flex flex-col bg-zinc-950 border border-zinc-800 rounded-lg p-5 space-y-4">
        <div className="border-b border-zinc-800 pb-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-white" />
            NLP Pipeline Sandbox & Risk Signal Generator
          </h3>
          <p className="text-xs text-zinc-400 mt-0.5">
            Type or paste raw financial text to test entity linking, sentiment, event classification, market-calibrated impact and automated stress triggers.
          </p>
        </div>

        {/* Pre-filled Scenarios */}
        <div className="space-y-1.5">
          <label className="text-xs text-zinc-400 font-medium">Test Scenario Presets:</label>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              type="button"
              onClick={() => {
                onTextChange(
                  'Apex Industrial Holdings missed its scheduled $45M coupon payment and syndicates report debt restructuring talks have collapsed, raising imminent Chapter 11 bankruptcy probability.'
                );
                onSourceChange('news');
              }}
              className="p-2 rounded bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-left text-zinc-300 hover:text-white transition-colors"
            >
              <div className="font-bold text-red-400">1. Severe Credit Default</div>
              <div className="text-[10px] text-zinc-500 truncate">$APEX missed $45M coupon</div>
            </button>

            <button
              type="button"
              onClick={() => {
                onTextChange(
                  'Federal Reserve unexpectedly raises benchmark federal funds rate by 75 bps following stubborn headline inflation data, driving SOFR swap yields sharply higher across all maturities.'
                );
                onSourceChange('news');
              }}
              className="p-2 rounded bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-left text-zinc-300 hover:text-white transition-colors"
            >
              <div className="font-bold text-zinc-200">2. Macro Rate Shock</div>
              <div className="text-[10px] text-zinc-500 truncate">Fed +75bps rate hike</div>
            </button>

            <button
              type="button"
              onClick={() => {
                onTextChange(
                  'A catastrophic fire at a primary microchip foundry halts global automotive component shipments for Vanguard Energy Corp and industrial equipment suppliers.'
                );
                onSourceChange('news');
              }}
              className="p-2 rounded bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-left text-zinc-300 hover:text-white transition-colors"
            >
              <div className="font-bold text-zinc-300">3. Supply Disruption</div>
              <div className="text-[10px] text-zinc-500 truncate">Semiconductor supply halt</div>
            </button>

            <button
              type="button"
              onClick={() => {
                onTextChange(
                  'Apex Industrial Holdings board of directors concludes routine quarterly administrative committee meeting; ordinary corporate governance procedures reaffirmed with no material changes.'
                );
                onSourceChange('news');
              }}
              className="p-2 rounded bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-left text-zinc-300 hover:text-white transition-colors"
            >
              <div className="font-bold text-zinc-400">4. Routine Governance</div>
              <div className="text-[10px] text-zinc-500 truncate">Admin meeting (Action Blocked)</div>
            </button>
          </div>
        </div>

        {/* Text Input Area */}
        <div className="flex-1 flex flex-col space-y-2">
          <div className="flex items-center justify-between text-xs">
            <label className="text-zinc-400 font-medium">Raw Input Text:</label>
            <div className="flex items-center gap-2">
              <span className="text-zinc-500">Source:</span>
              <select
                value={playgroundSource}
                onChange={(e) => onSourceChange(e.target.value)}
                className="bg-zinc-900 border border-zinc-800 rounded px-2 py-0.5 text-xs text-zinc-300"
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
            className="w-full flex-1 bg-zinc-900 border border-zinc-800 rounded p-3 text-xs text-zinc-200 placeholder-zinc-500 font-sans focus:outline-none focus:border-zinc-600 resize-none"
            placeholder="Enter news article or social post text..."
          />
        </div>

        <button
          type="button"
          onClick={onAnalyze}
          disabled={playgroundLoading}
          className="w-full py-2.5 px-4 rounded bg-white hover:bg-zinc-200 text-black font-semibold transition-colors flex items-center justify-center gap-2 disabled:opacity-50 text-xs"
        >
          {playgroundLoading ? (
            <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Process Through NLP Pipeline & Stress Engine
            </>
          )}
        </button>
      </div>

      {/* Right 6/12: Pipeline Output */}
      <div className="col-span-12 lg:col-span-6 flex flex-col bg-zinc-950 border border-zinc-800 rounded-lg p-5 space-y-4 overflow-y-auto">
        <div className="border-b border-zinc-800 pb-3 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-white" />
            Structured Risk Signal & Downstream Impact
          </h3>
          {playgroundResult && (
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-emerald-400">
              200 OK
            </span>
          )}
        </div>

        {playgroundResult ? (
          <div className="space-y-4 text-xs">
            {/* Entity & Event Badges */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-zinc-900 p-3 rounded border border-zinc-800">
                <div className="text-zinc-500 text-[10px]">RESOLVED ENTITY</div>
                <div className="text-sm font-bold text-white mt-0.5">
                  {playgroundResult.signal.entity.name}
                </div>
                <div className="text-[11px] text-zinc-400 font-mono">
                  {playgroundResult.signal.entity.ticker || 'No Ticker'} • {playgroundResult.signal.entity.scope}
                </div>
              </div>

              <div className="bg-zinc-900 p-3 rounded border border-zinc-800">
                <div className="text-zinc-500 text-[10px]">EVENT CLASSIFICATION</div>
                <div className="text-sm font-bold text-white mt-0.5 uppercase">
                  {playgroundResult.signal.event.label}
                </div>
                <div className="text-[11px] text-zinc-400 font-mono">
                  Confidence: {(playgroundResult.signal.event.confidence * 100).toFixed(0)}%
                  {playgroundResult.signal.event.abstained && ' (Abstained)'}
                </div>
              </div>
            </div>

            {/* Sentiment & Impact */}
            <div className="grid grid-cols-2 gap-3 font-mono">
              <div className="bg-zinc-900 p-3 rounded border border-zinc-800">
                <div className="text-zinc-500 text-[10px]">FINBERT SENTIMENT</div>
                <div className={`text-lg font-bold mt-0.5 ${playgroundResult.signal.sentiment.score < 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                  {playgroundResult.signal.sentiment.score.toFixed(3)}
                </div>
                <div className="text-[11px] text-zinc-400">
                  Label: {playgroundResult.signal.sentiment.label}
                </div>
              </div>

              <div className="bg-zinc-900 p-3 rounded border border-zinc-800">
                <div className="text-zinc-500 text-[10px]">IMPACT SEVERITY RUBRIC</div>
                <div className="text-lg font-bold text-white mt-0.5">
                  {playgroundResult.signal.impact.score} / 10
                </div>
                <div className="text-[11px] text-zinc-400">
                  Base: {playgroundResult.signal.impact.components.event_base} | Scope: +{playgroundResult.signal.impact.components.scope}
                </div>
              </div>
            </div>

            {/* Action Gate Policy */}
            <div className="bg-zinc-900 p-3.5 rounded border border-zinc-800">
              <div className="text-zinc-400 font-medium mb-1">Action Gate Eligibility</div>
              {playgroundResult.signal.eligible_for_action ? (
                <div className="text-emerald-400 font-semibold flex items-center gap-1.5">
                  <CheckCircle className="w-4 h-4" />
                  ELIGIBLE FOR ACTION → Automatically Triggered Wholesale Stress Run
                </div>
              ) : (
                <div className="text-zinc-400">
                  <div className="flex items-center gap-1.5 text-zinc-300 font-semibold">
                    <AlertTriangle className="w-4 h-4 text-zinc-400" />
                    ACTION BLOCKED BY POLICY
                  </div>
                  <div className="text-[11px] text-zinc-500 mt-1">
                    Reason: {playgroundResult.signal.action_block_reasons.join(', ')}
                  </div>
                </div>
              )}
            </div>

            {/* Triggered Stress Result if present */}
            {playgroundResult.stress_run && (
              <div className="bg-zinc-900 p-3.5 rounded border border-zinc-800 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="text-white font-bold flex items-center gap-1.5">
                    <TrendingDown className="w-4 h-4 text-red-400" />
                    Triggered Stress Valuation Result
                  </div>
                  <span className="font-mono text-red-400 font-bold">
                    PnL: -${Math.abs(playgroundResult.stress_run.total_pnl_usd).toLocaleString('en-US')}
                  </span>
                </div>
                <div className="text-[11px] text-zinc-400 font-mono">
                  Credit ECL Delta: +${playgroundResult.stress_run.credit_ecl_change_usd.toLocaleString('en-US')} • Market MTM Delta: ${playgroundResult.stress_run.market_mtm_change_usd.toLocaleString('en-US')}
                </div>
                <button
                  onClick={onOpenStressTab}
                  className="w-full mt-2 py-1.5 rounded bg-white hover:bg-zinc-200 text-black text-xs font-semibold transition-colors"
                >
                  Open Full Wholesale Portfolio Breakdown →
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-zinc-500 text-xs font-mono border border-dashed border-zinc-800 rounded">
            Run an analysis to inspect structured signals and stress triggers.
          </div>
        )}
      </div>
    </div>
  );
};
