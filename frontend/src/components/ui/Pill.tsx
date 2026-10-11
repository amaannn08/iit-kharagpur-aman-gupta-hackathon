import React from 'react';

export interface PillProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'loss' | 'warning' | 'neutral' | 'primary' | 'muted';
  size?: 'sm' | 'md';
  children: React.ReactNode;
}

export const Pill: React.FC<PillProps> = ({
  variant = 'neutral',
  size = 'sm',
  className = '',
  children,
  ...props
}) => {
  const sizeClasses = size === 'sm' ? 'px-2.5 py-0.5 text-[11px]' : 'px-3 py-1 text-xs';

  const variantClasses = {
    success: 'bg-theme-success-bg text-theme-success-dark border border-theme-success/30',
    loss: 'bg-theme-loss-bg text-theme-loss-dark border border-theme-loss/30',
    warning: 'bg-theme-warn-bg text-theme-warn border border-theme-warn/30',
    neutral: 'bg-theme-bg text-theme-text border border-theme-border',
    primary: 'bg-theme-primary-fill text-theme-on-primary border border-theme-primary-fill',
    muted: 'bg-theme-card-subtle text-theme-text-secondary border border-theme-border-subtle',
  }[variant];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium whitespace-nowrap transition-colors ${sizeClasses} ${variantClasses} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
};
