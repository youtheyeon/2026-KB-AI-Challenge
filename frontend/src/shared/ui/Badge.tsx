import type { ReactNode } from 'react';

import type { IconComponent } from '@/shared/lib/types';

interface BadgeProps {
  children: ReactNode;
  className?: string;
  icon?: IconComponent;
}

export const Badge = ({ children, className = '', icon: Icon }: BadgeProps) => (
  <span
    className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-xs ${className}`}
  >
    {Icon && <Icon className="h-3 w-3" />}
    {children}
  </span>
);
