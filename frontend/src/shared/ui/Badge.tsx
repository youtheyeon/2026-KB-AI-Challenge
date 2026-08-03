import type { ReactNode } from 'react';

import type { IconComponent } from '@/shared/lib/types';

interface BadgeProps {
  children: ReactNode;
  className?: string;
  icon?: IconComponent;
  variant?: 'outline' | 'solid';
}

const VARIANT_CLASS: Record<NonNullable<BadgeProps['variant']>, string> = {
  outline: 'border',
  solid: 'border-0 bg-foreground font-bold text-background',
};

export const Badge = ({
  children,
  className = '',
  icon: Icon,
  variant = 'outline',
}: BadgeProps) => (
  <span
    className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-xs ${VARIANT_CLASS[variant]} ${className}`}
  >
    {Icon && <Icon className="h-3 w-3" />}
    {children}
  </span>
);
