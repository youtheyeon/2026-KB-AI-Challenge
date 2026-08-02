import { AlertTriangle, ChevronRight, Megaphone, RotateCcw, Users, Wrench } from 'lucide-react';
import { useEffect, useState } from 'react';

import {
  CATEGORY_LABELS,
  getSimulation,
  SCENARIOS,
  type AllocationCategory,
  type LoanCond,
} from '@/entities/simulation';
import { getApiErrorMessage } from '@/shared/api';
import type { ScenarioResponse } from '@/shared/api/schema';
import type { IconComponent } from '@/shared/lib/types';
import { Button } from '@/shared/ui';

interface BuildStepProps {
  cond: LoanCond;
  businessId: number | null;
  simulationId: number | null;
  onNext: () => void;
}

const STRATEGY_ICON: Record<string, IconComponent> = {
  BOTTLENECK_FOCUSED: Megaphone,
  DIAGNOSIS_PROPORTIONAL: Wrench,
  EQUAL_DISTRIBUTION: Users,
};

const STRATEGY_LABEL: Record<string, string> = {
  BOTTLENECK_FOCUSED: '병목 집중형',
  DIAGNOSIS_PROPORTIONAL: '진단 비례 대응형',
  EQUAL_DISTRIBUTION: '균등 분산형',
};

const LoadingView = () => (
  <div className="space-y-6">
    <h2 className="text-xl font-semibold">자금 배분안 구성</h2>
    <div className="flex flex-col items-center gap-4 rounded border border-border p-14">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
      <p className="text-sm text-muted-foreground">A·B·C 자금 배분안을 생성하는 중...</p>
    </div>
  </div>
);

const ErrorView = ({ message, onRetry }: { message: string; onRetry: () => void }) => (
  <div className="space-y-6">
    <h2 className="text-xl font-semibold">자금 배분안 구성</h2>
    <div className="flex flex-col items-center gap-4 rounded border border-red-200 bg-red-50 p-14">
      <AlertTriangle className="h-8 w-8 text-red-500" />
      <p className="text-sm text-red-600">{message}</p>
      <Button variant="outline" onClick={onRetry} className="px-4 py-2">
        <RotateCcw className="h-3.5 w-3.5" /> 다시 불러오기
      </Button>
    </div>
  </div>
);

const RealScenarioCard = ({
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
          <span className="rounded bg-foreground px-1.5 py-0.5 font-mono text-xs font-bold text-background">
            {scenario.scenarioCode}안
          </span>
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

export const BuildStep = ({ cond, businessId, simulationId, onNext }: BuildStepProps) => {
  const isRealMode = businessId != null && simulationId != null;

  const [scenarios, setScenarios] = useState<ScenarioResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    if (!isRealMode || simulationId === null) return;
    let cancelled = false;

    const run = async () => {
      setError(null);
      setScenarios(null);
      try {
        const result = await getSimulation(simulationId);
        if (!cancelled) setScenarios(result.scenarios);
      } catch (e) {
        if (!cancelled) setError(getApiErrorMessage(e));
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [isRealMode, simulationId, retryToken]);

  if (isRealMode) {
    if (error) return <ErrorView message={error} onRetry={() => setRetryToken((t) => t + 1)} />;
    if (!scenarios) return <LoadingView />;

    const loanAmountWon = cond.loanAmount * 10_000;
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold">자금 배분안 구성</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            동일한 대출금 {cond.loanAmount.toLocaleString()}만원을 서로 다른 목적으로 배분하는 3가지
            안입니다. 각 안의 합계는 대출금액과 같습니다.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          {scenarios.map((sc) => (
            <RealScenarioCard key={sc.scenarioId} scenario={sc} loanAmountWon={loanAmountWon} />
          ))}
        </div>
        <div className="flex justify-end">
          <Button onClick={onNext} className="px-5 py-2.5">
            시나리오 비교 <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">자금 배분안 구성</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          동일한 대출금 {cond.loanAmount.toLocaleString()}만원을 서로 다른 목적으로 배분하는 3가지
          안입니다. 각 안의 합계는 대출금액과 같습니다.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        {SCENARIOS.map((sc) => {
          const Icon = sc.icon;
          return (
            <div key={sc.id} className="overflow-hidden rounded border border-border">
              <div className="space-y-1.5 border-b border-border bg-muted/20 px-4 py-4">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-foreground px-1.5 py-0.5 font-mono text-xs font-bold text-background">
                    {sc.id}안
                  </span>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">{sc.type}</span>
                </div>
                <p className="text-sm font-semibold">{sc.title}</p>
                <p className="text-xs leading-relaxed text-muted-foreground">{sc.desc}</p>
              </div>
              <div className="divide-y divide-border">
                {sc.allocation.map((a) => {
                  const pct = Math.round((a.amount / cond.loanAmount) * 100);
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
                        <div
                          className="h-full rounded bg-foreground/30"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="flex justify-between border-t border-border bg-muted/10 px-4 py-3">
                <p className="font-mono text-xs text-muted-foreground">합계</p>
                <p className="font-mono text-sm font-semibold">
                  {sc.allocation.reduce((s, a) => s + a.amount, 0).toLocaleString()}만원
                </p>
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex justify-end">
        <Button onClick={onNext} className="px-5 py-2.5">
          시나리오 비교 <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};
