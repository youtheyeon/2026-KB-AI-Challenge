import { AlertTriangle, ChevronRight, RotateCcw } from 'lucide-react';
import { useEffect, useState } from 'react';

import {
  getSimulation,
  MockScenarioAllocationCard,
  ScenarioAllocationCard,
  SCENARIOS,
  type LoanCond,
} from '@/entities/simulation';
import { getApiErrorMessage } from '@/shared/api';
import type { ScenarioResponse } from '@/shared/api/schema';
import { Button } from '@/shared/ui';

interface BuildStepProps {
  cond: LoanCond;
  businessId: number | null;
  simulationId: number | null;
  onNext: () => void;
}

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
            <ScenarioAllocationCard
              key={sc.scenarioId}
              scenario={sc}
              loanAmountWon={loanAmountWon}
            />
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
        {SCENARIOS.map((sc) => (
          <MockScenarioAllocationCard key={sc.id} scenario={sc} loanAmount={cond.loanAmount} />
        ))}
      </div>
      <div className="flex justify-end">
        <Button onClick={onNext} className="px-5 py-2.5">
          시나리오 비교 <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};
