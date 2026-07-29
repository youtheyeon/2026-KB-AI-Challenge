import { ChevronDown, ChevronRight, X } from 'lucide-react';
import { useState } from 'react';

import {
  calcMonthly,
  calcPayback,
  riskColor,
  SAMPLE,
  SCENARIOS,
  type LoanCond,
  type Scenario,
} from '@/entities/simulation';
import { Button } from '@/shared/ui';

interface CompareStepProps {
  cond: LoanCond;
  onNext: () => void;
}

const METRIC_ROWS = [
  { key: 'fixedCost', label: '추가 고정비' },
  { key: 'repayment', label: '월 상환금' },
  { key: 'residual', label: '상환 후 여유 현금' },
  { key: 'payback', label: '투자금 회수기간' },
  { key: 'employment', label: '직원 수 변화' },
  { key: 'risk', label: '결과 변동 위험' },
];

export const CompareStep = ({ cond, onNext }: CompareStepProps) => {
  const [selected, setSelected] = useState<string | null>(null);
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
      case 'payback':
        return payback < 200 ? `약 ${payback}개월` : '60개월 이상';
      case 'employment':
        return sc.employees > SAMPLE.employees_n
          ? `+${sc.employees - SAMPLE.employees_n}명`
          : '변화 없음';
      case 'risk':
        return sc.riskLevel;
      default:
        return '-';
    }
  };

  return (
    <div className="space-y-7">
      <div>
        <h2 className="text-xl font-semibold">시나리오 비교</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          A·B·C안의 예상 효과와 위험을 동일한 기준으로 비교합니다.
        </p>
      </div>

      <div className="space-y-3">
        <p className="text-xs text-muted-foreground">
          카드를 눌러 배분 근거와 SCB 성장 가능성을 확인할 수 있습니다.
        </p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {SCENARIOS.map((sc) => {
            const Icon = sc.icon;
            const isSelected = selected === sc.id;
            return (
              <button
                key={sc.id}
                onClick={() => setSelected(isSelected ? null : sc.id)}
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

        {selected &&
          SCENARIOS.filter((sc) => sc.id === selected).map((sc) => (
            <div key={sc.id} className="overflow-hidden rounded border border-foreground">
              <div className="flex items-center justify-between gap-2 border-b border-border bg-muted/20 px-6 py-4">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-foreground px-1.5 py-0.5 font-mono text-xs font-bold text-background">
                    {sc.id}안
                  </span>
                  <p className="text-sm font-semibold">배분 근거 & SCB 성장 가능성</p>
                </div>
                <button
                  onClick={() => setSelected(null)}
                  className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  <X className="h-3.5 w-3.5" />
                  닫기
                </button>
              </div>
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
                  <p className="text-sm leading-relaxed text-foreground">{sc.scbGrowthPotential}</p>
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
