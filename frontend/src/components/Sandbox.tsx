import React from 'react';
import { AlertTriangle, CheckCircle, Layers, Sparkles, TrendingDown } from 'lucide-react';
import { AnalyzeResponse } from '../api/client';
import { Card } from './ui/Card';
import { Pill } from './ui/Pill';
import { PillButton } from './ui/PillButton';

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
      <div className="col-span-12 lg:col-span-6 flex flex-col">
        <Card className="flex-1 flex flex-col space-y-4">
          <div className="border-b border-theme-border pb-3">
            <h3 className="text-sm font-bold text-theme-text flex items-center gap-2">
              <span className="w-7 h-7 rounded-full bg-theme-primary-tint text-theme-primary-text flex items-center justify-center">
                <Sparkles className="w-4 h-4" />
              </span>
              NLP Pipeline Sandbox & Risk Signal Generator
            </h3>
            <p className="text-xs text-theme-muted mt-1 leading-relaxed">
              Type or paste raw financial text to test entity linking, sentiment, event classification, market-calibrated impact and automated stress triggers.
            </p>
          </div>

          {/* Test Scenario Presets */}
          <div className="space-y-1.5">
            <label className="text-xs text-theme-text-secondary font-semibold">Test Scenario Presets:</label>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => {
                  onTextChange(
                    'Apex Industrial Holdings missed its scheduled $45M coupon payment and syndicates report debt restructuring talks have collapsed, raising imminent Chapter 11 bankruptcy probability.'
                  );
                  onSourceChange('news');
                }}
                className="p-2.5 rounded-xl bg-theme-card-subtle-alt border border-theme-border hover:border-theme-primary/40 hover:bg-theme-bg text-left transition-all cursor-pointer"
              >
                <div className="font-bold text-theme-loss">1. Severe Credit Default</div>
                <div className="text-[10px] text-theme-muted truncate mt-0.5">$APEX missed $45M coupon</div>
              </button>

              <button
                type="button"
                onClick={() => {
                  onTextChange(
                    'Federal Reserve unexpectedly raises benchmark federal funds rate by 75 bps following stubborn headline inflation data, driving SOFR swap yields sharply higher across all maturities.'
                  );
                  onSourceChange('news');
                }}
                className="p-2.5 rounded-xl bg-theme-card-subtle-alt border border-theme-border hover:border-theme-primary/40 hover:bg-theme-bg text-left transition-all cursor-pointer"
              >
                <div className="font-bold text-theme-text">2. Macro Rate Shock</div>
                <div className="text-[10px] text-theme-muted truncate mt-0.5">Fed +75bps rate hike</div>
              </button>

              <button
                type="button"
                onClick={() => {
                  onTextChange(
                    'A catastrophic fire at a primary microchip foundry halts global automotive component shipments for Vanguard Energy Corp and industrial equipment suppliers.'
                  );
                  onSourceChange('news');
                }}
                className="p-2.5 rounded-xl bg-theme-card-subtle-alt border border-theme-border hover:border-theme-primary/40 hover:bg-theme-bg text-left transition-all cursor-pointer"
              >
                <div className="font-bold text-theme-text">3. Supply Disruption</div>
                <div className="text-[10px] text-theme-muted truncate mt-0.5">Semiconductor supply halt</div>
              </button>

              <button
                type="button"
                onClick={() => {
                  onTextChange(
                    'Apex Industrial Holdings board of directors concludes routine quarterly administrative committee meeting; ordinary corporate governance procedures reaffirmed with no material changes.'
                  );
                  onSourceChange('news');
                }}
                className="p-2.5 rounded-xl bg-theme-card-subtle-alt border border-theme-border hover:border-theme-primary/40 hover:bg-theme-bg text-left transition-all cursor-pointer"
              >
                <div className="font-bold text-theme-muted">4. Routine Governance</div>
                <div className="text-[10px] text-theme-subtle truncate mt-0.5">Admin meeting (Action Blocked)</div>
              </button>
            </div>
          </div>

          {/* Text Input Area */}
          <div className="flex-1 flex flex-col space-y-2">
            <div className="flex items-center justify-between text-xs">
              <label className="text-theme-text-secondary font-semibold">Raw Input Text:</label>
              <div className="flex items-center gap-2">
                <span className="text-theme-muted">Source:</span>
                <select
                  value={playgroundSource}
                  onChange={(e) => onSourceChange(e.target.value)}
                  className="bg-theme-card-subtle-alt border border-theme-border rounded-full px-3 py-1 text-xs text-theme-text font-medium focus:outline-none focus:border-theme-primary"
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
              className="w-full flex-1 bg-theme-card-subtle-alt border border-theme-border rounded-xl p-3.5 text-xs text-theme-text placeholder-theme-subtle font-sans focus:outline-none focus:border-theme-primary focus:bg-theme-card resize-none transition-colors"
              placeholder="Enter news article or social post text..."
            />
          </div>

          <PillButton
            variant="primary"
            onClick={onAnalyze}
            disabled={playgroundLoading}
            className="w-full justify-center py-2.5"
          >
            {playgroundLoading ? (
              <div className="w-4 h-4 border-2 border-theme-on-primary border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Process Through NLP Pipeline & Stress Engine
              </>
            )}
          </PillButton>
        </Card>
      </div>

      {/* Right 6/12: Pipeline Output */}
      <div className="col-span-12 lg:col-span-6 flex flex-col overflow-y-auto">
        <Card className="flex-1 flex flex-col space-y-4">
          <div className="border-b border-theme-border pb-3 flex items-center justify-between">
            <h3 className="text-sm font-bold text-theme-text flex items-center gap-2">
              <span className="w-7 h-7 rounded-full bg-theme-border-subtle text-theme-text-body flex items-center justify-center">
                <Layers className="w-4 h-4" />
              </span>
              Structured Risk Signal & Downstream Impact
            </h3>
            {playgroundResult && (
              <Pill variant="success" size="sm">
                200 OK
              </Pill>
            )}
          </div>

          {playgroundResult ? (
            <div className="space-y-4 text-xs">
              {/* Entity & Event Badges */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-theme-card-subtle-alt p-3.5 rounded-xl border border-theme-border">
                  <div className="text-theme-muted text-[10px] font-bold uppercase tracking-wider">RESOLVED ENTITY</div>
                  <div className="text-sm font-bold text-theme-text mt-1">
                    {playgroundResult.signal.entity.name}
                  </div>
                  <div className="text-[11px] text-theme-muted font-mono mt-0.5">
                    {playgroundResult.signal.entity.ticker || 'No Ticker'} • {playgroundResult.signal.entity.scope}
                  </div>
                </div>

                <div className="bg-theme-card-subtle-alt p-3.5 rounded-xl border border-theme-border">
                  <div className="text-theme-muted text-[10px] font-bold uppercase tracking-wider">EVENT CLASSIFICATION</div>
                  <div className="text-sm font-bold text-theme-text mt-1 uppercase">
                    {playgroundResult.signal.event.label}
                  </div>
                  <div className="text-[11px] text-theme-muted font-mono mt-0.5">
                    Confidence: {(playgroundResult.signal.event.confidence * 100).toFixed(0)}%
                    {playgroundResult.signal.event.abstained && ' (Abstained)'}
                  </div>
                </div>
              </div>

              {/* Sentiment & Impact */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-theme-card-subtle-alt p-3.5 rounded-xl border border-theme-border">
                  <div className="text-theme-muted text-[10px] font-bold uppercase tracking-wider">FINBERT SENTIMENT</div>
                  <div className={`text-xl font-bold mt-1 ${playgroundResult.signal.sentiment.score < 0 ? 'text-theme-loss' : 'text-theme-success'}`}>
                    {playgroundResult.signal.sentiment.score.toFixed(3)}
                  </div>
                  <div className="text-[11px] text-theme-muted mt-0.5">
                    Label: <span className="font-semibold text-theme-text">{playgroundResult.signal.sentiment.label}</span>
                  </div>
                </div>

                <div className="bg-theme-card-subtle-alt p-3.5 rounded-xl border border-theme-border">
                  <div className="text-theme-muted text-[10px] font-bold uppercase tracking-wider">IMPACT SEVERITY RUBRIC</div>
                  <div className="text-xl font-bold text-theme-text mt-1">
                    {playgroundResult.signal.impact.score} / 10
                  </div>
                  <div className="text-[11px] text-theme-muted mt-0.5 font-mono">
                    Base: {playgroundResult.signal.impact.components.event_base} | Scope: +{playgroundResult.signal.impact.components.scope}
                  </div>
                </div>
              </div>

              {/* Action Gate Policy */}
              <div className="bg-theme-card-subtle-alt p-3.5 rounded-xl border border-theme-border">
                <div className="text-theme-text-secondary font-semibold mb-1">Action Gate Eligibility</div>
                {playgroundResult.signal.eligible_for_action ? (
                  <div className="text-theme-success font-semibold flex items-center gap-1.5">
                    <CheckCircle className="w-4 h-4 text-theme-success" />
                    ELIGIBLE FOR ACTION → Automatically Triggered Wholesale Stress Run
                  </div>
                ) : (
                  <div>
                    <div className="flex items-center gap-1.5 text-theme-loss font-semibold">
                      <AlertTriangle className="w-4 h-4 text-theme-loss" />
                      ACTION BLOCKED BY POLICY
                    </div>
                    <div className="text-[11px] text-theme-muted mt-1">
                      Reason: {playgroundResult.signal.action_block_reasons.join(', ')}
                    </div>
                  </div>
                )}
              </div>

              {/* Triggered Stress Result if present */}
              {playgroundResult.stress_run && (
                <div className="bg-theme-loss-bg-alt p-4 rounded-xl border border-theme-loss-bg space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="text-theme-loss-dark font-bold flex items-center gap-1.5">
                      <TrendingDown className="w-4 h-4 text-theme-loss" />
                      Triggered Stress Valuation Result
                    </div>
                    <span className="font-mono text-theme-loss font-bold text-sm">
                      PnL: -${Math.abs(playgroundResult.stress_run.total_pnl_usd).toLocaleString('en-US')}
                    </span>
                  </div>
                  <div className="text-[11px] text-theme-loss-deeper font-mono">
                    Credit ECL Delta: +${playgroundResult.stress_run.credit_ecl_change_usd.toLocaleString('en-US')} • Market MTM Delta: ${playgroundResult.stress_run.market_mtm_change_usd.toLocaleString('en-US')}
                  </div>
                  <PillButton
                    variant="primary"
                    size="sm"
                    onClick={onOpenStressTab}
                    className="w-full mt-2 justify-center"
                  >
                    Open Full Wholesale Portfolio Breakdown →
                  </PillButton>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 min-h-[220px] flex items-center justify-center text-theme-muted text-xs font-medium border border-dashed border-theme-border rounded-xl bg-theme-card-subtle-alt/50">
              Run an analysis to inspect structured signals and stress triggers.
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
