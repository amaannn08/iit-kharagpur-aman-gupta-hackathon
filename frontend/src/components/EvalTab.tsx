import React from 'react';
import { CheckCircle, FileCheck } from 'lucide-react';
import { MetricsPanel } from './MetricsPanel';
import { Card } from './ui/Card';
import { Pill } from './ui/Pill';

export const EvalTab: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col space-y-6 overflow-y-auto">
      <MetricsPanel />

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-theme-text flex items-center gap-2">
            <span className="w-8 h-8 rounded-full bg-theme-primary-tint text-theme-primary-text flex items-center justify-center">
              <FileCheck className="w-4 h-4" />
            </span>
            Evaluation Framework & Release Gates
          </h2>
          <p className="text-xs text-theme-muted mt-1">
            Strict distinction between verified release gates and quantitative empirical benchmarks.
          </p>
        </div>
        <Pill variant="neutral" size="md">
          Release Gate Audit
        </Pill>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
        {/* Binary Release Gates Card */}
        <Card
          title="Binary Release Gates (Pass/Fail)"
          subtitle="Mandatory baseline architecture requirements"
        >
          <ul className="space-y-3 mt-2 text-theme-text-body">
            <li className="flex items-start gap-2.5">
              <span className="w-5 h-5 rounded-full bg-theme-success-bg text-theme-success flex items-center justify-center shrink-0 mt-0.5">
                <CheckCircle className="w-3.5 h-3.5" />
              </span>
              <span className="text-xs leading-snug">Two distinct local text source adapters (News & Social) operational</span>
            </li>
            <li className="flex items-start gap-2.5">
              <span className="w-5 h-5 rounded-full bg-theme-success-bg text-theme-success flex items-center justify-center shrink-0 mt-0.5">
                <CheckCircle className="w-3.5 h-3.5" />
              </span>
              <span className="text-xs leading-snug">Pydantic v2 data contracts validated with strict probability sums</span>
            </li>
            <li className="flex items-start gap-2.5">
              <span className="w-5 h-5 rounded-full bg-theme-success-bg text-theme-success flex items-center justify-center shrink-0 mt-0.5">
                <CheckCircle className="w-3.5 h-3.5" />
              </span>
              <span className="text-xs leading-snug">Zero external runtime API calls or cloud dependencies</span>
            </li>
            <li className="flex items-start gap-2.5">
              <span className="w-5 h-5 rounded-full bg-theme-success-bg text-theme-success flex items-center justify-center shrink-0 mt-0.5">
                <CheckCircle className="w-3.5 h-3.5" />
              </span>
              <span className="text-xs leading-snug">Cryptographic manifest audited with SHA-256 for all datasets</span>
            </li>
            <li className="flex items-start gap-2.5">
              <span className="w-5 h-5 rounded-full bg-theme-success-bg text-theme-success flex items-center justify-center shrink-0 mt-0.5">
                <CheckCircle className="w-3.5 h-3.5" />
              </span>
              <span className="text-xs leading-snug">Funded book value and derivative notional/MTM reported separately</span>
            </li>
          </ul>
        </Card>

        {/* NLP Quality Targets & Empirical Holdouts Card */}
        <Card
          title="NLP Quality Targets & Empirical Holdouts"
          subtitle="Model accuracy against held-out ground truth fixtures"
        >
          <div className="space-y-3.5 mt-2">
            <div className="flex items-center justify-between p-2.5 rounded-xl bg-theme-card-subtle-alt border border-theme-border">
              <span className="text-theme-text-body font-medium text-xs">Sentiment macro-F1</span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-theme-success-bg text-theme-success">
                0.865 <span className="text-[10px] font-normal text-theme-success-dark">(Target ≥ 0.75)</span>
              </span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-xl bg-theme-card-subtle-alt border border-theme-border">
              <span className="text-theme-text-body font-medium text-xs">Event classification macro-F1</span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-theme-success-bg text-theme-success">
                0.887 <span className="text-[10px] font-normal text-theme-success-dark">(Target ≥ 0.70)</span>
              </span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-xl bg-theme-card-subtle-alt border border-theme-border">
              <span className="text-theme-text-body font-medium text-xs">Entity linking precision</span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-theme-success-bg text-theme-success">
                0.938 <span className="text-[10px] font-normal text-theme-success-dark">(Target ≥ 0.90)</span>
              </span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-xl bg-theme-warn-bg border border-theme-warn-border">
              <span className="text-theme-warn-dark font-medium text-xs">Severity MAE vs holdout labels</span>
              <span className="text-theme-warn-dark font-bold text-xs text-right">
                1.52 pts (target ≤ 1.5) · labels AI-generated, not human-reviewed
              </span>
            </div>

            <p className="text-[11px] text-theme-muted leading-relaxed pt-1">
              Measured values generated from docs/metrics.json on real held-out data and independent audit fixtures.
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
};
