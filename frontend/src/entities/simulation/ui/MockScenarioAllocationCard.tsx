import { Badge } from '@/shared/ui';

import type { Scenario } from '../model/types';

export const MockScenarioAllocationCard = ({
  scenario,
  loanAmount,
}: {
  scenario: Scenario;
  loanAmount: number;
}) => {
  const Icon = scenario.icon;
  const total = scenario.allocation.reduce((s, a) => s + a.amount, 0);
  return (
    <div className="overflow-hidden rounded border border-border">
      <div className="space-y-1.5 border-b border-border bg-muted/20 px-4 py-4">
        <div className="flex items-center gap-2">
          <Badge variant="solid">{scenario.id}안</Badge>
          <Icon className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">{scenario.type}</span>
        </div>
        <p className="text-sm font-semibold">{scenario.title}</p>
        <p className="text-xs leading-relaxed text-muted-foreground">{scenario.desc}</p>
      </div>
      <div className="divide-y divide-border">
        {scenario.allocation.map((a) => {
          const pct = Math.round((a.amount / loanAmount) * 100);
          return (
            <div key={a.item} className="space-y-1.5 px-4 py-2.5">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-xs">{a.item}</p>
                  <p className="font-mono text-xs text-muted-foreground/60">{a.type}</p>
                </div>
                <p className="shrink-0 font-mono text-xs tabular-nums">
                  {a.amount.toLocaleString()}만원
                </p>
              </div>
              <div className="h-1 overflow-hidden rounded bg-muted">
                <div className="h-full rounded bg-foreground/30" style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex justify-between border-t border-border bg-muted/10 px-4 py-3">
        <p className="font-mono text-xs text-muted-foreground">합계</p>
        <p className="font-mono text-sm font-semibold">{total.toLocaleString()}만원</p>
      </div>
    </div>
  );
};
