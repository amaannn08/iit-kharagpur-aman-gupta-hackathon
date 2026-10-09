import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { fetchMetrics } from '../api/client';

/** Real-data evaluation results, read from docs/metrics.json (scripts/run_evaluation.py). */
export function MetricsPanel() {
  const [m, setM] = useState<Record<string, any> | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetchMetrics().then(setM).catch(() => setFailed(true));
  }, []);

  if (failed || (m && !m.public_real)) {
    return (
      <div className="bg-[#111827] border border-gray-800 rounded-lg p-4 text-xs text-gray-500 font-mono" data-testid="metrics-panel">
        Real-data metrics unavailable: run <code>uv run python scripts/run_evaluation.py</code>.
      </div>
    );
  }
  if (!m) return null;

  const ev = m.public_real.event;
  const se = m.public_real.sentiment;
  const ent = m.entity_polygon;
  const imp = m.market_impact;
  const perf = m.perf;
  const rows: [string, string, string][] = [
    [`Event macro-F1 (${ev.n.toLocaleString('en-US')} held-out real tweets)`, ev.macro_f1_model.toFixed(3),
     `keyword ${ev.baseline_keyword_macro_f1.toFixed(3)} · old seed ${ev.baseline_seed_classifier_macro_f1.toFixed(3)}`],
    ['Event runtime path (abstention + gates)', `precision ${ev.precision_when_fired.toFixed(3)}`, `fires on ${(ev.fired_rate * 100).toFixed(0)}% of rows`],
    [`Sentiment macro-F1 (${se.n.toLocaleString('en-US')} held-out real tweets)`, se.macro_f1.toFixed(3), `lexicon ${se.baseline_lexicon_macro_f1.toFixed(3)}`],
    ...(ent ? [[`Entity linking (${ent.articles.toLocaleString('en-US')} real articles)`, `P ${ent.precision.toFixed(3)} / R ${ent.recall.toFixed(3)}`, 'gold: Polygon tickers'] as [string, string, string]] : []),
    ...(imp ? [[`Impact vs abnormal return (${imp.events.toLocaleString('en-US')} events)`, `ρ ${imp.learned_oof_spearman.toFixed(3)}`,
               `95% CI [${imp.learned_oof_spearman_ci95[0].toFixed(3)}, ${imp.learned_oof_spearman_ci95[1].toFixed(3)}] · rubric ${imp.rubric_v1_spearman.toFixed(3)}`] as [string, string, string]] : []),
    ...(perf ? [['Latency p95 / throughput (CPU)', `${perf.latency_p95_s.toFixed(3)} s`, `${perf.records_per_s} records/s · ${perf.peak_rss_gb} GB`] as [string, string, string]] : []),
  ];
  const deciles = imp
    ? Object.entries(imp.mean_abs_z_by_decile as Record<string, number>).map(([d, z]) => ({ decile: d, z }))
    : [];

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-lg p-4 grid grid-cols-12 gap-4" data-testid="metrics-panel">
      <div className="col-span-12 lg:col-span-7 text-xs">
        <h3 className="font-semibold text-gray-300 mb-2">Measured on real held-out data</h3>
        <table className="w-full font-mono">
          <tbody>
            {rows.map(([k, v, c]) => (
              <tr key={k} className="border-t border-gray-800">
                <td className="py-1.5 text-gray-400 pr-2">{k}</td>
                <td className="py-1.5 text-cyan-300 font-bold whitespace-nowrap">{v}</td>
                <td className="py-1.5 text-gray-500 pl-2">{c}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-gray-500">Generated {m.generated_at} by scripts/run_evaluation.py</p>
      </div>
      {deciles.length > 0 && (
        <div className="col-span-12 lg:col-span-5">
          <h3 className="text-xs font-semibold text-gray-300 mb-2">Mean |abnormal return z| by impact decile</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={deciles}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="decile" tick={{ fill: '#9ca3af', fontSize: 10 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#0B0F17', border: '1px solid #374151', fontSize: 11 }} />
              <Bar dataKey="z" fill="#a78bfa" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
