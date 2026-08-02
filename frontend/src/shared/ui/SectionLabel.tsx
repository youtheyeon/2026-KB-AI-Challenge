import type { ReactNode } from 'react';

interface SectionLabelProps {
  children: ReactNode;
  className?: string;
}

export const SectionLabel = ({ children, className = '' }: SectionLabelProps) => (
  <p className={`font-mono text-xs tracking-widest text-muted-foreground uppercase ${className}`}>
    {children}
  </p>
);
