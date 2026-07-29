import { AlertTriangle, ChevronRight } from 'lucide-react';
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
  const [scbTab, setScbTab] = useState('A');
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
          A·B·C안의 예상 효과와 위험을 동일한 기준으로 비교합니다. AI는 특정 안을 추천하지 않습니다.
        </p>
      </div>

      <div className="overflow-hidden overflow-x-auto rounded border border-border">
        <table className="w-full min-w-[560px]">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              <th className="w-36 px-5 py-3 text-left font-mono text-xs text-muted-foreground">
                지표
              </th>
              {SCENARIOS.map((sc) => (
                <th key={sc.id} className="border-l border-border px-5 py-3 text-center">
                  <p className="font-mono text-xs font-bold">{sc.id}안</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{sc.type}</p>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {METRIC_ROWS.map((row) => (
              <tr key={row.key} className="border-b border-border last:border-0">
                <td className="px-5 py-3">
                  <p className="text-xs text-muted-foreground">{row.label}</p>
                </td>
                {SCENARIOS.map((sc) => {
                  const val = getValue(sc, row.key);
                  const warn = row.key === 'risk' ? riskColor[sc.riskLevel] : '';
                  return (
                    <td key={sc.id} className="border-l border-border px-5 py-3 text-center">
                      <p className={`font-mono text-sm ${warn}`}>{val}</p>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="space-y-3">
        <div>
          <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
            SCB 연계 심사지표 해석
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            모델 출력(매출·고용·온라인 활동·상권 위치)을 SCB 평가 항목 언어로 설명합니다.
          </p>
        </div>
        <div className="overflow-hidden rounded border border-border">
          <div className="flex border-b border-border">
            {SCENARIOS.map((sc) => (
              <button
                key={sc.id}
                onClick={() => setScbTab(sc.id)}
                className={`flex-1 py-2.5 font-mono text-xs font-bold transition-colors ${
                  scbTab === sc.id
                    ? 'bg-foreground text-background'
                    : 'text-muted-foreground hover:bg-muted/30 hover:text-foreground'
                }`}
              >
                {sc.id}안
              </button>
            ))}
          </div>
          {SCENARIOS.filter((sc) => sc.id === scbTab).map((sc) => (
            <div key={sc.id} className="space-y-3 px-6 py-5">
              <p className="font-mono text-xs text-muted-foreground">{sc.type}</p>
              <div className="space-y-4">
                {sc.scbHints.map((hint) => (
                  <div key={hint} className="flex items-start gap-3">
                    <span className="mt-2 w-1.5 h-1.5 shrink-0 rounded-full bg-primary" />
                    <p className="text-sm leading-relaxed text-foreground">{hint}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {SCENARIOS.map((sc) => (
          <div key={sc.id} className="space-y-3 rounded border border-border p-4">
            <p className="font-mono text-xs font-bold">{sc.id}안 가정 및 위험</p>
            <div className="space-y-1">
              {sc.assumptions.map((a) => (
                <p key={a} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/40" />
                  {a}
                </p>
              ))}
            </div>
            <div className="space-y-1 border-t border-border pt-3">
              {sc.risks.map((r) => (
                <p key={r} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                  <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-amber-500" />
                  {r}
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-end">
        <button
          onClick={onNext}
          className="flex items-center gap-2 rounded bg-foreground px-5 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-90"
        >
          결과 저장 <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};
