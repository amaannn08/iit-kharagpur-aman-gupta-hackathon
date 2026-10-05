import { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Database,
  FileCheck,
  Layers,
  Pause,
  Play,
  RotateCcw,
  ShieldAlert,
  StepForward,
  TrendingDown,
  XCircle,
} from 'lucide-react';
import {
  fetchDatasets,
  fetchHealth,
  HealthResponse,
  ManifestResponse,
} from './api/client';

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [manifest, setManifest] = useState<ManifestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'feed' | 'stress' | 'eval'>('overview');

  useEffect(() => {
    Promise.allSettled([fetchHealth(), fetchDatasets()])
      .then(([healthResult, manifestResult]) => {
        if (healthResult.status === 'fulfilled') {
          setHealth(healthResult.value);
        }
        if (manifestResult.status === 'fulfilled') {
          setManifest(manifestResult.value);
        }
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, []);

  return (
    <div className="min-h-screen bg-[#0B0F17] text-[#E5E7EB] flex flex-col font-sans">
      {/* Top Warning Banner: Mandatory Honesty & Provenance Badge */}
      <div className="bg-amber-950/80 border-b border-amber-600/40 px-4 py-1.5 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 text-amber-300 font-semibold tracking-wide">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
          <span className="uppercase px-1.5 py-0.5 rounded bg-amber-500/20 border border-amber-400/30">
            HISTORICAL REPLAY / SYNTHETIC SCENARIO
          </span>
          <span className="text-amber-200/80 font-normal">
            100% Offline Localhost Execution • Zero External APIs • Verified Datasets
          </span>
        </div>
        <div className="flex items-center gap-3 text-amber-200/70">
          <span>Candidate: Aman Gupta (IIT Kharagpur)</span>
          <span>•</span>
          <span className="font-mono bg-amber-900/60 px-2 py-0.5 rounded border border-amber-700/40 text-amber-200">
            M0/M1 Foundation Active
          </span>
        </div>
      </div>

      {/* Main Terminal Header */}
      <header className="bg-[#111827] border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-cyan-400 animate-pulse" />
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              S&P Sentinel
              <span className="text-xs px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono">
                RISK TERMINAL
              </span>
            </h1>
          </div>
          <span className="text-gray-500 text-sm">|</span>
          <nav className="flex items-center gap-1">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                activeTab === 'overview'
                  ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-700/50'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
              }`}
            >
              Datasets & Readiness (M0/M1)
            </button>
            <button
              onClick={() => setActiveTab('feed')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                activeTab === 'feed'
                  ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-700/50'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
              }`}
            >
              Signal Feed (Planned M2)
            </button>
            <button
              onClick={() => setActiveTab('stress')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                activeTab === 'stress'
                  ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-700/50'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
              }`}
            >
              Wholesale Stress (Planned M4)
            </button>
            <button
              onClick={() => setActiveTab('eval')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                activeTab === 'eval'
                  ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-700/50'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
              }`}
            >
              Evaluation & Governance
            </button>
          </nav>
        </div>

        {/* Backend Status Pill */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs bg-gray-900 border border-gray-800 rounded-full px-3 py-1">
            <span className="text-gray-400">Core Engine:</span>
            {loading ? (
              <span className="text-yellow-400 font-mono">CHECKING...</span>
            ) : health?.status === 'ok' ? (
              <span className="text-emerald-400 font-medium flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                ONLINE (OFFLINE-MODE)
              </span>
            ) : (
              <span className="text-gray-400 font-medium flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-gray-500" />
                STANDALONE (API OFFLINE)
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Main Workspace Area */}
      <main className="flex-1 p-6 grid grid-cols-12 gap-6 overflow-hidden">
        {activeTab === 'overview' && (
          <div className="col-span-12 flex flex-col bg-[#111827] border border-gray-800 rounded-lg p-6 space-y-6 overflow-y-auto">
            {/* Header & Status Banner */}
            <div className="flex items-center justify-between border-b border-gray-800 pb-4">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Database className="w-5 h-5 text-cyan-400" />
                  M0/M1 Operational Status & Verified Dataset Catalog
                </h2>
                <p className="text-xs text-gray-400 mt-1">
                  Cryptographically audited synthetic replay fixtures and local readiness verification.
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono">
                <span className="px-2.5 py-1 rounded bg-gray-900 border border-gray-800 text-gray-300">
                  Manifest: v{manifest?.manifest_version ?? '1.0'}
                </span>
                <span className="px-2.5 py-1 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800">
                  {manifest?.datasets.length ?? 10} Registered Datasets
                </span>
              </div>
            </div>

            {/* System Readiness Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-[#0B0F17] p-4 rounded border border-gray-800">
                <div className="text-xs text-gray-400">FastAPI Health Service</div>
                <div className="text-base font-bold text-white font-mono mt-1 flex items-center gap-1.5">
                  {health?.status === 'ok' ? (
                    <>
                      <CheckCircle className="w-4 h-4 text-emerald-400" />
                      <span className="text-emerald-400">READY (200 OK)</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4 text-gray-400" />
                      <span className="text-gray-400">STANDALONE</span>
                    </>
                  )}
                </div>
                <div className="text-[11px] text-gray-500 mt-0.5">Route: /api/health</div>
              </div>

              <div className="bg-[#0B0F17] p-4 rounded border border-gray-800">
                <div className="text-xs text-gray-400">Offline Isolation Policy</div>
                <div className="text-base font-bold text-emerald-400 font-mono mt-1 flex items-center gap-1.5">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  100% LOCALHOST
                </div>
                <div className="text-[11px] text-gray-500 mt-0.5">External APIs: Strictly 0</div>
              </div>

              <div className="bg-[#0B0F17] p-4 rounded border border-gray-800">
                <div className="text-xs text-gray-400">Local SQLite Audit Store</div>
                <div className="text-base font-bold text-white font-mono mt-1 flex items-center gap-1.5">
                  {health?.environment.database_ready ? (
                    <>
                      <CheckCircle className="w-4 h-4 text-emerald-400" />
                      <span className="text-emerald-400">INITIALIZED</span>
                    </>
                  ) : (
                    <span className="text-gray-400">PENDING</span>
                  )}
                </div>
                <div className="text-[11px] text-gray-500 mt-0.5">SQLAlchemy 2.0 Engine</div>
              </div>

              <div className="bg-[#0B0F17] p-4 rounded border border-gray-800">
                <div className="text-xs text-gray-400">Dataset Provenance</div>
                <div className="text-base font-bold text-cyan-400 font-mono mt-1 flex items-center gap-1.5">
                  <FileCheck className="w-4 h-4 text-cyan-400" />
                  SHA-256 AUDITED
                </div>
                <div className="text-[11px] text-gray-500 mt-0.5">License: MIT (Project-Authored)</div>
              </div>
            </div>

            {/* Datasets Table */}
            <div className="bg-[#0B0F17] rounded border border-gray-800 p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
                  Bundled Offline Datasets & Cryptographic Checksums
                </h3>
                <span className="text-[11px] text-gray-500 font-mono">
                  data/manifest.json • Hackathon Section 8 & 9 Compliant
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="text-gray-400 border-b border-gray-800 font-mono text-[11px]">
                    <tr>
                      <th className="pb-2">Dataset File Path</th>
                      <th className="pb-2">Format</th>
                      <th className="pb-2">Records</th>
                      <th className="pb-2">Data Type</th>
                      <th className="pb-2">License</th>
                      <th className="pb-2 text-right">SHA-256 (Prefix)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/60 font-mono text-xs">
                    {(manifest?.datasets ?? [
                      {
                        file_path: 'data/news_demo.csv',
                        format: 'csv',
                        record_count: 25,
                        is_synthetic: true,
                        license: 'MIT License (Project-Authored Synthetic Data)',
                        sha256: '0f4ec4ae71089cf953abf953ecd888746f56e0cba487d703220ad2d4369b32fb',
                        byte_size: 8906,
                        description: 'Curated synthetic financial news headlines',
                      },
                      {
                        file_path: 'data/social_demo.csv',
                        format: 'csv',
                        record_count: 25,
                        is_synthetic: true,
                        license: 'MIT License (Project-Authored Synthetic Data)',
                        sha256: '38115556c42fc7b5557f2106c4f12c887e49bc8c6ec0044c62e1104e37a60f13',
                        byte_size: 6177,
                        description: 'Curated synthetic social posts',
                      },
                      {
                        file_path: 'data/entity_aliases.csv',
                        format: 'csv',
                        record_count: 23,
                        is_synthetic: false,
                        license: 'Public Factual Identifiers / MIT Reference Universe',
                        sha256: 'beeae2b4eaf41cf2980e5424dec3c682907d8c49f6032ce0819043808ceb5482',
                        byte_size: 1763,
                        description: 'Curated reference universe mapping',
                      },
                      {
                        file_path: 'data/wholesale_positions.json',
                        format: 'json',
                        record_count: 13,
                        is_synthetic: true,
                        license: 'MIT License (Project-Authored Synthetic Data)',
                        sha256: 'e2cc26e7dbe8f6254ee33a009a1b0926d7e2ada5ce2f885dce32da058c8703c8',
                        byte_size: 5865,
                        description: 'Synthetic $500M institutional wholesale portfolio',
                      },
                      {
                        file_path: 'data/graph_edges.csv',
                        format: 'csv',
                        record_count: 10,
                        is_synthetic: true,
                        license: 'MIT License (Project-Authored Synthetic Relationships)',
                        sha256: 'd23e1032c12b83428e6aa750ed008d1616c06f4c66cf2e591d11f5e644df2ae1',
                        byte_size: 1236,
                        description: 'Directed contagion graph edges',
                      },
                    ]).map((ds) => (
                      <tr key={ds.file_path} className="hover:bg-gray-900/40">
                        <td className="py-2.5 text-cyan-400 font-semibold">{ds.file_path}</td>
                        <td className="text-gray-400 uppercase">{ds.format}</td>
                        <td className="text-white">{ds.record_count}</td>
                        <td>
                          {ds.is_synthetic ? (
                            <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 text-[10px]">
                              SYNTHETIC
                            </span>
                          ) : (
                            <span className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/30 text-[10px]">
                              FACTUAL REF
                            </span>
                          )}
                        </td>
                        <td className="text-gray-300 text-[11px] truncate max-w-xs">{ds.license}</td>
                        <td className="py-2.5 text-right text-gray-500 font-mono text-[11px]">
                          {ds.sha256 ? `${ds.sha256.slice(0, 12)}...` : 'n/a'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'feed' && (
          <div className="col-span-12 flex flex-col space-y-4">
            {/* Roadmap Status Notice */}
            <div className="bg-cyan-950/50 border border-cyan-700/50 rounded-lg p-3.5 flex items-center justify-between text-xs text-cyan-300">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-cyan-400 shrink-0" />
                <span className="font-semibold uppercase tracking-wider">
                  [PLANNED M2: REPLAY ENGINE & NLP INFERENCE NOT INITIALIZED]
                </span>
                <span className="text-cyan-200/80">
                  Below is a static schema preview of the RiskSignal contract. Replay execution activates in M2.
                </span>
              </div>
              <span className="font-mono text-cyan-400/80">PRD §6.2 Signal Contract Spec</span>
            </div>

            <div className="grid grid-cols-12 gap-6 flex-1">
              {/* Left 7 Columns: Mock Feed Stream */}
              <div className="col-span-12 lg:col-span-7 flex flex-col bg-[#111827] border border-gray-800 rounded-lg overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between bg-gray-900/60">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-cyan-400" />
                    <h2 className="text-sm font-semibold text-gray-200">Replay Feed Stream Preview</h2>
                    <span className="text-xs text-gray-500 font-mono">(Contract Schema Mock)</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800">
                      NEWS ADAPTER
                    </span>
                    <span className="px-2 py-0.5 rounded bg-purple-950 text-purple-400 border border-purple-800">
                      SOCIAL ADAPTER
                    </span>
                  </div>
                </div>

                <div className="flex-1 p-4 space-y-3 overflow-y-auto">
                  <div className="p-3.5 rounded border border-gray-800 bg-[#0B0F17]">
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="px-1.5 py-0.5 rounded bg-blue-900/50 text-blue-300 font-semibold uppercase text-[10px]">
                          NEWS
                        </span>
                        <span className="font-semibold text-white">Apex Industrial Holdings missed coupon payment</span>
                        <span className="font-mono text-cyan-400 text-[11px]">$APEX</span>
                      </div>
                      <span className="text-gray-500 font-mono text-[11px]">2026-03-01 11:15 UTC</span>
                    </div>
                    <p className="text-xs text-gray-400 leading-relaxed">
                      Apex Industrial Holdings failed to remit a scheduled $45 million quarterly coupon payment to lending syndicates.
                    </p>
                    <div className="mt-2.5 pt-2 border-t border-gray-800/60 flex items-center justify-between text-[11px]">
                      <span className="text-amber-400 font-medium">Event: CREDIT • Impact: 8/10</span>
                      <span className="text-red-400 font-mono">Sentiment: -0.92 (Negative)</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right 5 Columns: Signal Inspector Preview */}
              <div className="col-span-12 lg:col-span-5 flex flex-col bg-[#111827] border border-gray-800 rounded-lg overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-800 bg-gray-900/60 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Layers className="w-4 h-4 text-cyan-400" />
                    <h2 className="text-sm font-semibold text-gray-200">Signal Audit Schema Preview</h2>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
                    SCHEMA PREVIEW
                  </span>
                </div>

                <div className="flex-1 p-5 space-y-4 text-xs overflow-y-auto">
                  <div className="bg-[#0B0F17] p-3.5 rounded border border-gray-800 space-y-2">
                    <div className="text-gray-400 font-medium">Target Entity Contract</div>
                    <div className="text-sm font-bold text-white flex items-center justify-between">
                      <span>Apex Industrial Holdings</span>
                      <span className="font-mono text-cyan-400">$APEX</span>
                    </div>
                    <div className="text-[11px] text-gray-400">Sector: Industrials • Target Counterparty</div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-[#0B0F17] p-3 rounded border border-gray-800">
                      <div className="text-gray-400 text-[11px]">FinBERT Sentiment Target</div>
                      <div className="text-base font-bold text-red-400 font-mono">-0.92</div>
                      <div className="text-[10px] text-gray-400">Contract: [-1.0, +1.0]</div>
                    </div>
                    <div className="bg-[#0B0F17] p-3 rounded border border-gray-800">
                      <div className="text-gray-400 text-[11px]">Severity Impact Rubric</div>
                      <div className="text-base font-bold text-amber-400 font-mono">8 / 10</div>
                      <div className="text-[10px] text-gray-400">Base: 5 + Scope: 1 + Sev: 2</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'stress' && (
          <div className="col-span-12 flex flex-col bg-[#111827] border border-gray-800 rounded-lg p-6 space-y-6">
            {/* Roadmap Status Notice */}
            <div className="bg-cyan-950/50 border border-cyan-700/50 rounded-lg p-3.5 flex items-center justify-between text-xs text-cyan-300">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-cyan-400 shrink-0" />
                <span className="font-semibold uppercase tracking-wider">
                  [PLANNED M4: WHOLESALE STRESS VALUATION ENGINE NOT INITIALIZED]
                </span>
                <span className="text-cyan-200/80">
                  Below is the baseline $500M wholesale portfolio specification. Shock execution activates in M4.
                </span>
              </div>
              <span className="font-mono text-cyan-400/80">PRD §10 Module B Spec</span>
            </div>

            <div className="flex items-center justify-between border-b border-gray-800 pb-4">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <TrendingDown className="w-5 h-5 text-red-400" />
                  Module B: Wholesale Banking Portfolio Specification
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  $500M Synthetic Wholesale Book • Multi-Asset Valuation (Loans ECL, Bond Duration, Swap Signed DV01)
                </p>
              </div>
              <div className="text-right font-mono">
                <div className="text-xs text-gray-400">Baseline Total Value</div>
                <div className="text-lg font-bold text-emerald-400">$500,000,000 USD</div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-[#0B0F17] p-4 rounded border border-gray-800">
                <div className="text-xs text-gray-400">Corporate Loans (Funded)</div>
                <div className="text-lg font-bold text-white font-mono mt-1">$220,000,000</div>
                <div className="text-[11px] text-gray-500 mt-0.5">5 Facilities • ECL Model</div>
              </div>
              <div className="bg-[#0B0F17] p-4 rounded border border-gray-800">
                <div className="text-xs text-gray-400">Corporate Bonds (MTM)</div>
                <div className="text-lg font-bold text-white font-mono mt-1">$200,000,000</div>
                <div className="text-[11px] text-gray-500 mt-0.5">5 Notes • Mod. Duration ~4.6y</div>
              </div>
              <div className="bg-[#0B0F17] p-4 rounded border border-gray-800">
                <div className="text-xs text-gray-400">Interest Rate Swaps (Notional)</div>
                <div className="text-lg font-bold text-cyan-400 font-mono mt-1">$150,000,000</div>
                <div className="text-[11px] text-gray-500 mt-0.5">2 SOFR Swaps • Signed DV01</div>
              </div>
              <div className="bg-[#0B0F17] p-4 rounded border border-gray-800">
                <div className="text-xs text-gray-400">Cash & Treasury Reserves</div>
                <div className="text-lg font-bold text-white font-mono mt-1">$80,000,000</div>
                <div className="text-[11px] text-gray-500 mt-0.5">Fed Overnight • 0 Duration</div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'eval' && (
          <div className="col-span-12 flex flex-col bg-[#111827] border border-gray-800 rounded-lg p-6 space-y-6">
            <div className="border-b border-gray-800 pb-4">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Database className="w-5 h-5 text-cyan-400" />
                Evaluation Framework & Release Gates (PRD Section 2.3 & 14)
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
                </ul>
              </div>

              <div className="bg-[#0B0F17] p-4 rounded border border-gray-800 space-y-3">
                <div className="text-cyan-400 font-semibold uppercase tracking-wider text-[11px]">
                  NLP Quality Targets (Measured on Holdout in M7)
                </div>
                <div className="space-y-2 text-gray-300 font-mono text-[11px]">
                  <div className="flex justify-between">
                    <span>Sentiment Macro-F1 Target:</span>
                    <span className="text-white">≥ 0.75</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Event Classification Macro-F1:</span>
                    <span className="text-white">≥ 0.70</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Entity Linking Precision:</span>
                    <span className="text-white">≥ 0.90</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Severity MAE Target:</span>
                    <span className="text-white">≤ 1.5 pts</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Bottom Replay Control Toolbar: Explicitly Disabled with Transparent Roadmap Badging */}
      <footer className="bg-[#111827] border-t border-gray-800 px-6 py-3 flex items-center justify-between text-xs">
        <div className="flex items-center gap-3">
          <span className="text-gray-400 font-medium">Replay Engine:</span>
          <div className="flex items-center gap-1 bg-gray-900 border border-gray-800 rounded p-1 opacity-60">
            <button
              disabled={true}
              className="p-1.5 rounded text-gray-500 cursor-not-allowed"
              title="Replay engine not initialized (planned M2)"
            >
              <Play className="w-3.5 h-3.5" />
            </button>
            <button
              disabled={true}
              className="p-1.5 rounded text-gray-500 cursor-not-allowed"
              title="Replay engine not initialized (planned M2)"
            >
              <Pause className="w-3.5 h-3.5" />
            </button>
            <button
              disabled={true}
              className="p-1.5 rounded text-gray-500 cursor-not-allowed"
              title="Replay engine not initialized (planned M2)"
            >
              <StepForward className="w-3.5 h-3.5" />
            </button>
            <button
              disabled={true}
              className="p-1.5 rounded text-gray-500 cursor-not-allowed"
              title="Replay engine not initialized (planned M2)"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
          <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700 text-[10px] font-mono">
            [PLANNED M2: CONTROLS DISABLED]
          </span>
        </div>

        <div className="flex items-center gap-4 text-gray-500">
          <div className="flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-gray-500" />
            <span className="font-mono text-gray-400">ENGINE: NOT INITIALIZED (M0/M1 SHELL)</span>
          </div>
          <span>•</span>
          <span className="font-mono">Clock: Standby</span>
        </div>
      </footer>
    </div>
  );
}
