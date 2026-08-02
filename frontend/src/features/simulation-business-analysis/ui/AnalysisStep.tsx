import { AlertTriangle, ChevronRight, RotateCcw } from 'lucide-react';
import { useEffect, useState } from 'react';

import { getDiagnosis, startDiagnosis } from '@/entities/business';
import {
  BOTTLENECKS,
  CATEGORY_LABELS,
  sevCfg,
  type BottleneckSeverity,
} from '@/entities/simulation';
import { getApiErrorMessage } from '@/shared/api';
import type { BottleneckResponse, DiagnosisResultResponse } from '@/shared/api/schema';
import { Button } from '@/shared/ui';

type BottleneckPriority = BottleneckResponse['priority'];
type BottleneckConfidence = BottleneckResponse['confidence'];

interface AnalysisStepProps {
  businessId: number | null;
  datasetId: number | null;
  onNext: () => void;
}

interface MetricItem {
  label: string;
  value: string;
  src: string;
  highlight?: boolean;
  warn?: boolean;
}

interface DisplayBottleneck {
  id: string;
  title: string;
  sev: BottleneckSeverity;
  description: string;
  metric?: string;
  confidenceLabel: string;
  sourceLabel?: string;
  relatedCategoryLabels?: string[];
}

const MOCK_FIN: MetricItem[] = [
  { label: '월평균 매출', value: '3,000만원', src: '실제 데이터' },
  { label: '최근 매출 증가율', value: '+2.1%', src: '실제 데이터' },
  { label: '영업이익률', value: '11.0%', src: '계산값' },
  { label: '재료비 원가율', value: '40.0%', src: '실제 데이터', highlight: true },
  { label: '인건비율', value: '28.0%', src: '실제 데이터' },
  { label: '월 여유현금', value: '180만원', src: '계산값' },
];

const MOCK_ACT: MetricItem[] = [
  { label: '월 주문 수', value: '420건', src: '실제 데이터' },
  { label: '객단가', value: '7.1만원', src: '계산값' },
  { label: '직원 수', value: '2명', src: '사용자 입력' },
  { label: '재구매율', value: '34%', src: '추정값', warn: true },
  { label: '온라인 판매 비중', value: '9%', src: '실제 데이터', warn: true },
  { label: '직원당 처리량', value: '210건/월', src: '계산값' },
];

const MOCK_DISTRICT: MetricItem[] = [
  { label: '유동인구 변화', value: '+3.2% (YoY)', src: '비교 데이터' },
  { label: '경쟁점 수', value: '8개 (반경 500m)', src: '비교 데이터' },
  { label: '비교군 대비 매출', value: '-8%', src: '비교 데이터', warn: true },
  { label: '상권 내 성장 추세', value: '보통', src: '비교 데이터' },
];

const SRC_COLOR: Record<string, string> = {
  '실제 데이터': 'text-green-600',
  계산값: 'text-foreground',
  '사용자 입력': 'text-blue-600',
  '비교 데이터': 'text-purple-600',
  추정값: 'text-amber-600',
};

const PRIORITY_TO_SEV: Record<BottleneckPriority, BottleneckSeverity> = {
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
};

const CONFIDENCE_LABEL: Record<BottleneckConfidence, string> = {
  HIGH: '높음',
  MEDIUM: '보통',
  LOW: '낮음',
};

const POLL_INTERVAL_MS = 1500;

const toKrWon = (amount: number) => `${Math.round(amount / 10_000).toLocaleString()}만원`;

const buildFinTiles = (diagnosis: DiagnosisResultResponse): MetricItem[] => {
  if (!diagnosis.financialMetrics) return [];
  const m = diagnosis.financialMetrics;
  return [
    { label: '월 매출', value: toKrWon(m.monthlySalesAmount), src: '실제 데이터' },
    { label: '영업이익률', value: `${m.operatingProfitRate.toFixed(1)}%`, src: '계산값' },
    {
      label: '재료비 원가율',
      value: `${m.materialCostRate.toFixed(1)}%`,
      src: '실제 데이터',
      highlight: m.materialCostRate >= 40,
    },
    { label: '월 여유현금', value: toKrWon(m.cashSurplusAmount), src: '계산값' },
  ];
};

const buildActTiles = (diagnosis: DiagnosisResultResponse): MetricItem[] => {
  if (!diagnosis.activityMetrics) return [];
  const m = diagnosis.activityMetrics;
  const tiles: MetricItem[] = [
    { label: '월 주문 수', value: `${m.monthlyOrderCount.toLocaleString()}건`, src: '실제 데이터' },
    { label: '직원 수', value: `${m.employeeCount}명`, src: '사용자 입력' },
  ];
  if (m.onlineSalesRatio !== null) {
    tiles.push({
      label: '온라인 판매 비중',
      value: `${m.onlineSalesRatio.toFixed(1)}%`,
      src: '실제 데이터',
      warn: m.onlineSalesRatio < 15,
    });
  }
  return tiles;
};

