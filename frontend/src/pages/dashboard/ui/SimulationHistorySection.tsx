import { AlertTriangle, CheckCircle2 } from 'lucide-react';

import { wonToManwon } from '@/entities/simulation';
import { outcomeCfg, SIMULATION_HISTORY } from '@/entities/verify';
import type { CycleHistoryResponse } from '@/shared/api/schema';
import { Badge, SectionLabel } from '@/shared/ui';

const OVERALL_STATUS_BADGE: Record<string, string> = {
  MET: 'bg-green-50 border-green-200 text-green-600',
  PARTIALLY_MET: 'bg-amber-50 border-amber-200 text-amber-700',
  NOT_MET: 'bg-red-50 border-red-200 text-red-600',
  NOT_COMPARABLE: 'bg-secondary border-border text-muted-foreground',
};

const OVERALL_STATUS_LABEL: Record<string, string> = {
  MET: '목표 달성',
  PARTIALLY_MET: '부분 달성',
  NOT_MET: '목표 미달',
  NOT_COMPARABLE: '비교 불가',
};

const EXEC_MODE_LABEL: Record<string, string> = {
  SAME_AS_A: 'A안과 동일',
  SAME_AS_B: 'B안과 동일',
  SAME_AS_C: 'C안과 동일',
  MIXED: '여러 안 조합',
  CUSTOM: '직접 입력',
};

interface SimulationHistorySectionProps {
  isRealMode: boolean;
  cycleHistories: CycleHistoryResponse[] | null;
}

export const SimulationHistorySection = ({
  isRealMode,
  cycleHistories,
}: SimulationHistorySectionProps) => {
  if (isRealMode) {
    if (!cycleHistories || cycleHistories.length === 0) {
      return (
        <section className="space-y-4">
          <SectionLabel>시뮬레이션 이력</SectionLabel>
          <div className="rounded border border-border px-5 py-8 text-center text-sm text-muted-foreground">
            아직 완료된 시뮬레이션 이력이 없습니다.
          </div>
        </section>
      );
    }

    return (
      <section className="space-y-4">
        <SectionLabel>시뮬레이션 이력</SectionLabel>
        <div className="space-y-4">
          {cycleHistories.map((h) => (
            <div key={h.simulationId} className="overflow-hidden rounded border border-border">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted/10 px-5 py-4">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-muted-foreground">
                    {new Date(h.simulatedAt).toLocaleDateString('ko-KR')}
                  </span>
                  {h.selectedPlan && (
                    <>
                      <span className="rounded bg-foreground px-1.5 py-0.5 font-mono text-xs font-bold text-background">
                        {h.selectedPlan.scenarioCode}안
                      </span>
                      <p className="text-sm font-medium">{h.selectedPlan.title}</p>
                    </>
                  )}
                </div>
                <Badge className={OVERALL_STATUS_BADGE[h.outcome.overallStatus] ?? ''}>
                  {OVERALL_STATUS_LABEL[h.outcome.overallStatus] ?? h.outcome.overallStatus}
                </Badge>
              </div>
              <div className="px-5 py-4 text-xs text-muted-foreground">
                {h.execution ? (
                  <p>
                    실행: {EXEC_MODE_LABEL[h.execution.executionMode] ?? h.execution.executionMode}{' '}
                    · {wonToManwon(h.execution.totalExecutedAmount).toLocaleString()}만원 집행
                  </p>
                ) : (
                  <p>실제 진행 내역이 등록되지 않았습니다.</p>
                )}
                <p className="mt-1">
                  결과 확인일: {new Date(h.outcome.completedAt).toLocaleDateString('ko-KR')}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <SectionLabel>시뮬레이션 이력</SectionLabel>
      <div className="space-y-4">
        {SIMULATION_HISTORY.map((h) => {
          const cfg = outcomeCfg[h.outcome];
          const rows = [
            { label: '순매출', plan: h.revenue.plan, actual: h.revenue.actual },
            { label: '영업이익', plan: h.profit.plan, actual: h.profit.actual },
            { label: '상환 후 여유', plan: h.residual.plan, actual: h.residual.actual },
          ];
          return (
            <div key={h.id} className="overflow-hidden rounded border border-border">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted/10 px-5 py-4">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-muted-foreground">{h.round}회차</span>
                  <span className="rounded bg-foreground px-1.5 py-0.5 font-mono text-xs font-bold text-background">
                    {h.scenarioCode}안
                  </span>
                  <p className="text-sm font-medium">{h.planLabel}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-muted-foreground">{h.period}</span>
                  <Badge className={cfg.badge} icon={cfg.icon}>
                    {cfg.label}
                  </Badge>
                </div>
              </div>
              <div className="grid grid-cols-1 divide-y divide-border sm:grid-cols-3 sm:divide-x sm:divide-y-0">
                {rows.map((r) => (
                  <div key={r.label} className="px-5 py-4">
                    <p className="text-xs text-muted-foreground">{r.label}</p>
                    <div className="mt-1 flex items-baseline gap-2">
                      <p className="font-mono text-sm font-semibold">{r.actual}</p>
                      <p className="font-mono text-xs text-muted-foreground">계획 {r.plan}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-1 gap-3 border-t border-border px-5 py-3 sm:grid-cols-2">
                <div className="space-y-1">
                  <p className="font-mono text-xs text-muted-foreground">해결된 병목</p>
                  {h.bottleneckResolved.map((b) => (
                    <div key={b} className="flex items-center gap-1.5 text-xs text-green-600">
                      <CheckCircle2 className="h-3 w-3 shrink-0" />
                      {b}
                    </div>
                  ))}
                </div>
                <div className="space-y-1">
                  <p className="font-mono text-xs text-muted-foreground">미해결 병목</p>
                  {h.bottleneckRemaining.map((b) => (
                    <div key={b} className="flex items-center gap-1.5 text-xs text-amber-600">
                      <AlertTriangle className="h-3 w-3 shrink-0" />
                      {b}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};
