import { useEffect, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { fetchIndexCurrent, fetchIndexHistory, IndexCurrent, IndexRecord, resetIndex } from '../api/client';

const PALETTE = [
  '#22d3ee', '#a78bfa', '#f472b6', '#facc15', '#4ade80', '#fb923c', '#60a5fa', '#f87171',
  '#2dd4bf', '#c084fc', '#e879f9', '#fde047', '#86efac', '#fdba74', '#93c5fd', '#fca5a5',
  '#5eead4', '#d8b4fe', '#f0abfc', '#bef264',
];

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

/** Module A: sentiment-driven mock index. Weights over time is the PS dashboard requirement. */
export function IndexPanel() {
  const [current, setCurrent] = useState<IndexCurrent | null>(null);
  const [history, setHistory] = useState<IndexRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const [c, h] = await Promise.all([fetchIndexCurrent(), fetchIndexHistory(500)]);
      setCurrent(c);
      setHistory(h);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, []);

  if (error && !current) {
    return <div className="p-6 text-xs text-gray-500 font-mono">Index unavailable: {error}</div>;
  }
  if (!current) {
    return <div className="p-6 text-xs text-gray-500 font-mono">Loading mock index...</div>;
  }

  const tickers = Object.keys(current.weights);
  const series = history.map((r, i) => ({ step: i, label: r.timestamp.slice(0, 16), ...r.weights }));
  const bars = tickers
    .map((t) => ({ ticker: t, current: current.weights[t], base: current.base_weights[t], ema: current.sentiment_ema[t] ?? 0 }))
    .sort((a, b) => b.current - a.current);

  return (
    <div className="flex-1 overflow-y-auto space-y-6" data-testid="index-panel">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-white">Module A: Sentiment-Driven Index Rebalancer</h2>
          <p className="text-xs text-gray-400">
            {current.label}. Positive sentiment raises a weight, negative lowers it; caps {pct(current.constraints.name_cap)} per
            name, {pct(current.constraints.sector_cap)} per sector; sentiment half-life {current.constraints.halflife_days} days.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="font-mono text-cyan-400">{current.rebalances} rebalances</span>
          <button
            onClick={async () => {
              await resetIndex();
              refresh();
            }}
            className="px-3 py-1.5 rounded border border-gray-700 text-gray-300 hover:bg-gray-800"
          >
            Reset index
          </button>
        </div>
      </div>

      <div className="bg-[#111827] border border-gray-800 rounded-lg p-4">
        <h3 className="text-xs font-semibold text-gray-300 mb-3">Index weights over time</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={series} stackOffset="expand">
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="step" tick={{ fill: '#9ca3af', fontSize: 10 }} label={{ value: 'rebalance #', fill: '#6b7280', fontSize: 10, position: 'insideBottom' }} />
            <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fill: '#9ca3af', fontSize: 10 }} />
            <Tooltip
              formatter={(v: number) => pct(v)}
              labelFormatter={(i) => series[Number(i)]?.label ?? i}
              contentStyle={{ background: '#0B0F17', border: '1px solid #374151', fontSize: 11 }}
            />
            {tickers.map((t, i) => (
              <Area key={t} type="stepAfter" dataKey={t} stackId="w" stroke="none" fill={PALETTE[i % PALETTE.length]} fillOpacity={0.85} />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-12 lg:col-span-7 bg-[#111827] border border-gray-800 rounded-lg p-4">
          <h3 className="text-xs font-semibold text-gray-300 mb-3">Current weight vs base (equal weight)</h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={bars} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis type="number" tickFormatter={(v) => pct(v)} tick={{ fill: '#9ca3af', fontSize: 10 }} />
              <YAxis type="category" dataKey="ticker" width={50} tick={{ fill: '#d1d5db', fontSize: 10 }} />
              <Tooltip formatter={(v: number) => pct(v)} contentStyle={{ background: '#0B0F17', border: '1px solid #374151', fontSize: 11 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="base" name="Base" fill="#374151" />
              <Bar dataKey="current" name="Current" fill="#22d3ee" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="col-span-12 lg:col-span-5 bg-[#111827] border border-gray-800 rounded-lg p-4 text-xs">
          <h3 className="font-semibold text-gray-300 mb-3">Why each weight moved</h3>
          <table className="w-full font-mono">
            <thead className="text-gray-500">
              <tr><th className="text-left">Ticker</th><th className="text-right">Weight</th><th className="text-right">Sentiment</th><th className="text-left pl-3">Reason</th></tr>
            </thead>
            <tbody>
              {bars.map((b) => (
                <tr key={b.ticker} className="border-t border-gray-800">
                  <td className="py-1 text-gray-200">{b.ticker}</td>
                  <td className="text-right text-cyan-300">{pct(b.current)}</td>
                  <td className={`text-right ${b.ema > 0 ? 'text-emerald-400' : b.ema < 0 ? 'text-red-400' : 'text-gray-500'}`}>{b.ema.toFixed(2)}</td>
                  <td className="pl-3 text-gray-400">{current.reasons[b.ticker]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