const buildDistrictTiles = (diagnosis: DiagnosisResultResponse): MetricItem[] => {
  if (!diagnosis.commercialMetrics) return [];
  const m = diagnosis.commercialMetrics;
  const tiles: MetricItem[] = [
    {
      label: '비교군 대비 매출',
      value: `${m.salesComparedToPeerRate > 0 ? '+' : ''}${m.salesComparedToPeerRate.toFixed(1)}%`,
      src: '비교 데이터',
      warn: m.salesComparedToPeerRate < 0,
    },
  ];
  if (m.floatingPopulationGrowthRate !== null) {
    tiles.push({
      label: '유동인구 변화',
      value: `${m.floatingPopulationGrowthRate > 0 ? '+' : ''}${m.floatingPopulationGrowthRate.toFixed(1)}%`,
      src: '비교 데이터',
    });
  }
  return tiles;
};

const buildDisplayBottlenecks = (diagnosis: DiagnosisResultResponse): DisplayBottleneck[] =>
  (diagnosis.bottlenecks ?? []).map((b) => ({
    id: b.code,
    title: b.title,
    sev: PRIORITY_TO_SEV[b.priority],
    description: b.evidence,
    confidenceLabel: CONFIDENCE_LABEL[b.confidence],
  }));

const MOCK_DISPLAY_BOTTLENECKS: DisplayBottleneck[] = BOTTLENECKS.map((b) => ({
  id: b.id,
  title: b.label,
  sev: b.sev,
  description: b.desc,
  metric: b.metric,
  confidenceLabel: b.conf,
  sourceLabel: `${b.evidenceSourceType} · ${b.evidenceDescription}`,
  relatedCategoryLabels: b.relatedCategories.map((c) => CATEGORY_LABELS[c]),
}));

