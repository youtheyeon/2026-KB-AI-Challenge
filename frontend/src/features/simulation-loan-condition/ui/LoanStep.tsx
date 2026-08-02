import { AlertTriangle, ChevronRight } from 'lucide-react';
import { useState } from 'react';

import {
  calcMonthly,
  createSimulation,
  DEMO_RATE,
  manwonToWon,
  methodToRepaymentType,
  SAMPLE,
  yearsToMonths,
  type LoanCond,
  type LoanRateMode,
} from '@/entities/simulation';
import { getApiErrorMessage } from '@/shared/api';
import { Button, ErrorBanner } from '@/shared/ui';

interface LoanStepProps {
  cond: LoanCond;
  setCond: (c: LoanCond) => void;
  businessId: number | null;
  diagnosisId: number | null;
  onNext: () => void;
  onSimulationCreated: (simulationId: number) => void;
}

const METHODS = [
  { id: 'equal-payment', label: '원리금균등', desc: '매월 동일 금액' },
  { id: 'equal-principal', label: '원금균등', desc: '초기 상환액 높음' },
  { id: 'bullet', label: '만기일시', desc: '만기에 원금 일괄' },
];

export const LoanStep = ({
  cond,
  setCond,
  businessId,
  diagnosisId,
  onNext,
  onSimulationCreated,
}: LoanStepProps) => {
  const isRealMode = businessId != null && diagnosisId != null;
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const set = (p: Partial<LoanCond>) => setCond({ ...cond, ...p });
  const monthly = calcMonthly(cond.loanAmount, cond.rate, cond.period, cond.grace, cond.method);
  const totalMonthly = monthly + cond.existingMonthly;
  const burden = SAMPLE.residual > 0 ? Math.round((totalMonthly / SAMPLE.residual) * 100) : 0;
  const baseResidual = SAMPLE.residual - totalMonthly;

  const handleNext = async () => {
    if (!isRealMode || businessId === null || diagnosisId === null) {
      onNext();
      return;
    }

    setCreating(true);
    setCreateError(null);
    try {
      const { simulationId } = await createSimulation(businessId, {
        diagnosisId,
        loanAmount: manwonToWon(cond.loanAmount),
        annualInterestRate: cond.rate / 100,
        termMonths: yearsToMonths(cond.period),
        graceMonths: yearsToMonths(cond.grace),
        repaymentType: methodToRepaymentType(cond.method),
      });
      onSimulationCreated(simulationId);
      onNext();
    } catch (error) {
      setCreateError(getApiErrorMessage(error));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-7">
      <div>
        <h2 className="text-xl font-semibold">대출 조건 입력</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          월 상환금과 상환 후 현금흐름 계산을 위한 대출 조건을 입력하세요.
        </p>
      </div>

      <div className="space-y-3">
        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
          대출·자금 규모
        </p>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {[
            {
              label: '대출금액 (만원) *',
              val: cond.loanAmount,
              set: (v: number) => set({ loanAmount: v }),
            },
            {
              label: '기존 월 상환액 (만원)',
              val: cond.existingMonthly,
              set: (v: number) => set({ existingMonthly: v }),
            },
          ].map((f) => (
            <div key={f.label} className="space-y-1.5">
              <label className="font-mono text-xs text-muted-foreground">{f.label}</label>
              <input
                type="number"
                value={f.val}
                onChange={(e) => f.set(Number(e.target.value))}
                className="w-full rounded border border-border bg-input-background px-3 py-2 font-mono text-sm focus:border-foreground focus:outline-none"
              />
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
          연 금리 *
        </p>
        <div className="grid grid-cols-2 gap-2">
          {(['demo', 'manual'] as LoanRateMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => set({ rateMode: mode, rate: mode === 'demo' ? DEMO_RATE : cond.rate })}
              className={`rounded border px-4 py-3 text-left transition-colors ${
                cond.rateMode === mode
                  ? 'border-foreground bg-foreground/5'
                  : 'border-border hover:border-foreground/30'
              }`}
            >
              <p className="text-sm font-medium">
                {mode === 'demo' ? '데모 조건 적용' : '직접 입력'}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {mode === 'demo' ? `연 ${DEMO_RATE}% · 시뮬레이션 기준값` : '실제 상담받은 금리'}
              </p>
            </button>
          ))}
        </div>
        {cond.rateMode === 'manual' && (
          <div className="flex items-center gap-3">
            <input
              type="number"
              value={cond.rate}
              step="0.1"
              min="1"
              max="30"
              onChange={(e) => set({ rate: parseFloat(e.target.value) || 0 })}
              className="w-28 rounded border border-border bg-input-background px-3 py-2 font-mono text-sm focus:border-foreground focus:outline-none"
            />
            <span className="text-sm text-muted-foreground">% / 년</span>
          </div>
        )}
        <p className="text-xs text-muted-foreground">
          입력한 대출 조건을 기준으로 계산합니다. 실제 대출심사 결과는 신용 금리를 예측하지
          않습니다.
        </p>
      </div>

      <div className="space-y-3">
        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
          상환 조건
        </p>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {[
            {
              label: '상환 기간 (년) *',
              val: cond.period,
              opts: [1, 2, 3, 5, 7, 10],
              set: (v: number) => set({ period: v }),
            },
            {
              label: '거치 기간 (년)',
              val: cond.grace,
              opts: [0, 1, 2, 3],
              set: (v: number) => set({ grace: v }),
            },
          ].map((f) => (
            <div key={f.label} className="space-y-1.5">
              <label className="font-mono text-xs text-muted-foreground">{f.label}</label>
              <select
                value={f.val}
                onChange={(e) => f.set(Number(e.target.value))}
                className="w-full rounded border border-border bg-input-background px-3 py-2 font-mono text-sm focus:border-foreground focus:outline-none"
              >
                {f.opts.map((y) => (
                  <option key={y} value={y}>
                    {y}년
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {METHODS.map((m) => (
            <button
              key={m.id}
              onClick={() => set({ method: m.id })}
              className={`rounded border p-3 text-left transition-colors ${
                cond.method === m.id
                  ? 'border-foreground bg-foreground/5'
                  : 'border-border hover:border-foreground/30'
              }`}
            >
              <p className="text-sm font-medium">{m.label}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{m.desc}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded border border-border">
        <div className="border-b border-border bg-muted/20 px-5 py-3">
          <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
            입력 즉시 계산
          </p>
        </div>
        <div className="grid grid-cols-2 divide-x divide-border sm:grid-cols-4">
          {[
            { label: '예상 월 상환금', value: `${monthly.toLocaleString()}만원` },
            { label: '기존 포함 합계', value: `${totalMonthly.toLocaleString()}만원` },
            { label: '여유현금 대비 상환 부담', value: `${burden}%`, warn: burden > 60 },
            {
              label: '상환 후 기준 여유 현금',
              value: `${baseResidual >= 0 ? '+' : ''}${baseResidual}만원`,
              warn: baseResidual < 0,
            },
          ].map((k) => (
            <div key={k.label} className="px-4 py-3">
              <p className="text-xs text-muted-foreground">{k.label}</p>
              <p
                className={`mt-1 font-mono text-lg font-semibold tabular-nums ${
                  k.warn ? 'text-red-500' : ''
                }`}
              >
                {k.value}
              </p>
            </div>
          ))}
        </div>
        {burden > 60 && (
          <div className="flex items-center gap-2 border-t border-border bg-red-50 px-5 py-3">
            <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
            <p className="text-xs text-red-600">
              여유현금 대비 상환 부담이 60%를 초과합니다. 사업 성장 없이 상환이 어려워질 수
              있습니다.
            </p>
          </div>
        )}
      </div>

      {createError && <ErrorBanner message={createError} />}

      <div className="flex justify-end">
        <Button
          onClick={handleNext}
          disabled={creating}
          className="px-5 py-2.5 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {creating ? '시뮬레이션 생성 중...' : '자금 배분안 구성'}{' '}
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};
