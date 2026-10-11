import React, { useId } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

export interface PillBarChartDataPoint {
  name: string;
  eligible: number;
  blocked: number;
  [key: string]: string | number;
}

export interface PillBarChartProps {
  data: PillBarChartDataPoint[];
  height?: number;
  className?: string;
}

export const PillBarChart: React.FC<PillBarChartProps> = ({
  data,
  height = 240,
  className = '',
}) => {
  const rawId = useId();
  // Sanitize useId for SVG id attribute
  const hatchId = `hatch-${rawId.replace(/[^a-zA-Z0-9-_]/g, '')}`;

  return (
    <div className={`w-full ${className}`}>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          margin={{ top: 16, right: 12, left: -20, bottom: 8 }}
          barCategoryGap="22%"
          barGap={6}
        >
          <defs>
            <pattern
              id={hatchId}
              width="8"
              height="8"
              patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)"
            >
              <line x1="0" y1="0" x2="0" y2="8" stroke="var(--theme-chart-hatch)" strokeWidth="2.5" />
              <rect width="8" height="8" fill="var(--theme-primary-tint)" opacity="0.35" />
            </pattern>
          </defs>

          <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--theme-border)" />

          <XAxis
            dataKey="name"
            tick={{ fill: 'var(--theme-muted)', fontSize: 11, fontWeight: 500 }}
            tickLine={false}
            axisLine={{ stroke: 'var(--theme-border)' }}
          />

          <YAxis
            tick={{ fill: 'var(--theme-muted)', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
          />

          <Tooltip
            cursor={{ fill: 'var(--theme-cursor-fill)', radius: 8 }}
            content={({ active, payload, label }) => {
              if (active && payload && payload.length) {
                const el = Number(payload.find((p) => p.dataKey === 'eligible')?.value ?? 0);
                const bl = Number(payload.find((p) => p.dataKey === 'blocked')?.value ?? 0);
                const tot = el + bl;
                const pct = tot > 0 ? Math.round((el / tot) * 100) : 0;

                return (
                  <div className="bg-theme-card border border-theme-border shadow-md rounded-xl px-3 py-2 text-xs">
                    <div className="font-bold text-theme-text mb-1">{label}</div>
                    <div className="flex items-center gap-2 text-theme-primary-text">
                      <span className="w-2 h-2 rounded-full bg-theme-primary" />
                      <span>Action Eligible: {el}</span>
                    </div>
                    <div className="flex items-center gap-2 text-theme-muted">
                      <span className="w-2 h-2 rounded-full bg-theme-chart-hatch" />
                      <span>Blocked: {bl}</span>
                    </div>
                    <div className="mt-1 pt-1 border-t border-theme-border-subtle font-semibold text-theme-primary-text">
                      Eligible Rate: {pct}%
                    </div>
                  </div>
                );
              }
              return null;
            }}
          />

          <Legend
            verticalAlign="top"
            align="right"
            iconType="circle"
            wrapperStyle={{ paddingBottom: 12, fontSize: 11 }}
            formatter={(val) => (
              <span className="text-theme-text-body font-medium capitalize">
                {val === 'eligible' ? 'Action Eligible' : 'Blocked'}
              </span>
            )}
          />

          {/* Pill-shaped solid bar for Action Eligible */}
          <Bar
            dataKey="eligible"
            fill="var(--theme-primary)"
            radius={[12, 12, 12, 12]}
            name="eligible"
          />

          {/* Pill-shaped hatched bar for Blocked */}
          <Bar
            dataKey="blocked"
            fill={`url(#${hatchId})`}
            stroke="var(--theme-primary-light)"
            strokeWidth={1}
            radius={[12, 12, 12, 12]}
            name="blocked"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
