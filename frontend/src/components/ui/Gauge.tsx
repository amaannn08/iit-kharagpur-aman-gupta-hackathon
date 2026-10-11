import React, { useId } from 'react';
import { Cell, Pie, PieChart, ResponsiveContainer } from 'recharts';

export interface GaugeProps {
  eligibleCount: number;
  blockedCount: number;
  duplicateCount: number;
  label?: string;
  className?: string;
}

export const Gauge: React.FC<GaugeProps> = ({
  eligibleCount,
  blockedCount,
  duplicateCount,
  label = 'Action Eligible',
  className = '',
}) => {
  const rawId = useId();
  const hatchId = `gauge-hatch-${rawId.replace(/[^a-zA-Z0-9-_]/g, '')}`;

  const total = eligibleCount + blockedCount + duplicateCount;
  const pct = total > 0 ? Math.round((eligibleCount / total) * 100) : null;

  // Pie segments (ensure at least a minimal dummy slice if total is 0 to draw background arc)
  const data =
    total > 0
      ? [
          { name: 'Eligible', value: eligibleCount },
          { name: 'Blocked', value: blockedCount },
          { name: 'Duplicates', value: duplicateCount },
        ]
      : [{ name: 'Empty', value: 1 }];

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <div className="relative w-full h-40 flex items-center justify-center">
        <ResponsiveContainer width="100%" height={160}>
          <PieChart>
            <defs>
              <pattern
                id={hatchId}
                width="6"
                height="6"
                patternUnits="userSpaceOnUse"
                patternTransform="rotate(45)"
              >
                <line x1="0" y1="0" x2="0" y2="6" stroke="var(--theme-border-strong)" strokeWidth="2" />
                <rect width="6" height="6" fill="var(--theme-card-subtle)" />
              </pattern>
            </defs>
            <Pie
              data={data}
              cx="50%"
              cy="85%"
              startAngle={180}
              endAngle={0}
              innerRadius="68%"
              outerRadius="98%"
              paddingAngle={total > 0 ? 3 : 0}
              dataKey="value"
              stroke="var(--theme-card)"
              strokeWidth={2}
            >
              {total > 0 ? (
                <>
                  <Cell key="cell-0" fill="var(--theme-primary-fill)" />
                  <Cell key="cell-1" fill={`url(#${hatchId})`} stroke="var(--theme-border-strong)" strokeWidth={1} />
                  <Cell key="cell-2" fill="var(--theme-warn)" />
                </>
              ) : (
                <Cell fill="var(--theme-border-light)" />
              )}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {/* Center label inside semicircle */}
        <div className="absolute bottom-2 text-center pointer-events-none select-none">
          <div className="text-3xl font-bold font-mono tracking-tight text-theme-text">
            {pct !== null ? `${pct}%` : '—'}
          </div>
          <div className="text-xs text-theme-muted font-medium">{label}</div>
        </div>
      </div>

      {/* Legend with circular dots */}
      <div className="mt-3 flex flex-wrap items-center justify-center gap-4 text-xs text-theme-text-body">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-theme-primary-fill shrink-0" />
          <span>Eligible ({eligibleCount})</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className="w-2.5 h-2.5 rounded-full border border-theme-border-strong shrink-0"
            style={{
              background:
                'repeating-linear-gradient(45deg, var(--theme-border-strong), var(--theme-border-strong) 2px, var(--theme-card-subtle) 2px, var(--theme-card-subtle) 4px)',
            }}
          />
          <span>Blocked ({blockedCount})</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-theme-warn shrink-0" />
          <span>Duplicates ({duplicateCount})</span>
        </div>
      </div>
    </div>
  );
};
