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
      'bg-[#14532D] hover:bg-[#1F6B45] text-white shadow-sm border border-[#14532D] disabled:opacity-50 disabled:hover:bg-[#14532D]',
    secondary:
      'bg-white hover:bg-[#E8F5EE] text-[#14532D] border border-[#14532D] disabled:opacity-50',
    outline:
      'bg-white hover:bg-[#F3F4F3] text-[#374151] border border-[#ECEDEC] hover:border-gray-300 disabled:opacity-50',
    danger:
      'bg-[#DC2626] hover:bg-red-700 text-white border border-[#DC2626] disabled:opacity-50',
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
