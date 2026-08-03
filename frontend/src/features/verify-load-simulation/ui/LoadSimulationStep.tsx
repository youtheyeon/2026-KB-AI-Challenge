import { AlertTriangle, ChevronRight, RotateCcw } from 'lucide-react';
import { useEffect, useState } from 'react';

import { ARCHIVED_SIMS, getVerificationTargets } from '@/entities/verify';
import { getApiErrorMessage } from '@/shared/api';
import type { VerificationTargetResponse } from '@/shared/api/schema';
import { Button } from '@/shared/ui';

interface LoadSimulationStepProps {
  businessId: number | null;
  onNext: () => void;
  onSimulationSelected: (simulationId: number) => void;
}

const LoadingView = () => (
  <div className="space-y-6">
    <h2 className="text-xl font-semibold">어떤 시뮬레이션을 기준으로 결과를 확인할까요?</h2>
    <div className="flex flex-col items-center gap-4 rounded border border-border p-14">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
      <p className="text-sm text-muted-foreground">검증 가능한 시뮬레이션을 불러오는 중...</p>
    </div>
  </div>
);

const ErrorView = ({ message, onRetry }: { message: string; onRetry: () => void }) => (
  <div className="space-y-6">
    <h2 className="text-xl font-semibold">어떤 시뮬레이션을 기준으로 결과를 확인할까요?</h2>
    <div className="flex flex-col items-center gap-4 rounded border border-red-200 bg-red-50 p-14">
      <AlertTriangle className="h-8 w-8 text-red-500" />
      <p className="text-sm text-red-600">{message}</p>
      <Button variant="outline" onClick={onRetry} className="px-4 py-2">
        <RotateCcw className="h-3.5 w-3.5" /> 다시 불러오기
      </Button>
    </div>
  </div>
);

const EmptyView = () => (
  <div className="space-y-6">
    <h2 className="text-xl font-semibold">어떤 시뮬레이션을 기준으로 결과를 확인할까요?</h2>
    <div className="space-y-2 rounded border border-border px-5 py-14 text-center">
      <p className="text-sm text-muted-foreground">아직 검증 가능한 시뮬레이션이 없습니다.</p>
      <p className="text-xs text-muted-foreground">
        시뮬레이션을 저장한 뒤 90일이 지나야 실제 집행 내역을 등록하고 결과를 검증할 수 있습니다.
      </p>
    </div>
  </div>
);

