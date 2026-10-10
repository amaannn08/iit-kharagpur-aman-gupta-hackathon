import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { fetchStressScenarios, runCustomStress, runStressScenario, StressRunResult, StressScenario } from '../api/client';

const usd = (v: number) => `${v < 0 ? '-' : ''}$${Math.abs(v / 1e6).toFixed(2)}M`;
const ASSET_ORDER = ['loan', 'bond', 'equity', 'cash'];

/** P&L waterfall: funded baseline, one bar per funded asset class, derivative MTM, stressed. */
export function waterfallData(r: StressRunResult) {
  const rows: { name: string; base: number; delta: number; kind: 'total' | 'loss' | 'gain' }[] = [];
  const baseline = r.funded_baseline_value_usd ?? r.baseline_total_book_value_usd;
  rows.push({ name: 'Funded baseline', base: 0, delta: baseline, kind: 'total' });
  let level = baseline;
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
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    fetchStressScenarios()
      .then((s) => setScenarios(s.filter((x) => x.scenario_id.startsWith('HIST-'))))
      .catch(() => setScenarios([]));
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