const MetricGrid = ({
  title,
  items,
  cols,
}: {
  title: string;
  items: MetricItem[];
  cols: 3 | 4;
}) => {
  if (items.length === 0) return null;
  return (
    <div className="space-y-2">
      <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">{title}</p>
      <div className={`grid grid-cols-2 gap-3 ${cols === 3 ? 'sm:grid-cols-3' : 'sm:grid-cols-4'}`}>
        {items.map((m) => (
          <div key={m.label} className="rounded border border-border px-4 py-4">
            <p className="text-xs text-muted-foreground">{m.label}</p>
            <p
              className={`mt-1 font-mono text-lg font-semibold tabular-nums ${
                m.highlight || m.warn ? 'text-amber-600' : ''
              }`}
            >
              {m.value}
            </p>
            <p
              className={`mt-0.5 font-mono text-xs ${SRC_COLOR[m.src] ?? 'text-muted-foreground'}`}
            >
              {m.src}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

const LoadingView = ({ message }: { message: string }) => (
  <div className="space-y-6">
    <h2 className="text-xl font-semibold">사업 상태 분석 중</h2>
    <div className="flex flex-col items-center gap-4 rounded border border-border p-14">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  </div>
);

const ErrorView = ({ message, onRetry }: { message: string; onRetry: () => void }) => (
  <div className="space-y-6">
    <h2 className="text-xl font-semibold">사업 상태 분석</h2>
    <div className="flex flex-col items-center gap-4 rounded border border-red-200 bg-red-50 p-14">
      <AlertTriangle className="h-8 w-8 text-red-500" />
      <p className="text-sm text-red-600">{message}</p>
      <Button variant="outline" onClick={onRetry} className="px-4 py-2">
        <RotateCcw className="h-3.5 w-3.5" /> 다시 진단하기
      </Button>
    </div>
  </div>
);

const ResultsView = ({
  finTiles,
  actTiles,
  districtTiles,
  bottlenecks,
  onNext,
}: {
  finTiles: MetricItem[];
  actTiles: MetricItem[];
  districtTiles: MetricItem[];
  bottlenecks: DisplayBottleneck[];
  onNext: () => void;
}) => {
  const [showBasis, setShowBasis] = useState<string | null>(null);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold">현재 사업 상태 분석</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          자금 시뮬레이션에 앞서 현재 사업의 재무 상태와 성장 병목 후보를 확인하세요.
        </p>
      </div>

      <MetricGrid title="재무" items={finTiles} cols={3} />
      <MetricGrid title="사업 활동" items={actTiles} cols={3} />
      <MetricGrid title="상권" items={districtTiles} cols={4} />

      <div className="space-y-2">
        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
          확인이 필요한 병목 후보
        </p>
        {bottlenecks.length === 0 && (
          <p className="rounded border border-border px-4 py-6 text-center text-sm text-muted-foreground">
            뚜렷한 병목 후보가 발견되지 않았습니다.
          </p>
        )}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {bottlenecks.map((b) => {
            const cfg = sevCfg[b.sev];
            return (
              <div key={b.id} className="space-y-2 rounded border border-border p-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
                    <p className="text-sm font-medium">{b.title}</p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={`rounded border px-1.5 py-0.5 font-mono text-xs ${cfg.badge}`}>
                      {cfg.label}
                    </span>
                    <span className="font-mono text-xs text-muted-foreground/60">
                      신뢰도 {b.confidenceLabel}
                    </span>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">{b.description}</p>
                {b.relatedCategoryLabels && (
                  <div className="flex flex-wrap gap-1.5">
                    {b.relatedCategoryLabels.map((c) => (
                      <span
                        key={c}
                        className="rounded border border-border bg-muted/40 px-1.5 py-0.5 font-mono text-xs text-muted-foreground"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex items-center justify-between gap-2">
                  {b.metric ? (
                    <p className="flex-1 rounded bg-muted/50 px-2.5 py-1.5 font-mono text-xs">
                      {b.metric}
                    </p>
                  ) : (
                    <span />
                  )}
                  <button
                    onClick={() => setShowBasis(showBasis === b.id ? null : b.id)}
                    className="shrink-0 text-xs text-muted-foreground underline hover:text-foreground"
                  >
                    {showBasis === b.id ? '닫기' : '근거 보기'}
                  </button>
                </div>
                {showBasis === b.id && (
                  <div className="space-y-1 rounded bg-muted/30 px-3 py-2.5">
                    <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                      근거
                    </p>
                    <p className="text-xs leading-relaxed text-muted-foreground">{b.description}</p>
                    {b.sourceLabel && (
                      <p className="font-mono text-xs text-muted-foreground">
                        출처: {b.sourceLabel}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <p className="text-xs text-muted-foreground">
          병목 후보는 분석 후보이며 확정이 아닙니다. 실제 상황과 다를 수 있으며 사용자가 판단을 최종
          확정할 수 있습니다.
        </p>
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {Object.entries(SRC_COLOR).map(([label, color]) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className={`h-1.5 w-1.5 rounded-full ${color.replace('text-', 'bg-')}`} />
            <p className={`font-mono text-xs ${color}`}>{label}</p>
          </div>
        ))}
      </div>

      <div className="flex justify-end">
        <Button onClick={onNext} className="px-5 py-2.5">
          대출 조건 입력 <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};

export const AnalysisStep = ({ businessId, datasetId, onNext }: AnalysisStepProps) => {
  const isRealMode = businessId != null && datasetId != null;

  const [mockLoading, setMockLoading] = useState(true);
  const [diagnosis, setDiagnosis] = useState<DiagnosisResultResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    if (isRealMode) return;
    const t = setTimeout(() => setMockLoading(false), 1800);
    return () => clearTimeout(t);
  }, [isRealMode]);

  useEffect(() => {
    if (!isRealMode || businessId === null || datasetId === null) return;

    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout>;

    const poll = async (diagnosisId: number) => {
      try {
        const result = await getDiagnosis(diagnosisId);
        if (cancelled) return;
        setDiagnosis(result);
        if (result.status === 'RUNNING') {
          timeoutId = setTimeout(() => poll(diagnosisId), POLL_INTERVAL_MS);
        }
      } catch (e) {
        if (!cancelled) {
          setError(getApiErrorMessage(e));
        }
      }
    };

    const run = async () => {
      setError(null);
      setDiagnosis(null);
      try {
        const started = await startDiagnosis(businessId, datasetId);
        if (cancelled) return;
        await poll(started.diagnosisId);
      } catch (e) {
        if (!cancelled) {
          setError(getApiErrorMessage(e));
        }
      }
    };

    run();
    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [isRealMode, businessId, datasetId, retryToken]);

  if (!isRealMode) {
    if (mockLoading) return <LoadingView message="매출·비용·상권 데이터 종합 분석 중..." />;
    return (
      <ResultsView
        finTiles={MOCK_FIN}
        actTiles={MOCK_ACT}
        districtTiles={MOCK_DISTRICT}
        bottlenecks={MOCK_DISPLAY_BOTTLENECKS}
        onNext={onNext}
      />
    );
  }

  if (error) {
    return <ErrorView message={error} onRetry={() => setRetryToken((t) => t + 1)} />;
  }

  if (!diagnosis || diagnosis.status === 'RUNNING') {
    return <LoadingView message="매출·비용·상권 데이터 종합 분석 중..." />;
  }

  if (diagnosis.status === 'FAILED') {
    return (
      <ErrorView
        message="병목 진단에 실패했습니다. 잠시 후 다시 시도해주세요."
        onRetry={() => setRetryToken((t) => t + 1)}
      />
    );
  }

  return (
    <ResultsView
      finTiles={buildFinTiles(diagnosis)}
      actTiles={buildActTiles(diagnosis)}
      districtTiles={buildDistrictTiles(diagnosis)}
      bottlenecks={buildDisplayBottlenecks(diagnosis)}
      onNext={onNext}
    />
  );
};
