import { ChevronRight } from 'lucide-react';

import { SCENARIOS, type LoanCond } from '@/entities/simulation';

interface BuildStepProps {
  cond: LoanCond;
  onNext: () => void;
}

export const BuildStep = ({ cond, onNext }: BuildStepProps) => {
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
        <button
          onClick={onNext}
          className="flex items-center gap-2 rounded bg-foreground px-5 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-90"
        >
          시나리오 비교 <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};
