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
    success: 'bg-[#E8F5EE] text-[#14532D] border border-[#7FD1A4]/50',
    loss: 'bg-[#FEE2E2] text-[#DC2626] border border-red-200',
    warning: 'bg-[#FEF3C7] text-[#B45309] border border-amber-200',
    neutral: 'bg-[#F3F4F3] text-[#374151] border border-[#ECEDEC]',
    primary: 'bg-[#14532D] text-white border border-[#14532D]',
    muted: 'bg-gray-100 text-[#6B7280] border border-gray-200',
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