const RealTargetList = ({
  targets,
  onNext,
  onSimulationSelected,
}: {
  targets: VerificationTargetResponse[];
  onNext: () => void;
  onSimulationSelected: (simulationId: number) => void;
}) => {
  const [loadedId, setLoadedId] = useState<number | null>(null);

  const handleNext = () => {
    if (loadedId === null) return;
    onSimulationSelected(loadedId);
    onNext();
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">어떤 시뮬레이션을 기준으로 결과를 확인할까요?</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          저장된 시뮬레이션을 불러와 실제 진행 내역과 비교합니다.
        </p>
      </div>

      <div className="space-y-3">
        {targets.map((t) => {
          const isLoaded = loadedId === t.simulationId;
          return (
            <div
              key={t.simulationId}
              className={`overflow-hidden rounded border transition-colors ${
                isLoaded ? 'border-foreground' : 'border-border'
              }`}
            >
              <div className="flex flex-col gap-2 px-5 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs text-muted-foreground">
                        {new Date(t.savedAt).toLocaleDateString('ko-KR')}
                      </span>
                      <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground">
                        {t.daysElapsed}일 경과
                      </span>
                      <span className="rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 font-mono text-xs text-amber-700">
                        {t.executionRegistered ? '진행 등록됨' : '진행 미등록'}
                      </span>
                    </div>
                    <p className="text-sm font-medium">
                      {t.businessName} · {t.region}
                    </p>
                    <p className="font-mono text-xs text-muted-foreground">
                      대출금 {Math.round(t.loanAmount / 10_000).toLocaleString()}만원
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col gap-2">
                    <button
                      onClick={() => setLoadedId(isLoaded ? null : t.simulationId)}
                      className={`rounded px-4 py-2 text-sm font-medium transition-colors ${
                        isLoaded
                          ? 'bg-foreground text-background'
                          : 'border border-border hover:border-foreground/40'
                      }`}
                    >
                      {isLoaded ? '✓ 불러옴' : '이 시뮬레이션 불러오기'}
                    </button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {t.planSummaries.map((p) => (
                    <span
                      key={p.planCode}
                      className="rounded bg-muted px-2 py-0.5 font-mono text-xs text-muted-foreground"
                    >
                      {p.planCode}. {p.title}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex justify-end">
        <Button
          onClick={handleNext}
          disabled={loadedId === null}
          className="px-5 py-2.5 disabled:cursor-not-allowed disabled:opacity-30"
        >
          실제 진행 등록 <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};

export const LoadSimulationStep = ({
  businessId,
  onNext,
  onSimulationSelected,
}: LoadSimulationStepProps) => {
  const isRealMode = businessId != null;

  const [targets, setTargets] = useState<VerificationTargetResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);
  const [loadedSim, setLoadedSim] = useState<string | null>(null);

  useEffect(() => {
    if (!isRealMode || businessId === null) return;
    let cancelled = false;

    const run = async () => {
      setError(null);
      setTargets(null);
      try {
        const result = await getVerificationTargets(businessId);
        if (!cancelled) setTargets(result.targets);
      } catch (e) {
        if (!cancelled) setError(getApiErrorMessage(e));
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [isRealMode, businessId, retryToken]);

  if (isRealMode) {
    if (error) return <ErrorView message={error} onRetry={() => setRetryToken((t) => t + 1)} />;
    if (!targets) return <LoadingView />;
    if (targets.length === 0) return <EmptyView />;
    return (
      <RealTargetList
        targets={targets}
        onNext={onNext}
        onSimulationSelected={onSimulationSelected}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">어떤 시뮬레이션을 기준으로 결과를 확인할까요?</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          저장된 시뮬레이션을 불러와 실제 진행 내역과 비교합니다.
        </p>
      </div>

      <div className="space-y-3">
        {ARCHIVED_SIMS.map((s) => {
          const isLoaded = loadedSim === s.id;
          return (
            <div
              key={s.id}
              className={`overflow-hidden rounded border transition-colors ${
                isLoaded ? 'border-foreground' : 'border-border'
              }`}
            >
              <div className="flex flex-col gap-2 px-5 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs text-muted-foreground">{s.date}</span>
                      <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground">
                        {s.daysAgo}일 경과
                      </span>
                      <span className="rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 font-mono text-xs text-amber-700">
                        {s.status}
                      </span>
                    </div>
                    <p className="text-sm font-medium">{s.biz}</p>
                    <p className="font-mono text-xs text-muted-foreground">
                      대출금 {s.loanAmount.toLocaleString()}만원
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col gap-2">
                    <button
                      onClick={() => setLoadedSim(isLoaded ? null : s.id)}
                      className={`rounded px-4 py-2 text-sm font-medium transition-colors ${
                        isLoaded
                          ? 'bg-foreground text-background'
                          : 'border border-border hover:border-foreground/40'
                      }`}
                    >
                      {isLoaded ? '✓ 불러옴' : '이 시뮬레이션 불러오기'}
                    </button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {s.scenarios.map((sc) => (
                    <span
                      key={sc}
                      className="rounded bg-muted px-2 py-0.5 font-mono text-xs text-muted-foreground"
                    >
                      {sc}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex justify-end">
        <Button
          onClick={onNext}
          disabled={!loadedSim}
          className="px-5 py-2.5 disabled:cursor-not-allowed disabled:opacity-30"
        >
          실제 진행 등록 <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};
