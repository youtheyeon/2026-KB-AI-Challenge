import { AlertTriangle, ChevronDown, ChevronRight, RotateCcw, X } from 'lucide-react';
import { useEffect, useState } from 'react';

import {
  calcMonthly,
  calcPayback,
  getSimulationComparison,
  riskColor,
  SAMPLE,
  SCENARIOS,
  wonToManwon,
  type LoanCond,
  type RiskLevel,
  type Scenario,
} from '@/entities/simulation';
import { getApiErrorMessage } from '@/shared/api';
import type { ScenarioComparisonResponse, SimulationComparisonResponse } from '@/shared/api/schema';
import { Button } from '@/shared/ui';

interface CompareStepProps {
  cond: LoanCond;
  businessId: number | null;
  simulationId: number | null;
  onNext: () => void;
}

const METRIC_ROWS = [
  { key: 'fixedCost', label: '추가 고정비' },
  { key: 'repayment', label: '월 상환금' },
  { key: 'residual', label: '상환 후 여유 현금' },
  { key: 'breakEven', label: '손익분기 추가매출' },
  { key: 'requiredOrders', label: '필요 추가 주문 수' },
  { key: 'payback', label: '투자금 회수기간' },
  { key: 'risk', label: '결과 변동 위험' },
];

const RISK_LABEL: Record<string, RiskLevel> = {
  LOW: '낮음',
  MEDIUM: '중간',
  HIGH: '높음',
};

const LoadingView = () => (
  <div className="space-y-6">
    <h2 className="text-xl font-semibold">시나리오 비교</h2>
    <div className="flex flex-col items-center gap-4 rounded border border-border p-14">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
      <p className="text-sm text-muted-foreground">시나리오 비교 결과를 불러오는 중...</p>
    </div>
  </div>
);

const ErrorView = ({ message, onRetry }: { message: string; onRetry: () => void }) => (
  <div className="space-y-6">
    <h2 className="text-xl font-semibold">시나리오 비교</h2>
    <div className="flex flex-col items-center gap-4 rounded border border-red-200 bg-red-50 p-14">
      <AlertTriangle className="h-8 w-8 text-red-500" />
      <p className="text-sm text-red-600">{message}</p>
      <Button variant="outline" onClick={onRetry} className="px-4 py-2">
        <RotateCcw className="h-3.5 w-3.5" /> 다시 불러오기
      </Button>
    </div>
  </div>
);

const getRealValue = (sc: ScenarioComparisonResponse, key: string): string => {
  const fr = sc.financialResult;
  switch (key) {
    case 'fixedCost':
      return fr.monthlyRecurringCost != null
        ? `+${wonToManwon(fr.monthlyRecurringCost)}만원/월`
        : '-';
    case 'repayment':
      return fr.monthlyLoanPayment != null ? `${wonToManwon(fr.monthlyLoanPayment)}만원/월` : '-';
    case 'residual':
      return fr.cashAfterPayment != null ? `${wonToManwon(fr.cashAfterPayment)}만원` : '-';
    case 'breakEven':
      return fr.breakEvenAdditionalRevenue != null
        ? `+${wonToManwon(fr.breakEvenAdditionalRevenue)}만원/월`
        : '-';
    case 'requiredOrders':
      return fr.requiredAdditionalOrders != null ? `약 ${fr.requiredAdditionalOrders}건/월` : '-';
    case 'payback':
      return fr.paybackPeriodMonths != null ? `약 ${fr.paybackPeriodMonths}개월` : '-';
    case 'risk':
      return fr.riskLevel ? (RISK_LABEL[fr.riskLevel] ?? fr.riskLevel) : '-';
    default:
      return '-';
  }
};

