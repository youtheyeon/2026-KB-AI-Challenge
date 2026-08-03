import { Megaphone, Users, Wrench } from 'lucide-react';

import type { ScenarioResponse } from '@/shared/api/schema';
import { Badge } from '@/shared/ui';

import { CATEGORY_LABELS } from '../model/constants';
import type { AllocationCategory } from '../model/types';

const STRATEGY_ICON: Record<string, typeof Megaphone> = {
  BOTTLENECK_FOCUSED: Megaphone,
  DIAGNOSIS_PROPORTIONAL: Wrench,
  EQUAL_DISTRIBUTION: Users,
};

const STRATEGY_LABEL: Record<string, string> = {
  BOTTLENECK_FOCUSED: '병목 집중형',
  DIAGNOSIS_PROPORTIONAL: '진단 비례 대응형',
  EQUAL_DISTRIBUTION: '균등 분산형',
};

export const ScenarioAllocationCard = ({
  scenario,
  loanAmountWon,
}: {
  scenario: ScenarioResponse;
  loanAmountWon: number;
}) => {
  const Icon = STRATEGY_ICON[scenario.strategyType] ?? Users;
  const total = scenario.allocations.reduce((s, a) => s + a.amount, 0);
  return (
    <div className="overflow-hidden rounded border border-border">
      <div className="space-y-1.5 border-b border-border bg-muted/20 px-4 py-4">
        <div className="flex items-center gap-2">
          <Badge variant="solid">{scenario.scenarioCode}안</Badge>
          <Icon className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">
            {STRATEGY_LABEL[scenario.strategyType] ?? scenario.strategyType}
          </span>
        </div>
        <p className="text-sm font-semibold">{scenario.title}</p>
      </div>
      <div className="divide-y divide-border">
        {scenario.allocations.map((a) => {
          const pct = Math.round((a.amount / loanAmountWon) * 100);
          return (
            <div key={a.category} className="space-y-1.5 px-4 py-2.5">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs">
                  {CATEGORY_LABELS[a.category as AllocationCategory] ?? a.category}
                </p>
                <p className="shrink-0 font-mono text-xs tabular-nums">
                  {Math.round(a.amount / 10_000).toLocaleString()}만원
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
        <p className="font-mono text-sm font-semibold">
          {Math.round(total / 10_000).toLocaleString()}만원
        </p>
      </div>
    </div>
  );
};
