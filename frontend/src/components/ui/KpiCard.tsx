import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import { Card } from './Card';

export interface KpiCardProps {
  title: string;
  value: string | number | null | undefined;
  subtitle?: string | null;
  onNavigate?: () => void;
  variant?: 'default' | 'hero';
  className?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  onNavigate,
  variant = 'default',
  className = '',
}) => {
  const displayVal = value !== null && value !== undefined ? String(value) : '—';

  return (
    <Card variant={variant} className={`flex flex-col justify-between ${className}`}>
      <div className="flex items-start justify-between gap-2">
        <span
          className={`text-xs md:text-sm font-medium tracking-tight ${
            variant === 'hero' ? 'text-theme-hero-subtle' : 'text-theme-muted'
          }`}
        >
          {title}
        </span>
        {onNavigate && (
          <button
            type="button"
            onClick={onNavigate}
            aria-label={`Navigate from ${title}`}
            className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
              variant === 'hero'
                ? 'bg-theme-hero-text/15 text-theme-hero-text hover:bg-theme-hero-text/25 border border-theme-hero-text/20'
                : 'bg-theme-card text-theme-text hover:bg-theme-bg border border-theme-border hover:border-theme-primary'
            }`}
          >
            <ArrowUpRight className="w-4 h-4" />
          </button>
        )}
      </div>

      <div className="mt-4 mb-2">
        <div
          className={`text-3xl md:text-4xl font-bold font-mono tracking-tight ${
            variant === 'hero' ? 'text-theme-hero-text' : 'text-theme-text'
          }`}
        >
          {displayVal}
        </div>
      </div>

      {subtitle && (
        <div className="mt-1 flex items-center gap-1.5">
          <span
            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${
              variant === 'hero'
                ? 'bg-theme-hero-text/20 text-theme-hero-text border border-theme-hero-text/30 backdrop-blur-sm'
                : 'bg-theme-primary-tint text-theme-primary-text border border-theme-primary/30'
            }`}
          >
            {subtitle}
          </span>
        </div>
      )}
    </Card>
  );
};
