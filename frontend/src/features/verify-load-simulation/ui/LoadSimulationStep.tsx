import { ChevronRight } from 'lucide-react';
import { useState } from 'react';

import { ARCHIVED_SIMS } from '@/entities/verify';
import { Button } from '@/shared/ui';

interface LoadSimulationStepProps {
  onNext: () => void;
}

export const LoadSimulationStep = ({ onNext }: LoadSimulationStepProps) => {
  const [loadedSim, setLoadedSim] = useState<string | null>(null);

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
