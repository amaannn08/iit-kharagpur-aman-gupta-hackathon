import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import {
  fetchMetrics,
  fetchStressScenarios,
  runCustomStress,
  runStressScenario,
  StressRunResult,
  StressScenario,
} from '../api/client';

const usd = (v: number) => `${v < 0 ? '-' : ''}$${Math.abs(v / 1e6).toFixed(2)}M`;
const ASSET_ORDER = ['loan', 'bond', 'equity', 'cash'];

/** P&L waterfall: funded baseline, one bar per loss component (or asset class fallback), stressed. */
export function waterfallData(r: StressRunResult) {
  const rows: { name: string; base: number; delta: number; kind: 'total' | 'loss' | 'gain' }[] = [];
  const baseline = r.funded_baseline_value_usd ?? r.baseline_total_book_value_usd;
  rows.push({ name: 'Funded baseline', base: 0, delta: baseline, kind: 'total' });
  let level = baseline;

  if (r.attribution?.by_component) {
    const COMPONENT_ORDER: [string, string][] = [
      ['rates_usd', 'Rates'],
      ['spread_usd', 'Spread'],
      ['pd_usd', 'Loan PD'],
      ['lgd_usd', 'Loan LGD'],
      ['equity_usd', 'Equity'],
      ['operational_usd', 'Op-loss'],
      ['clamp_usd', 'Clamp'],
    ];
    for (const [key, label] of COMPONENT_ORDER) {
      const d = r.attribution.by_component[key] ?? 0;
      if (Math.abs(d) > 0.01) {
        rows.push({
          name: label,
          base: d < 0 ? level + d : level,
          delta: Math.abs(d),
          kind: d < 0 ? 'loss' : 'gain',
        });
        level += d;
      }
    }
  } else {
    const classes = r.asset_class_breakdown.filter((a) => ASSET_ORDER.includes(a.asset_class));
    classes.sort((a, b) => ASSET_ORDER.indexOf(a.asset_class) - ASSET_ORDER.indexOf(b.asset_class));
    for (const a of classes) {
      const d = a.total_pnl_usd;
      rows.push({ name: a.asset_class, base: d < 0 ? level + d : level, delta: Math.abs(d), kind: d < 0 ? 'loss' : 'gain' });
      level += d;
    }
    const deriv = r.derivative_mtm_change_usd ?? 0;
    rows.push({ name: 'swap MTM', base: deriv < 0 ? level + deriv : level, delta: Math.abs(deriv), kind: deriv < 0 ? 'loss' : 'gain' });
    level += deriv;
  }
  rows.push({ name: 'After stress', base: 0, delta: level, kind: 'total' });
  return rows;
}

interface Props {
  result: StressRunResult | null;
  onResult: (r: StressRunResult) => void;
}

