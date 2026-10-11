import React from 'react';

export interface PillButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger';
  size?: 'sm' | 'md';
  children: React.ReactNode;
}

export const PillButton: React.FC<PillButtonProps> = ({
  variant = 'primary',
  size = 'md',
  className = '',
  disabled,
  children,
  ...props
}) => {
  const sizeClasses =
    size === 'sm' ? 'px-3 py-1.5 text-xs' : 'px-4 py-2 text-xs md:text-sm font-medium';

  const variantClasses = {
    primary:
      'bg-theme-primary-fill hover:bg-theme-primary-hover text-theme-on-primary shadow-sm border border-theme-primary-fill disabled:opacity-50 disabled:hover:bg-theme-primary-fill',
    secondary:
      'bg-theme-card hover:bg-theme-primary-tint text-theme-primary-text border border-theme-primary-text disabled:opacity-50',
    outline:
      'bg-theme-card hover:bg-theme-bg text-theme-text-body border border-theme-border hover:border-theme-muted disabled:opacity-50',
    danger:
      'bg-theme-loss hover:opacity-90 text-theme-on-primary border border-theme-loss disabled:opacity-50',
  }[variant];

  return (
    <button
      type="button"
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-full cursor-pointer transition-all active:scale-[0.98] select-none ${sizeClasses} ${variantClasses} ${
        disabled ? 'cursor-not-allowed opacity-60' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};
