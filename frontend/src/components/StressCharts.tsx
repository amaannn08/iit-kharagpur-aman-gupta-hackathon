import { useEffect, useId, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  fetchMetrics,
  fetchStressScenarios,
  runCustomStress,
  runStressScenario,
  StressRunResult,
  StressScenario,
} from '../api/client';
import { Card } from './ui/Card';

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

  const rawId = useId();
  const hatchId = `stress-hatch-${rawId.replace(/[^a-zA-Z0-9-_]/g, '')}`;

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
    <Card className="space-y-5" data-testid="stress-charts">
      {/* PS Benchmark Reference Card */}
      {psBenchmark && (
        <div
          className="bg-theme-card-subtle border border-theme-border rounded-2xl p-4 text-xs space-y-3"
          data-testid="ps-benchmark-card"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="font-bold text-theme-text">
              Problem Statement Benchmark: &ldquo;Geopolitical event, impact 8 &rarr; equities -10%, rates +200 bp&rdquo;
            </span>
            <button
              type="button"
              onClick={() => run('ps', () => runCustomStress({ equity_shock_pct: -0.1, benchmark_yield_shift_bps: 200 }))}
              disabled={busy !== null}
              className="px-3.5 py-1.5 rounded-full bg-theme-primary-fill hover:bg-theme-primary text-theme-on-primary font-semibold shadow-xs transition-colors cursor-pointer"
            >
              Run live
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-theme-text font-mono">
            <div className="p-2.5 rounded-xl bg-theme-card border border-theme-border">
              <span className="text-theme-muted block text-[10px] uppercase font-sans">Funded Baseline</span>
              <span className="font-bold text-sm">
                ${((psBenchmark.funded_baseline_usd ?? 610000000) / 1e6).toFixed(1)}M
              </span>
            </div>
            <div className="p-2.5 rounded-xl bg-theme-card border border-theme-border">
              <span className="text-theme-muted block text-[10px] uppercase font-sans">Funded Stressed</span>
              <span className="font-bold text-sm">
                ${((psBenchmark.funded_stressed_usd ?? 588240467.2) / 1e6).toFixed(1)}M
              </span>
            </div>
            <div className="p-2.5 rounded-xl bg-theme-card border border-theme-border">
              <span className="text-theme-muted block text-[10px] uppercase font-sans">Total P&amp;L</span>
              <span className="text-theme-loss font-bold text-sm">
                {usd(psBenchmark.total_pnl_usd)}
              </span>
            </div>
            <div className="p-2.5 rounded-xl bg-theme-card border border-theme-border">
              <span className="text-theme-muted block text-[10px] uppercase font-sans">Derivative MTM</span>
              <span className="text-theme-primary font-bold text-sm">
                +${(psBenchmark.derivative_mtm_change_usd / 1e3).toFixed(0)}k
              </span>
            </div>
          </div>

          {psBenchmark.by_sleeve_usd && (
            <div className="flex flex-wrap gap-3 pt-1 border-t border-theme-border text-[11px]">
              <span className="text-theme-muted font-medium">P&amp;L by sleeve:</span>
              {Object.entries(psBenchmark.by_sleeve_usd).map(([sleeve, pnl]: [string, any]) => (
                <span key={sleeve} className="text-theme-text-body">
                  <span className="capitalize text-theme-muted">{sleeve}:</span> {usd(Number(pnl))}
                </span>
              ))}
            </div>
          )}

          {psBenchmark.top_drivers && psBenchmark.top_drivers.length > 0 && (
            <div className="flex flex-wrap gap-2 text-[10px] text-theme-muted pt-1 border-t border-theme-border">
              <span className="font-medium">Top loss drivers:</span>
              {psBenchmark.top_drivers.slice(0, 3).map((d: any, idx: number) => (
                <span key={idx} className="bg-theme-card px-2 py-0.5 rounded-full text-theme-text-body border border-theme-border">
                  {d.counterparty_name || d.position_id} ({d.dominant_component}): {usd(d.pnl_usd)}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Scenario Presets Strip */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-theme-muted font-semibold mr-1">One-click scenario:</span>
        <button
          type="button"
          onClick={() => run('ps', () => runCustomStress({ equity_shock_pct: -0.1, benchmark_yield_shift_bps: 200 }))}
          disabled={busy !== null}
          className="px-3 py-1 rounded-full border border-theme-primary-fill bg-theme-primary-tint text-theme-primary-text hover:opacity-90 transition-colors font-semibold cursor-pointer"
        >
          PS example: equities -10%, rates +2%
        </button>
        {scenarios.map((s) => (
          <button
            key={s.scenario_id}
            type="button"
            onClick={() => run(s.scenario_id, () => runStressScenario(s.scenario_id))}
            disabled={busy !== null}
            title={s.description}
            className="px-3 py-1 rounded-full border border-theme-border bg-theme-card text-theme-text-body hover:bg-theme-bg transition-colors cursor-pointer"
          >
            {s.name.replace('Historical: ', '').replace(/ \(.*\)$/, '')}
          </button>
        ))}
        {busy && <span className="text-theme-muted font-mono">running...</span>}
      </div>

      {!result ? (
        <div className="py-8 text-center text-xs text-theme-subtle font-mono">
          Run a scenario or wait for an event-triggered stress test.
        </div>
      ) : result.status === 'NO_EXPOSURE' ? (
        <div className="py-6 text-center text-xs text-theme-muted font-mono p-4 rounded-xl bg-theme-card-subtle border border-theme-border">
          NO EXPOSURE: the {result.event_class} shock on {result.target_entity ?? 'target'} touches no position in the book.
        </div>
      ) : (
        <div className="grid grid-cols-12 gap-5 pt-2">
          {/* Before vs After Chart */}
          <div className="col-span-12 lg:col-span-6 p-4 rounded-2xl bg-theme-card-subtle border border-theme-border">
            <h3 className="text-xs font-bold text-theme-text mb-3">
              Portfolio value before vs after, by sleeve
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={sleeves}>
                <defs>
                  <pattern
                    id={hatchId}
                    width="6"
                    height="6"
                    patternUnits="userSpaceOnUse"
                    patternTransform="rotate(45)"
                  >
                    <line x1="0" y1="0" x2="0" y2="6" stroke="var(--theme-subtle)" strokeWidth="2" />
                    <rect width="6" height="6" fill="var(--theme-bg)" opacity="0.3" />
                  </pattern>
                </defs>
                <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--theme-border)" />
                <XAxis dataKey="sleeve" tick={{ fill: 'var(--theme-muted)', fontSize: 11 }} />
                <YAxis tickFormatter={(v) => `$${Math.round(v / 1e6)}M`} tick={{ fill: 'var(--theme-muted)', fontSize: 10 }} />
                <Tooltip
                  formatter={(v: number) => usd(v)}
                  contentStyle={{ background: 'var(--theme-card)', border: '1px solid var(--theme-border)', borderRadius: 12, fontSize: 11, color: 'var(--theme-text)' }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Before" fill={`url(#${hatchId})`} stroke="var(--theme-muted)" strokeWidth={1} radius={[8, 8, 8, 8]} />
                <Bar dataKey="After" fill="var(--theme-primary)" radius={[8, 8, 8, 8]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Loss Waterfall Chart */}
          <div className="col-span-12 lg:col-span-6 p-4 rounded-2xl bg-theme-card-subtle border border-theme-border">
            <h3 className="text-xs font-bold text-theme-text mb-3 flex items-center justify-between">
              <span>Loss waterfall: total {usd(result.total_pnl_usd)} ({(result.total_pnl_pct * 100).toFixed(2)}%)</span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold ${result.reconciliation_passed ? 'bg-theme-primary-tint text-theme-primary-text' : 'bg-theme-loss-bg text-theme-loss'}`}>
                {result.reconciliation_passed ? 'Reconciled' : 'Reconciliation Failed'}
              </span>
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={waterfallData(result)}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--theme-border)" />
                <XAxis dataKey="name" tick={{ fill: 'var(--theme-muted)', fontSize: 10 }} />
                <YAxis domain={['auto', 'auto']} tickFormatter={(v) => `$${Math.round(v / 1e6)}M`} tick={{ fill: 'var(--theme-muted)', fontSize: 10 }} />
                <Tooltip
                  formatter={(v: number, k: string) => (k === 'base' ? null : usd(v))}
                  contentStyle={{ background: 'var(--theme-card)', border: '1px solid var(--theme-border)', borderRadius: 12, fontSize: 11, color: 'var(--theme-text)' }}
                />
                <Bar dataKey="base" stackId="w" fill="transparent" />
                <Bar dataKey="delta" stackId="w" radius={[6, 6, 6, 6]}>
                  {waterfallData(result).map((d, i) => (
                    <Cell
                      key={i}
                      fill={d.kind === 'total' ? 'var(--theme-primary-fill)' : d.kind === 'loss' ? 'var(--theme-loss)' : 'var(--theme-primary-light)'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </Card>
  );
}