export const CompareStep = ({ cond, businessId, simulationId, onNext }: CompareStepProps) => {
  const isRealMode = businessId != null && simulationId != null;

  const [expanded, setExpanded] = useState<number | string | null>(null);
  const [comparison, setComparison] = useState<SimulationComparisonResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    if (!isRealMode || simulationId === null) return;
    let cancelled = false;

    const run = async () => {
      setError(null);
      setComparison(null);
      try {
        const result = await getSimulationComparison(simulationId);
        if (!cancelled) setComparison(result);
      } catch (e) {
        if (!cancelled) setError(getApiErrorMessage(e));
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [isRealMode, simulationId, retryToken]);

  const monthly = calcMonthly(cond.loanAmount, cond.rate, cond.period, cond.grace, cond.method);

  const getValue = (sc: Scenario, key: string) => {
    const extraCash =
      Math.round(((SAMPLE.profit * (sc.profitRange[0] + sc.profitRange[1])) / 2 / 100) * 10) -
      sc.addFixed;
    const payback = calcPayback(cond.loanAmount, extraCash);
    const resid = `${sc.residualRange[0]}~${sc.residualRange[1]}만원`;
    switch (key) {
      case 'fixedCost':
        return `+${sc.addFixed}만원/월`;
      case 'repayment':
        return `${monthly}만원/월`;
      case 'residual':
        return resid;
      case 'breakEven':
        return `+${sc.breakEvenAdditionalRevenue}만원/월`;
      case 'requiredOrders':
        return `약 ${sc.requiredAdditionalOrders}건/월`;
      case 'payback':
        return payback < 200 ? `약 ${payback}개월` : '60개월 이상';
      case 'risk':
        return sc.riskLevel;
      default:
        return '-';
    }
  };

  if (isRealMode) {
    if (error) return <ErrorView message={error} onRetry={() => setRetryToken((t) => t + 1)} />;
    if (!comparison) return <LoadingView />;

    return (
      <div className="space-y-7">
        <div>
          <h2 className="text-xl font-semibold">시나리오 비교</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            A·B·C안의 예상 효과와 위험을 동일한 기준으로 비교합니다.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">{comparison.disclaimer}</p>
        </div>

        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            카드를 눌러 배분 근거와 SCB 성장 가능성을 확인하세요. 실제로 어떤 안으로 진행했는지는
            나중에 결과 검증 시 입력합니다.
          </p>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {comparison.scenarios.map((sc) => {
              const isExpanded = expanded === sc.scenarioId;
              return (
                <div
                  key={sc.scenarioId}
                  className="flex flex-col overflow-hidden rounded border border-border text-left transition-colors hover:border-foreground/40"
                >
                  <button
                    onClick={() => setExpanded(isExpanded ? null : sc.scenarioId)}
                    className="space-y-1.5 border-b border-border bg-muted/20 px-4 py-4 text-left"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="rounded bg-foreground px-1.5 py-0.5 font-mono text-xs font-bold text-background">
                        {sc.scenarioCode}안
                      </span>
                      <ChevronDown
                        className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform ${
                          isExpanded ? 'rotate-180' : ''
                        }`}
                      />
                    </div>
                    <p className="text-sm font-semibold">{sc.title}</p>
                  </button>
                  <div className="space-y-2 px-4 py-3">
                    {METRIC_ROWS.map((row) => {
                      const val = getRealValue(sc, row.key);
                      const riskKrLabel = RISK_LABEL[sc.financialResult.riskLevel ?? ''];
                      const warn = row.key === 'risk' && riskKrLabel ? riskColor[riskKrLabel] : '';
                      return (
                        <div key={row.key} className="flex items-center justify-between gap-2">
                          <span className="text-xs text-muted-foreground">{row.label}</span>
                          <span className={`font-mono text-xs ${warn}`}>{val}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          {expanded != null &&
            comparison.scenarios
              .filter((sc) => sc.scenarioId === expanded)
              .map((sc) => (
                <div
                  key={sc.scenarioId}
                  className="overflow-hidden rounded border border-foreground"
                >
                  <div className="flex items-center justify-between gap-2 border-b border-border bg-muted/20 px-6 py-4">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-foreground px-1.5 py-0.5 font-mono text-xs font-bold text-background">
                        {sc.scenarioCode}안
                      </span>
                      <p className="text-sm font-semibold">배분 근거 & SCB 성장 가능성</p>
                    </div>
                    <button
                      onClick={() => setExpanded(null)}
                      className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                    >
                      <X className="h-3.5 w-3.5" />
                      닫기
                    </button>
                  </div>
                  <div className="divide-y divide-border">
                    <div className="grid grid-cols-1 divide-y divide-border md:grid-cols-2 md:divide-x md:divide-y-0">
                      <div className="space-y-2 px-6 py-5">
                        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                          배분 근거
                        </p>
                        <p className="text-sm leading-relaxed text-foreground">
                          {sc.allocationRationale ?? '배분 근거 정보가 없습니다.'}
                        </p>
                      </div>
                      <div className="space-y-2 px-6 py-5">
                        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                          SCB 성장 가능성
                        </p>
                        <p className="text-sm leading-relaxed text-foreground">
                          {sc.scbGrowthOutlook ?? 'SCB 성장 가능성 정보가 없습니다.'}
                        </p>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 divide-y divide-border md:grid-cols-2 md:divide-x md:divide-y-0">
                      <div className="space-y-2 px-6 py-5">
                        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                          위험 근거
                        </p>
                        <ul className="space-y-1">
                          {sc.riskReasons.map((reason) => (
                            <li
                              key={reason}
                              className="text-sm leading-relaxed text-foreground before:mr-1.5 before:text-muted-foreground before:content-['·']"
                            >
                              {reason}
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div className="space-y-2 px-6 py-5">
                        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                          집행 후 확인할 목표 지표
                        </p>
                        <ul className="space-y-1">
                          {sc.targetMetrics.map((metric) => (
                            <li
                              key={metric}
                              className="text-sm leading-relaxed text-foreground before:mr-1.5 before:text-muted-foreground before:content-['·']"
                            >
                              {metric}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
        </div>

        <div className="flex justify-end">
          <Button onClick={onNext} className="px-5 py-2.5">
            결과 저장 <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-7">
      <div>
        <h2 className="text-xl font-semibold">시나리오 비교</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          A·B·C안의 예상 효과와 위험을 동일한 기준으로 비교합니다.
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          본 결과는 현재 사업 상태와 대출 조건을 바탕으로 계산한 재무 비교이며 실제 성과를
          예측하거나 보장하지 않습니다. AI는 특정 배분안을 추천하지 않습니다.
        </p>
      </div>

      <div className="space-y-3">
        <p className="text-xs text-muted-foreground">
          카드를 눌러 배분 근거와 SCB 성장 가능성을 확인할 수 있습니다.
        </p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {SCENARIOS.map((sc) => {
            const Icon = sc.icon;
            const isSelected = expanded === sc.id;
            return (
              <button
                key={sc.id}
                onClick={() => setExpanded(isSelected ? null : sc.id)}
                className={`flex flex-col overflow-hidden rounded border text-left transition-colors ${
                  isSelected ? 'border-foreground' : 'border-border hover:border-foreground/40'
                }`}
              >
                <div className="space-y-1.5 border-b border-border bg-muted/20 px-4 py-4">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-foreground px-1.5 py-0.5 font-mono text-xs font-bold text-background">
                        {sc.id}안
                      </span>
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <span className="text-xs text-muted-foreground">{sc.type}</span>
                    </div>
                    <ChevronDown
                      className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform ${
                        isSelected ? 'rotate-180' : ''
                      }`}
                    />
                  </div>
                  <p className="text-sm font-semibold">{sc.title}</p>
                  <p className="text-xs leading-relaxed text-muted-foreground">{sc.desc}</p>
                </div>
                <div className="space-y-2 px-4 py-3">
                  {METRIC_ROWS.map((row) => {
                    const val = getValue(sc, row.key);
                    const warn = row.key === 'risk' ? riskColor[sc.riskLevel] : '';
                    return (
                      <div key={row.key} className="flex items-center justify-between gap-2">
                        <span className="text-xs text-muted-foreground">{row.label}</span>
                        <span className={`font-mono text-xs ${warn}`}>{val}</span>
                      </div>
                    );
                  })}
                </div>
              </button>
            );
          })}
        </div>

        {expanded &&
          SCENARIOS.filter((sc) => sc.id === expanded).map((sc) => (
            <div key={sc.id} className="overflow-hidden rounded border border-foreground">
              <div className="flex items-center justify-between gap-2 border-b border-border bg-muted/20 px-6 py-4">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-foreground px-1.5 py-0.5 font-mono text-xs font-bold text-background">
                    {sc.id}안
                  </span>
                  <p className="text-sm font-semibold">배분 근거 & SCB 성장 가능성</p>
                </div>
                <button
                  onClick={() => setExpanded(null)}
                  className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  <X className="h-3.5 w-3.5" />
                  닫기
                </button>
              </div>
              <div className="divide-y divide-border">
                <div className="grid grid-cols-1 divide-y divide-border md:grid-cols-2 md:divide-x md:divide-y-0">
                  <div className="space-y-2 px-6 py-5">
                    <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                      배분 근거
                    </p>
                    <p className="text-sm leading-relaxed text-foreground">
                      {sc.allocationRationale}
                    </p>
                  </div>
                  <div className="space-y-2 px-6 py-5">
                    <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                      SCB 성장 가능성
                    </p>
                    <p className="text-sm leading-relaxed text-foreground">
                      {sc.scbGrowthPotential}
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-1 divide-y divide-border md:grid-cols-2 md:divide-x md:divide-y-0">
                  <div className="space-y-2 px-6 py-5">
                    <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                      위험 근거
                    </p>
                    <ul className="space-y-1">
                      {sc.riskReasons.map((reason) => (
                        <li
                          key={reason}
                          className="text-sm leading-relaxed text-foreground before:mr-1.5 before:text-muted-foreground before:content-['·']"
                        >
                          {reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="space-y-2 px-6 py-5">
                    <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                      집행 후 확인할 목표 지표
                    </p>
                    <ul className="space-y-1">
                      {sc.targetMetrics.map((metric) => (
                        <li
                          key={metric}
                          className="text-sm leading-relaxed text-foreground before:mr-1.5 before:text-muted-foreground before:content-['·']"
                        >
                          {metric}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          ))}
      </div>

      <div className="flex justify-end">
        <Button onClick={onNext} className="px-5 py-2.5">
          결과 저장 <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};
