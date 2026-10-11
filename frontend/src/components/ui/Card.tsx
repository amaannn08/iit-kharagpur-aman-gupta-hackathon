import React from 'react';

export interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  variant?: 'default' | 'hero';
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({
  variant = 'default',
  title,
  subtitle,
  action,
  className = '',
  children,
  ...props
}) => {
  if (variant === 'hero') {
    return (
      <div
        className={`relative overflow-hidden rounded-[20px] bg-gradient-to-br from-theme-hero-from to-theme-hero-to text-theme-hero-text p-5 md:p-6 shadow-[0_4px_20px_rgba(20,83,45,0.18)] ${className}`}
        {...props}
      >
        {/* Subtle decorative wave pattern */}
        <svg
          className="absolute -right-12 -bottom-12 w-64 h-64 opacity-15 pointer-events-none select-none text-current"
          viewBox="0 0 200 200"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M20 180C60 120 100 220 140 160C180 100 220 140 240 120"
            stroke="currentColor"
            strokeWidth="14"
            strokeLinecap="round"
          />
          <path
            d="M0 140C40 80 80 180 120 120C160 60 200 100 220 80"
            stroke="currentColor"
            strokeWidth="10"
            strokeLinecap="round"
          />
          <path
            d="M-20 100C20 40 60 140 100 80C140 20 180 60 200 40"
            stroke="currentColor"
            strokeWidth="6"
            strokeLinecap="round"
          />
        </svg>
        <div className="relative z-10">
          {(title || subtitle || action) && (
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                {title && (
                  typeof title === 'string' ? (
                    <h3 className="text-sm font-bold text-theme-hero-text tracking-tight">{title}</h3>
                  ) : title
                )}
                {subtitle && (
                  typeof subtitle === 'string' ? (
                    <p className="text-xs text-theme-hero-subtle mt-0.5">{subtitle}</p>
                  ) : subtitle
                )}
              </div>
              {action && <div>{action}</div>}
            </div>
          )}
          {children}
        </div>
      </div>
    );
  }

  return (
    <div
      className={`rounded-[20px] bg-theme-card border border-theme-border shadow-[0_2px_12px_rgba(0,0,0,0.03)] p-5 md:p-6 text-theme-text ${className}`}
      {...props}
    >
      {(title || subtitle || action) && (
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            {title && (
              typeof title === 'string' ? (
                <h3 className="text-sm font-bold text-theme-text tracking-tight">{title}</h3>
              ) : title
            )}
            {subtitle && (
              typeof subtitle === 'string' ? (
                <p className="text-xs text-theme-muted mt-0.5">{subtitle}</p>
              ) : subtitle
            )}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
};