/** Module B dashboard: before vs after by sleeve, loss waterfall, and one-click scenarios. */
export function StressCharts({ result, onResult }: Props) {
  const [scenarios, setScenarios] = useState<StressScenario[]>([]);
  const [psBenchmark, setPsBenchmark] = useState<any | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    fetchStressScenarios()
      .then((s) => setScenarios(s.filter((x) => x.scenario_id.startsWith('HIST-'))))
      .catch(() => setScenarios([]));

    fetchMetrics()
      .then((m) => {
        const ps = m?.stress?.['ps_example_equities_-10pct_rates_+200bp'];
        if (ps) setPsBenchmark(ps);
      })
      .catch(() => {});
  }, []);

  const run = async (key: string, fn: () => Promise<StressRunResult>) => {
    setBusy(key);
    try {
      onResult(await fn());
    } finally {
      setBusy(null);
    }
  };

  const sleeves = (result?.sleeve_breakdown ?? []).map((s) => ({
    sleeve: s.sleeve,
    Before: s.baseline_value_usd,
    After: s.stressed_value_usd,
    pnl: s.total_pnl_usd,
  }));

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-lg p-4 space-y-4" data-testid="stress-charts">
      {/* PS Benchmark Reference Card (Item 18) */}
      {psBenchmark && (
        <div
          className="bg-gray-900/90 border border-cyan-800/50 rounded-lg p-3 text-xs space-y-2"
          data-testid="ps-benchmark-card"
        >
          <div className="flex items-center justify-between">
            <span className="font-semibold text-cyan-300">
              Problem Statement Benchmark: &ldquo;Geopolitical event, impact 8 &rarr; equities -10%, rates +200 bp&rdquo;
            </span>
            <button
              onClick={() => run('ps', () => runCustomStress({ equity_shock_pct: -0.1, benchmark_yield_shift_bps: 200 }))}
              disabled={busy !== null}
              className="px-2.5 py-1 rounded bg-cyan-950 border border-cyan-600 text-cyan-200 hover:bg-cyan-900 font-medium transition-colors"
            >
              Run live
            </button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-gray-300 font-mono">
            <div>
              <span className="text-gray-500 block text-[10px] uppercase">Funded Baseline</span>
              ${((psBenchmark.funded_baseline_usd ?? 610000000) / 1e6).toFixed(1)}M
            </div>
            <div>
              <span className="text-gray-500 block text-[10px] uppercase">Funded Stressed</span>
              ${((psBenchmark.funded_stressed_usd ?? 588240467.2) / 1e6).toFixed(1)}M
            </div>
            <div>
              <span className="text-gray-500 block text-[10px] uppercase">Total P&L</span>
              <span className="text-rose-400 font-bold">{usd(psBenchmark.total_pnl_usd)}</span>
            </div>
            <div>
              <span className="text-gray-500 block text-[10px] uppercase">Derivative MTM</span>
              <span className="text-emerald-400">+${(psBenchmark.derivative_mtm_change_usd / 1e3).toFixed(0)}k</span>
            </div>
          </div>
          {psBenchmark.by_sleeve_usd && (
            <div className="flex flex-wrap gap-3 pt-1 border-t border-gray-800 text-[11px]">
              <span className="text-gray-400">P&L by sleeve:</span>
              {Object.entries(psBenchmark.by_sleeve_usd).map(([sleeve, pnl]: [string, any]) => (
                <span key={sleeve} className="text-gray-300">
                  <span className="capitalize text-gray-500">{sleeve}:</span> {usd(Number(pnl))}
                </span>
              ))}
            </div>
          )}
          {psBenchmark.top_drivers && psBenchmark.top_drivers.length > 0 && (
            <div className="flex flex-wrap gap-2 text-[10px] text-gray-400 pt-1 border-t border-gray-800/60">
              <span className="text-gray-500">Top loss drivers:</span>
              {psBenchmark.top_drivers.slice(0, 3).map((d: any, idx: number) => (
                <span key={idx} className="bg-gray-800/80 px-1.5 py-0.5 rounded text-gray-300">
                  {d.counterparty_name || d.position_id} ({d.dominant_component}): {usd(d.pnl_usd)}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-gray-400 font-medium mr-1">Run scenario:</span>
        <button
          onClick={() => run('ps', () => runCustomStress({ equity_shock_pct: -0.1, benchmark_yield_shift_bps: 200 }))}
          disabled={busy !== null}
          className="px-2.5 py-1 rounded border border-cyan-700 text-cyan-300 hover:bg-cyan-950"
        >
          PS example: equities -10%, rates +2%
        </button>
        {scenarios.map((s) => (
          <button
            key={s.scenario_id}
            onClick={() => run(s.scenario_id, () => runStressScenario(s.scenario_id))}
            disabled={busy !== null}
            title={s.description}
            className="px-2.5 py-1 rounded border border-gray-700 text-gray-300 hover:bg-gray-800"
          >
            {s.name.replace('Historical: ', '').replace(/ \(.*\)$/, '')}
          </button>
        ))}
        {busy && <span className="text-gray-500 font-mono">running...</span>}
      </div>

      {!result ? (
        <div className="py-8 text-center text-xs text-gray-500 font-mono">Run a scenario or wait for an event-triggered stress test.</div>
      ) : result.status === 'NO_EXPOSURE' ? (
        <div className="py-6 text-center text-xs text-amber-300 font-mono">
          NO EXPOSURE: the {result.event_class} shock on {result.target_entity ?? 'target'} touches no position in the book.
        </div>
      ) : (
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-6">
            <h3 className="text-xs font-semibold text-gray-300 mb-2">Portfolio value before vs after, by sleeve</h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={sleeves}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="sleeve" tick={{ fill: '#d1d5db', fontSize: 10 }} />
                <YAxis tickFormatter={(v) => `$${Math.round(v / 1e6)}M`} tick={{ fill: '#9ca3af', fontSize: 10 }} />
                <Tooltip formatter={(v: number) => usd(v)} contentStyle={{ background: '#0B0F17', border: '1px solid #374151', fontSize: 11 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Before" fill="#374151" />
                <Bar dataKey="After" fill="#22d3ee" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="col-span-12 lg:col-span-6">
            <h3 className="text-xs font-semibold text-gray-300 mb-2">
              Loss waterfall: total {usd(result.total_pnl_usd)} ({(result.total_pnl_pct * 100).toFixed(2)}%)
              {result.reconciliation_passed ? ' · reconciled' : ' · RECONCILIATION FAILED'}
            </h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={waterfallData(result)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="name" tick={{ fill: '#d1d5db', fontSize: 10 }} />
                <YAxis domain={['auto', 'auto']} tickFormatter={(v) => `$${Math.round(v / 1e6)}M`} tick={{ fill: '#9ca3af', fontSize: 10 }} />
                <Tooltip
                  formatter={(v: number, k: string) => (k === 'base' ? null : usd(v))}
                  contentStyle={{ background: '#0B0F17', border: '1px solid #374151', fontSize: 11 }}
                />
                <Bar dataKey="base" stackId="w" fill="transparent" />
                <Bar dataKey="delta" stackId="w">
                  {waterfallData(result).map((d, i) => (
                    <Cell key={i} fill={d.kind === 'total' ? '#6366f1' : d.kind === 'loss' ? '#ef4444' : '#22c55e'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
