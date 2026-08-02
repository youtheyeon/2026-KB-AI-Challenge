import { AlertTriangle, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';
import { useEffect, useState } from 'react';

import { getSimulation, manwonToWon, wonToManwon } from '@/entities/simulation';
import { ARCHIVED_SIMS, createExecution, DEFAULT_ITEMS } from '@/entities/verify';
import { getApiErrorMessage } from '@/shared/api';
import { ExecutionModeRequest, type SimulationResponse } from '@/shared/api/schema';
import { Button, ErrorBanner } from '@/shared/ui';

interface RecordExecutionStepProps {
  simulationId: number | null;
  onPrev: () => void;
  onNext: () => void;
  onExecutionRegistered: (executionId: number) => void;
}

const EXEC_OPTIONS = [
  { id: 'A', label: 'A안과 동일하게 진행' },
  { id: 'B', label: 'B안과 동일하게 진행' },
  { id: 'C', label: 'C안과 동일하게 진행' },
  { id: 'mix', label: '여러 안을 조합해 진행' },
  { id: 'custom', label: '계획과 다르게 직접 입력' },
] as const;

const EXEC_MODE_TO_REQUEST: Record<string, ExecutionModeRequest> = {
  A: ExecutionModeRequest.SAME_AS_A,
  B: ExecutionModeRequest.SAME_AS_B,
  C: ExecutionModeRequest.SAME_AS_C,
  mix: ExecutionModeRequest.MIXED,
  custom: ExecutionModeRequest.CUSTOM,
};

const todayIso = () => new Date().toISOString().slice(0, 10);

const LoadingView = () => (
  <div className="space-y-6">
    <h2 className="text-xl font-semibold">실제로 대출금을 어떻게 사용했나요?</h2>
    <div className="flex flex-col items-center gap-4 rounded border border-border p-14">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
      <p className="text-sm text-muted-foreground">시뮬레이션 정보를 불러오는 중...</p>
    </div>
  </div>
);

const ErrorView = ({ message, onRetry }: { message: string; onRetry: () => void }) => (
  <div className="space-y-6">
    <h2 className="text-xl font-semibold">실제로 대출금을 어떻게 사용했나요?</h2>
    <div className="flex flex-col items-center gap-4 rounded border border-red-200 bg-red-50 p-14">
      <AlertTriangle className="h-8 w-8 text-red-500" />
      <p className="text-sm text-red-600">{message}</p>
      <Button variant="outline" onClick={onRetry} className="px-4 py-2">
        <RotateCcw className="h-3.5 w-3.5" /> 다시 불러오기
      </Button>
    </div>
  </div>
);

const RealForm = ({
  simulationId,
  simulation,
  onPrev,
  onNext,
  onExecutionRegistered,
}: {
  simulationId: number;
  simulation: SimulationResponse;
  onPrev: () => void;
  onNext: () => void;
  onExecutionRegistered: (executionId: number) => void;
}) => {
  const loanAmountManwon = wonToManwon(simulation.loanCondition.amount);
  const [execMode, setExecMode] = useState<string | null>(null);
  const [execItems, setExecItems] = useState([{ id: '1', name: '', amount: 0 }]);
  const [execDate, setExecDate] = useState(todayIso());
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const totalExec = execItems.reduce((s, i) => s + i.amount, 0);
  const unusedAmount = Math.max(0, loanAmountManwon - totalExec);

  const handleSubmit = async () => {
    if (!execMode) return;
    setCreating(true);
    setCreateError(null);
    try {
      const { executionId } = await createExecution(simulationId, {
        executionMode: EXEC_MODE_TO_REQUEST[execMode],
        executedAt: execDate,
        items: execItems
          .filter((i) => i.name.trim().length > 0)
          .map((i) => ({ name: i.name, amount: manwonToWon(i.amount) })),
        unusedAmount: manwonToWon(unusedAmount),
      });
      onExecutionRegistered(executionId);
      onNext();
    } catch (error) {
      setCreateError(getApiErrorMessage(error));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">실제로 대출금을 어떻게 사용했나요?</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          시뮬레이션의 A·B·C안은 의사결정 참고자료입니다. 실제 진행은 다를 수 있으며, 실제 내역을
          기준으로 예측값을 재계산합니다.
        </p>
      </div>

      <div className="space-y-3">
        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
          진행 방식
        </p>
        <div className="space-y-2">
          {EXEC_OPTIONS.map((opt) => (
            <label
              key={opt.id}
              className={`flex cursor-pointer items-center gap-3 rounded border px-4 py-3 transition-colors ${
                execMode === opt.id
                  ? 'border-foreground bg-foreground/5'
                  : 'border-border hover:border-foreground/30'
              }`}
            >
              <input
                type="radio"
                name="execMode"
                value={opt.id}
                checked={execMode === opt.id}
                onChange={() => setExecMode(opt.id)}
                className="accent-foreground"
              />
              <span className="text-sm">{opt.label}</span>
            </label>
          ))}
        </div>
      </div>

      {execMode && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
              항목별 실제 진행 내역
            </p>
            <p className="font-mono text-xs text-muted-foreground">
              합계 {totalExec.toLocaleString()}만원 / {loanAmountManwon.toLocaleString()}만원
            </p>
          </div>
          <div className="overflow-hidden rounded border border-border">
            <div className="grid grid-cols-12 border-b border-border bg-muted/30 px-5 py-2.5">
              {['항목', '실제 사용액 (만원)', ''].map((h, i) => (
                <p
                  key={h || i}
                  className={`font-mono text-xs text-muted-foreground ${
                    i === 0 ? 'col-span-5' : i === 1 ? 'col-span-5' : 'col-span-2'
                  }`}
                >
                  {h}
                </p>
              ))}
            </div>
            {execItems.map((item) => (
              <div
                key={item.id}
                className="grid grid-cols-12 items-center gap-2 border-b border-border px-5 py-3 last:border-0"
              >
                <input
                  value={item.name}
                  onChange={(e) =>
                    setExecItems((prev) =>
                      prev.map((i) => (i.id === item.id ? { ...i, name: e.target.value } : i)),
                    )
                  }
                  placeholder="예: 주방 설비 교체"
                  className="col-span-5 rounded border border-border bg-background px-2 py-1 text-sm focus:border-foreground focus:outline-none"
                />
                <input
                  type="number"
                  value={item.amount}
                  onChange={(e) =>
                    setExecItems((prev) =>
                      prev.map((i) =>
                        i.id === item.id ? { ...i, amount: Number(e.target.value) } : i,
                      ),
                    )
                  }
                  className="col-span-5 rounded border border-border bg-background px-2 py-1 font-mono text-sm focus:border-foreground focus:outline-none"
                />
                <button
                  onClick={() => setExecItems((prev) => prev.filter((i) => i.id !== item.id))}
                  className="col-span-2 text-right text-xs text-muted-foreground transition-colors hover:text-red-500"
                >
                  제거
                </button>
              </div>
            ))}
            <div className="border-t border-border px-5 py-3">
              <button
                onClick={() =>
                  setExecItems((prev) => [...prev, { id: String(Date.now()), name: '', amount: 0 }])
                }
                className="text-xs text-muted-foreground underline underline-offset-2 transition-colors hover:text-foreground"
              >
                + 항목 추가
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <p className="font-mono text-xs text-muted-foreground">대출 실행일</p>
              <input
                type="date"
                value={execDate}
                onChange={(e) => setExecDate(e.target.value)}
                className="w-full rounded border border-border bg-background px-3 py-2 font-mono text-sm focus:border-foreground focus:outline-none"
              />
            </div>
            <div className="space-y-1.5">
              <p className="font-mono text-xs text-muted-foreground">미사용 금액</p>
              <p className="rounded border border-border bg-muted/20 px-3 py-2 font-mono text-sm">
                {unusedAmount.toLocaleString()}만원
              </p>
            </div>
          </div>

          <div className="rounded border border-border bg-muted/10 px-5 py-4">
            <p className="text-xs text-muted-foreground">
              실제 진행 내역이 시뮬레이션 안과 다를 경우, 실제 진행안을 기준으로 예상값을 재계산한
              뒤 현재 성과와 비교합니다.
            </p>
          </div>
        </div>
      )}

      {createError && <ErrorBanner message={createError} />}

      <div className="flex items-center justify-between">
        <button
          onClick={onPrev}
          className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
          이전
        </button>
        <Button
          onClick={handleSubmit}
          disabled={!execMode || creating}
          className="px-5 py-2.5 disabled:cursor-not-allowed disabled:opacity-30"
        >
          {creating ? '저장 중...' : '진행 내역 저장 후 결과 비교'}{' '}
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};

export const RecordExecutionStep = ({
  simulationId,
  onPrev,
  onNext,
  onExecutionRegistered,
}: RecordExecutionStepProps) => {
  const isRealMode = simulationId != null;

  const [simulation, setSimulation] = useState<SimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    if (!isRealMode || simulationId === null) return;
    let cancelled = false;

    const run = async () => {
      setError(null);
      setSimulation(null);
      try {
        const result = await getSimulation(simulationId);
        if (!cancelled) setSimulation(result);
      } catch (e) {
        if (!cancelled) setError(getApiErrorMessage(e));
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [isRealMode, simulationId, retryToken]);

  if (isRealMode && simulationId !== null) {
    if (error) return <ErrorView message={error} onRetry={() => setRetryToken((t) => t + 1)} />;
    if (!simulation) return <LoadingView />;
    return (
      <RealForm
        simulationId={simulationId}
        simulation={simulation}
        onPrev={onPrev}
        onNext={onNext}
        onExecutionRegistered={onExecutionRegistered}
      />
    );
  }

  const sim = ARCHIVED_SIMS[0];
  return <MockForm sim={sim} onPrev={onPrev} onNext={onNext} />;
};

const MockForm = ({
  sim,
  onPrev,
  onNext,
}: {
  sim: (typeof ARCHIVED_SIMS)[number];
  onPrev: () => void;
  onNext: () => void;
}) => {
  const [execMode, setExecMode] = useState<string | null>(null);
  const [execItems, setExecItems] = useState(DEFAULT_ITEMS);
  const [execDate, setExecDate] = useState('2025.10.20');

  const totalExec = execItems.reduce((s, i) => s + i.amount, 0);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">실제로 대출금을 어떻게 사용했나요?</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          시뮬레이션의 A·B·C안은 의사결정 참고자료입니다. 실제 진행은 다를 수 있으며, 실제 내역을
          기준으로 예측값을 재계산합니다.
        </p>
      </div>

      <div className="space-y-3">
        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
          진행 방식
        </p>
        <div className="space-y-2">
          {EXEC_OPTIONS.map((opt) => (
            <label
              key={opt.id}
              className={`flex cursor-pointer items-center gap-3 rounded border px-4 py-3 transition-colors ${
                execMode === opt.id
                  ? 'border-foreground bg-foreground/5'
                  : 'border-border hover:border-foreground/30'
              }`}
            >
              <input
                type="radio"
                name="execMode"
                value={opt.id}
                checked={execMode === opt.id}
                onChange={() => setExecMode(opt.id)}
                className="accent-foreground"
              />
              <span className="text-sm">{opt.label}</span>
            </label>
          ))}
        </div>
      </div>

      {execMode && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
              항목별 실제 진행 내역
            </p>
            <p className="font-mono text-xs text-muted-foreground">
              합계 {totalExec.toLocaleString()}만원 / {sim.loanAmount.toLocaleString()}만원
            </p>
          </div>
          <div className="overflow-hidden rounded border border-border">
            <div className="grid grid-cols-12 border-b border-border bg-muted/30 px-5 py-2.5">
              {['항목', '실제 사용액 (만원)', ''].map((h, i) => (
                <p
                  key={h || i}
                  className={`font-mono text-xs text-muted-foreground ${
                    i === 0 ? 'col-span-5' : i === 1 ? 'col-span-5' : 'col-span-2'
                  }`}
                >
                  {h}
                </p>
              ))}
            </div>
            {execItems.map((item) => (
              <div
                key={item.id}
                className="grid grid-cols-12 items-center gap-2 border-b border-border px-5 py-3 last:border-0"
              >
                <input
                  value={item.name}
                  onChange={(e) =>
                    setExecItems((prev) =>
                      prev.map((i) => (i.id === item.id ? { ...i, name: e.target.value } : i)),
                    )
                  }
                  className="col-span-5 rounded border border-border bg-background px-2 py-1 text-sm focus:border-foreground focus:outline-none"
                />
                <input
                  type="number"
                  value={item.amount}
                  onChange={(e) =>
                    setExecItems((prev) =>
                      prev.map((i) =>
                        i.id === item.id ? { ...i, amount: Number(e.target.value) } : i,
                      ),
                    )
                  }
                  className="col-span-5 rounded border border-border bg-background px-2 py-1 font-mono text-sm focus:border-foreground focus:outline-none"
                />
                <button
                  onClick={() => setExecItems((prev) => prev.filter((i) => i.id !== item.id))}
                  className="col-span-2 text-right text-xs text-muted-foreground transition-colors hover:text-red-500"
                >
                  제거
                </button>
              </div>
            ))}
            <div className="border-t border-border px-5 py-3">
              <button
                onClick={() =>
                  setExecItems((prev) => [...prev, { id: String(Date.now()), name: '', amount: 0 }])
                }
                className="text-xs text-muted-foreground underline underline-offset-2 transition-colors hover:text-foreground"
              >
                + 항목 추가
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <p className="font-mono text-xs text-muted-foreground">대출 실행일</p>
              <input
                value={execDate}
                onChange={(e) => setExecDate(e.target.value)}
                className="w-full rounded border border-border bg-background px-3 py-2 font-mono text-sm focus:border-foreground focus:outline-none"
              />
            </div>
            <div className="space-y-1.5">
              <p className="font-mono text-xs text-muted-foreground">미사용 금액</p>
              <p className="rounded border border-border bg-muted/20 px-3 py-2 font-mono text-sm">
                {Math.max(0, sim.loanAmount - totalExec).toLocaleString()}만원
              </p>
            </div>
          </div>

          <div className="rounded border border-border bg-muted/10 px-5 py-4">
            <p className="text-xs text-muted-foreground">
              실제 진행 내역이 시뮬레이션 안과 다를 경우, 실제 진행안을 기준으로 예상값을 재계산한
              뒤 현재 성과와 비교합니다.
            </p>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <button
          onClick={onPrev}
          className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
          이전
        </button>
        <Button
          onClick={onNext}
          disabled={!execMode}
          className="px-5 py-2.5 disabled:cursor-not-allowed disabled:opacity-30"
        >
          진행 내역 저장 후 결과 비교 <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};
