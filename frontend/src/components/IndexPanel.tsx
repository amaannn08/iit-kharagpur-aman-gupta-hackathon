import { useEffect, useId, useState } from 'react';
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
import { Card } from './ui/Card';
import { Pill } from './ui/Pill';
import { PillButton } from './ui/PillButton';

const DONEZO_PALETTE = [
  '#14532D', '#1F6B45', '#2F9E62', '#52B788', '#7FD1A4', '#A7E3C4',
  '#0F766E', '#14B8A6', '#2DD4BF', '#5EEAD4', '#0284C7', '#38BDF8',
  '#334155', '#475569', '#64748B', '#94A3B8', '#CBD5E1', '#E2E8F0',
  '#15803D', '#166534',
];

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

/** Module A: sentiment-driven mock index. Weights over time is the PS dashboard requirement. */
export function IndexPanel() {
  const [current, setCurrent] = useState<IndexCurrent | null>(null);
  const [history, setHistory] = useState<IndexRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const patternId = useId();

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
    return (
      <Card className="p-8 text-center">
        <p className="text-xs font-semibold text-[#DC2626]">Index unavailable: {error}</p>
      </Card>
    );
  }
  if (!current) {
    return (
      <Card className="p-8 text-center">
        <p className="text-xs font-medium text-[#6B7280]">Loading mock index...</p>
      </Card>
    );
  }

  const tickers = Object.keys(current.weights);
  const series = history.map((r, i) => ({ step: i, label: r.timestamp.slice(0, 16), ...r.weights }));
  const bars = tickers
    .map((t) => ({ ticker: t, current: current.weights[t], base: current.base_weights[t], ema: current.sentiment_ema[t] ?? 0 }))
    .sort((a, b) => b.current - a.current);

  return (
    <div className="flex-1 overflow-y-auto space-y-6" data-testid="index-panel">
      {/* Header bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-[#111827]">Module A: Sentiment-Driven Index Rebalancer</h2>
            <Pill variant="neutral" size="sm">Mock Model</Pill>
          </div>
          <p className="text-xs text-[#6B7280] mt-1 max-w-3xl leading-relaxed">
            {current.label}. Positive sentiment raises a weight, negative lowers it; caps {pct(current.constraints.name_cap)} per
            name, {pct(current.constraints.sector_cap)} per sector; sentiment half-life {current.constraints.halflife_days} days.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Pill variant="primary" size="md">
            {current.rebalances} rebalances
          </Pill>
          <PillButton
            variant="secondary"
            size="sm"
            onClick={async () => {
              await resetIndex();
              refresh();
            }}
          >
            Reset index
          </PillButton>
        </div>
      </div>

      {/* Main Area Chart Card */}
      <Card
        title="Index weights over time"
        subtitle={`Historical rebalance trajectory across ${tickers.length} constituent names`}
      >
        <div className="h-[320px] w-full mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={series} stackOffset="expand">
              <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
              <XAxis
                dataKey="step"
                tick={{ fill: '#6B7280', fontSize: 10, fontFamily: 'Plus Jakarta Sans' }}
                axisLine={{ stroke: '#E5E7EB' }}
                tickLine={false}
                label={{ value: 'rebalance #', fill: '#9CA3AF', fontSize: 10, position: 'insideBottom', offset: -2 }}
              />
              <YAxis
                tickFormatter={(v) => `${Math.round(v * 100)}%`}
                tick={{ fill: '#6B7280', fontSize: 10, fontFamily: 'Plus Jakarta Sans' }}
                axisLine={{ stroke: '#E5E7EB' }}
                tickLine={false}
              />
              <Tooltip
                formatter={(v: number) => pct(v)}
                labelFormatter={(i) => series[Number(i)]?.label ?? i}
                contentStyle={{
                  background: '#FFFFFF',
                  border: '1px solid #ECEDEC',
                  borderRadius: '12px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
                  fontSize: '11px',
                  color: '#111827',
                  fontFamily: 'Plus Jakarta Sans',
                }}
              />
              {tickers.map((t, i) => (
                <Area
                  key={t}
                  type="stepAfter"
                  dataKey={t}
                  stackId="w"
                  stroke="none"
                  fill={DONEZO_PALETTE[i % DONEZO_PALETTE.length]}
                  fillOpacity={0.88}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Lower Dual Cards */}
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-12 lg:col-span-7">
          <Card
            title="Current weight vs base (equal weight)"
            subtitle="Constituent weighting adjusted by sentiment signal"
          >
            <div className="h-[360px] w-full mt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={bars} layout="vertical" margin={{ left: 10, right: 20 }}>
                  <defs>
                    <pattern id={`base-hatch-${patternId}`} width="6" height="6" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
                      <line x1="0" y1="0" x2="0" y2="6" stroke="#D1D5DB" strokeWidth="2" />
                    </pattern>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" horizontal={false} />
                  <XAxis
                    type="number"
                    tickFormatter={(v) => pct(v)}
                    tick={{ fill: '#6B7280', fontSize: 10, fontFamily: 'Plus Jakarta Sans' }}
                    axisLine={{ stroke: '#E5E7EB' }}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="ticker"
                    width={55}
                    tick={{ fill: '#111827', fontSize: 11, fontWeight: 600, fontFamily: 'Plus Jakarta Sans' }}
                    axisLine={{ stroke: '#E5E7EB' }}
                    tickLine={false}
                  />
                  <Tooltip
                    formatter={(v: number) => pct(v)}
                    contentStyle={{
                      background: '#FFFFFF',
                      border: '1px solid #ECEDEC',
                      borderRadius: '12px',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
                      fontSize: '11px',
                      fontFamily: 'Plus Jakarta Sans',
                    }}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 11, paddingTop: 10, fontFamily: 'Plus Jakarta Sans' }}
                  />
                  <Bar
                    dataKey="base"
                    name="Base"
                    fill={`url(#base-hatch-${patternId})`}
                    stroke="#9CA3AF"
                    strokeWidth={1}
                    radius={[0, 4, 4, 0]}
                  />
                  <Bar
                    dataKey="current"
                    name="Current"
                    fill="#1F6B45"
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>

        <div className="col-span-12 lg:col-span-5">
          <Card
            title="Why each weight moved"
            subtitle="Exponential moving average sentiment & attribution"
          >
            <div className="overflow-x-auto mt-2 max-h-[360px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-[#F3F4F6] text-[#6B7280] font-semibold">
                    <th className="text-left pb-2 font-medium">Ticker</th>
                    <th className="text-right pb-2 font-medium">Weight</th>
                    <th className="text-right pb-2 font-medium">Sentiment</th>
                    <th className="text-left pl-3 pb-2 font-medium">Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F3F4F6]">
                  {bars.map((b) => (
                    <tr key={b.ticker} className="hover:bg-[#F9FAFB] transition-colors">
                      <td className="py-2 font-bold text-[#111827]">{b.ticker}</td>
                      <td className="text-right font-semibold text-[#111827]">{pct(b.current)}</td>
                      <td className="text-right">
                        <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          b.ema > 0
                            ? 'bg-[#DCFCE7] text-[#15803D]'
                            : b.ema < 0
                            ? 'bg-[#FEE2E2] text-[#DC2626]'
                            : 'bg-[#F3F4F6] text-[#6B7280]'
                        }`}>
                          {b.ema > 0 ? `+${b.ema.toFixed(2)}` : b.ema.toFixed(2)}
                        </span>
                      </td>
                      <td className="pl-3 py-2 text-[#4B5563] text-[11px] leading-snug">{current.reasons[b.ticker]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
