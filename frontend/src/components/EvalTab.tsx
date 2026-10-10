import React from 'react';
import { CheckCircle, FileCheck } from 'lucide-react';
import { MetricsPanel } from './MetricsPanel';

export const EvalTab: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col bg-[#111827] border border-gray-800 rounded-lg p-6 space-y-6 overflow-y-auto">
      <MetricsPanel />
      <div className="border-b border-gray-800 pb-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <FileCheck className="w-5 h-5 text-cyan-400" />
          Evaluation Framework & Release Gates
        </h2>
        <p className="text-xs text-gray-400 mt-0.5">
          Strict distinction between verified release gates and aspirational quality targets.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        <div className="bg-[#0B0F17] p-4 rounded border border-gray-800 space-y-3">
          <div className="text-emerald-400 font-semibold uppercase tracking-wider text-[11px]">
            Binary Release Gates (Pass/Fail)
          </div>
          <ul className="space-y-2 text-gray-300">
            <li className="flex items-center gap-2">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
              Two distinct local text source adapters (News & Social) operational
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
              Pydantic v2 data contracts validated with strict probability sums
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
              Zero external runtime API calls or cloud dependencies
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
              Cryptographic manifest audited with SHA-256 for all datasets
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
              Funded book value and derivative notional/MTM reported separately
            </li>
          </ul>
        </div>

        <div className="bg-[#0B0F17] p-4 rounded border border-gray-800 space-y-3">
          <div className="text-cyan-400 font-semibold uppercase tracking-wider text-[11px]">
            NLP Quality Targets
          </div>
          <div className="space-y-2 text-gray-300 font-mono text-[11px]">
            <div className="flex justify-between">
              <span>Sentiment macro-F1</span>
              <span className="text-white font-bold">≥ 0.75</span>
            </div>
            <div className="flex justify-between">
              <span>Event classification macro-F1</span>
              <span className="text-white font-bold">≥ 0.70</span>
            </div>
            <div className="flex justify-between">
              <span>Entity linking precision</span>
              <span className="text-white font-bold">≥ 0.90</span>
            </div>
            <div className="flex justify-between">
              <span>Severity MAE vs human labels</span>
              <span className="text-amber-300 font-bold">≤ 1.5 pts · pending human-labeled news set</span>
            </div>
            <p className="text-gray-500 font-sans pt-1">
              Measured values are in the table above, generated from docs/metrics.json on real held-out data.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
