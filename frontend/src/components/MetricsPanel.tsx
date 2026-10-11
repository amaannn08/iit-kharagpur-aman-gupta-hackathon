import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { fetchMetrics } from '../api/client';
import { Card } from './ui/Card';

/** Real-data evaluation results, read from docs/metrics.json (scripts/run_evaluation.py). */
export function MetricsPanel() {
  const [m, setM] = useState<Record<string, any> | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetchMetrics().then(setM).catch(() => setFailed(true));
  }, []);

  if (failed || (m && !m.public_real)) {
    return (
      <Card className="p-4" data-testid="metrics-panel">
        <p className="text-xs text-[#6B7280] font-mono">
          Real-data metrics unavailable: run <code className="text-[#111827] font-semibold">uv run python scripts/run_evaluation.py</code>.
        </p>
      </Card>
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
    <Card className="p-6" data-testid="metrics-panel">
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-12 lg:col-span-7 text-xs">
          <h3 className="font-bold text-sm text-[#111827] mb-3">Measured on real held-out data</h3>
          <table className="w-full text-xs">
            <tbody className="divide-y divide-[#F3F4F6]">
              {rows.map(([k, v, c]) => (
                <tr key={k} className="hover:bg-[#F9FAFB] transition-colors">
                  <td className="py-2 text-[#4B5563] pr-2 font-medium">{k}</td>
                  <td className="py-2 text-[#111827] font-bold font-mono whitespace-nowrap">{v}</td>
                  <td className="py-2 text-[#6B7280] pl-2 text-[11px]">{c}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-[11px] text-[#9CA3AF] font-mono">Generated {m.generated_at} by scripts/run_evaluation.py</p>
        </div>
        {deciles.length > 0 && (
          <div className="col-span-12 lg:col-span-5">
            <h3 className="text-xs font-bold text-[#111827] mb-3">Mean |abnormal return z| by impact decile</h3>
            <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={deciles} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
                  <XAxis
                    dataKey="decile"
                    tick={{ fill: '#6B7280', fontSize: 10, fontFamily: 'Plus Jakarta Sans' }}
                    axisLine={{ stroke: '#E5E7EB' }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: '#6B7280', fontSize: 10, fontFamily: 'Plus Jakarta Sans' }}
                    axisLine={{ stroke: '#E5E7EB' }}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#FFFFFF',
                      border: '1px solid #ECEDEC',
                      borderRadius: '12px',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
                      fontSize: '11px',
                      fontFamily: 'Plus Jakarta Sans',
                    }}
                  />
                  <Bar dataKey="z" fill="#1F6B45" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
