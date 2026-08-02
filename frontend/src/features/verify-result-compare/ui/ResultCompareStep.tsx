import {
  AlertTriangle,
  ArrowRight,
  BarChart2,
  CheckCircle2,
  ChevronLeft,
  FileText,
  LayoutGrid,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Upload,
} from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import {
  COMPARE_ROWS,
  createOutcome,
  createOutcomeData,
  getOutcome,
  NEW_BOTTLENECKS,
  REEVAL_METRICS,
  RESOLVED,
  statusCfg,
  TREND_DATA,
  type ManualOutcomeMetricsRequest,
} from '@/entities/verify';
import { getApiErrorMessage } from '@/shared/api';
import type { ComparisonRowResponse, OutcomeResultResponse } from '@/shared/api/schema';
import { ROUTES } from '@/shared/config/routes';
import { Button, ErrorBanner } from '@/shared/ui';

type DataMode = 'mock' | 'upload' | 'manual';

const DATA_SOURCE_OPTIONS: {
  id: DataMode;
  icon: typeof LayoutGrid;
  title: string;
  desc: string;
}[] = [
  {
    id: 'mock',
    icon: LayoutGrid,
    title: 'Mock 데이터로 체험',
    desc: '3개월 후 가상 데이터를 자동 생성합니다.',
  },
  {
    id: 'upload',
    icon: Upload,
    title: '최신 파일 업로드',
    desc: '최신 매출·비용 CSV 또는 엑셀을 업로드합니다.',
  },
  {
    id: 'manual',
    icon: FileText,
    title: '핵심 지표 직접 입력',
    desc: '매출·이익·온라인비중 등 핵심 지표를 직접 입력합니다.',
  },
];

const MANUAL_FIELDS: {
  key: keyof ManualOutcomeMetricsRequest;
  label: string;
  placeholder: string;
  toRequest: (input: number) => number;
}[] = [
  {
    key: 'monthlySalesAmount',
    label: '월평균 매출 (만원)',
    placeholder: '3210',
    toRequest: (v) => v * 10_000,
  },
  {
    key: 'operatingProfitAmount',
    label: '영업이익 (만원)',
    placeholder: '352',
    toRequest: (v) => v * 10_000,
  },
  {
    key: 'onlineOrderRatio',
    label: '온라인 주문 비중 (%)',
    placeholder: '13',
    toRequest: (v) => v / 100,
  },
  {
    key: 'cashAfterRepaymentAmount',
    label: '상환 후 여유현금 (만원)',
    placeholder: '198',
    toRequest: (v) => v * 10_000,
  },
];

const STATUS_LABEL: Record<string, string> = {
  ABOVE_EXPECTED: '예상 상단 초과',
  WITHIN_RANGE: '범위 내',
  BELOW_EXPECTED: '범위 미달',
  NOT_COMPARABLE: '비교 불가',
};

const STATUS_BADGE: Record<string, string> = {
  ABOVE_EXPECTED: 'bg-blue-50 border-blue-200 text-blue-600',
  WITHIN_RANGE: 'bg-green-50 border-green-200 text-green-600',
  BELOW_EXPECTED: 'bg-red-50 border-red-200 text-red-600',
  NOT_COMPARABLE: 'bg-secondary border-border text-muted-foreground',
};

const OVERALL_STATUS_LABEL: Record<string, string> = {
  MET: '목표 달성',
  PARTIALLY_MET: '부분 달성',
  NOT_MET: '목표 미달',
  NOT_COMPARABLE: '비교 불가',
};

const CHANGE_TYPE_LABEL: Record<string, string> = {
  RESOLVED: '개선됨',
  REMAINING: '지속',
  NEW: '신규',
};

const formatMetricValue = (value: number | null, unit: string): string => {
  if (value === null) return '-';
  if (unit === 'RATIO') return `${(value * 100).toFixed(1)}%`;
  if (unit === 'KRW') return `${Math.round(value / 10_000).toLocaleString()}만원`;
  return value.toLocaleString();
};

interface ResultCompareStepProps {
  businessId: number | null;
  simulationId: number | null;
  executionId: number | null;
  onPrev: () => void;
}

const RealComparisonTable = ({ rows }: { rows: ComparisonRowResponse[] }) => (
  <div className="overflow-hidden rounded border border-border">
    <div className="grid grid-cols-12 border-b border-border bg-muted/30 px-5 py-2.5">
      {[
        { label: '지표', span: 'col-span-3' },
        { label: '목표', span: 'col-span-3' },
        { label: '실제', span: 'col-span-3' },
        { label: '상태', span: 'col-span-3' },
      ].map((h) => (
        <p key={h.label} className={`font-mono text-xs text-muted-foreground ${h.span}`}>
          {h.label}
        </p>
      ))}
    </div>
    {rows.map((row) => (
      <div
        key={row.metricCode}
        className="grid grid-cols-12 items-center border-b border-border px-5 py-3.5 last:border-0"
      >
        <p className="col-span-3 text-sm font-medium">{row.label}</p>
        <p className="col-span-3 font-mono text-sm text-muted-foreground">
          {formatMetricValue(row.targetValue, row.unit)}
        </p>
        <p className="col-span-3 font-mono text-sm font-semibold">
          {formatMetricValue(row.observedValue, row.unit)}
        </p>
        <div className="col-span-3">
          <span
            className={`rounded border px-1.5 py-0.5 font-mono text-xs ${STATUS_BADGE[row.status] ?? STATUS_BADGE.NOT_COMPARABLE}`}
          >
            {STATUS_LABEL[row.status] ?? row.status}
          </span>
        </div>
      </div>
    ))}
  </div>
);

const RealResultView = ({
  businessId,
  result,
}: {
  businessId: number | null;
  result: OutcomeResultResponse;
}) => {
  const navigate = useNavigate();
  const dashboardHref =
    businessId != null ? `${ROUTES.dashboard}?businessId=${businessId}` : ROUTES.dashboard;

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-2">
        <span className="rounded bg-foreground px-1.5 py-0.5 font-mono text-xs text-background">
          {OVERALL_STATUS_LABEL[result.overallStatus] ?? result.overallStatus}
        </span>
        <p className="text-xs text-muted-foreground">
          {new Date(result.createdAt).toLocaleDateString('ko-KR')} 기준 결과 검증
        </p>
      </div>

      <div className="space-y-2">
        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
          목표 대비 실제 성과
        </p>
        <RealComparisonTable rows={result.comparisonRows} />
        <p className="text-xs text-muted-foreground">
          지표 변화와 자금 지표 사이의 인과관계를 단정하지 않습니다. 외부 환경 변화가 결과에 영향을
          미쳤을 수 있습니다.
        </p>
      </div>

      <div className="space-y-6 border-t border-border pt-8">
        <div>
          <p className="mb-1 font-mono text-xs tracking-widest text-muted-foreground uppercase">
            사업 상태 재평가
          </p>
          <p className="text-sm text-muted-foreground">
            이번 회차 결과를 반영해 초기 조건을 갱신합니다. 갱신된 조건은 다음 시뮬레이션의 출발점이
            됩니다.
          </p>
        </div>

        {result.reevaluation.length > 0 && (
          <div className="overflow-hidden rounded border border-border">
            <div className="grid grid-cols-3 border-b border-border bg-muted/30 px-5 py-2.5">
              {['병목', '변화', '설명'].map((h) => (
                <p key={h} className="font-mono text-xs text-muted-foreground">
                  {h}
                </p>
              ))}
            </div>
            {result.reevaluation.map((item, i) => (
              <div
                key={`${item.bottleneckType}-${i}`}
                className="grid grid-cols-3 items-center border-b border-border px-5 py-3.5 last:border-0"
              >
                <p className="text-sm">{item.bottleneckType}</p>
                <p className="font-mono text-sm text-muted-foreground">
                  {CHANGE_TYPE_LABEL[item.changeType] ?? item.changeType}
                </p>
                <p className="text-xs text-muted-foreground">{item.detail ?? '-'}</p>
              </div>
            ))}
          </div>
        )}

        {result.newBottlenecks.length > 0 && (
          <div className="space-y-2">
            <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
              새로운 병목 후보
            </p>
            {result.newBottlenecks.map((b, i) => (
              <div
                key={`${b.bottleneckType}-${i}`}
                className="flex items-start gap-2 rounded border border-red-200 bg-red-50 px-4 py-3"
              >
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" />
                <div>
                  <p className="text-sm font-medium text-red-800">{b.title}</p>
                  {b.detail && <p className="mt-0.5 text-xs text-red-700">{b.detail}</p>}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex flex-col gap-3 sm:flex-row">
          <Button onClick={() => navigate(ROUTES.simulation)} className="px-5 py-3">
            <RefreshCw className="h-4 w-4" />새 시뮬레이션 시작
          </Button>
          <Button variant="outline" onClick={() => navigate(dashboardHref)} className="px-5 py-3">
            <BarChart2 className="h-4 w-4" />
            전체 대시보드
          </Button>
        </div>
      </div>
    </div>
  );
};

const RealResultCompare = ({
  businessId,
  simulationId,
  executionId,
  onPrev,
}: {
  businessId: number | null;
  simulationId: number;
  executionId: number;
  onPrev: () => void;
}) => {
  const [dataMode, setDataMode] = useState<DataMode | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [mappingNotice, setMappingNotice] = useState<string | null>(null);
  const [result, setResult] = useState<OutcomeResultResponse | null>(null);
  const [manualValues, setManualValues] = useState<Record<string, string>>({});
  const [salesFile, setSalesFile] = useState<File | null>(null);
  const [costFile, setCostFile] = useState<File | null>(null);

  const finishOutcome = async (outcomeDataId: number) => {
    await createOutcome(simulationId, { executionId, outcomeDataId });
    const outcome = await getOutcome(simulationId);
    setResult(outcome);
  };

  const handleLoadMock = async () => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const data = await createOutcomeData(simulationId, { sourceType: 'MOCK' });
      await finishOutcome(data.outcomeDataId);
    } catch (e) {
      setSubmitError(getApiErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitManual = async () => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const metrics = {
        monthlySalesAmount: MANUAL_FIELDS[0].toRequest(
          Number(manualValues.monthlySalesAmount) || 0,
        ),
        operatingProfitAmount: MANUAL_FIELDS[1].toRequest(
          Number(manualValues.operatingProfitAmount) || 0,
        ),
        onlineOrderRatio: MANUAL_FIELDS[2].toRequest(Number(manualValues.onlineOrderRatio) || 0),
        cashAfterRepaymentAmount: MANUAL_FIELDS[3].toRequest(
          Number(manualValues.cashAfterRepaymentAmount) || 0,
        ),
      };
      const data = await createOutcomeData(simulationId, {
        sourceType: 'MANUAL_INPUT',
        metrics,
      });
      await finishOutcome(data.outcomeDataId);
    } catch (e) {
      setSubmitError(getApiErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitUpload = async () => {
    if (!salesFile || !costFile) return;
    setSubmitting(true);
    setSubmitError(null);
    setMappingNotice(null);
    try {
      const data = await createOutcomeData(simulationId, {
        sourceType: 'FILE_UPLOAD',
        salesFile,
        costFile,
      });
      if (data.status === 'MAPPING_READY') {
        setMappingNotice(
          '업로드한 파일의 일부 항목을 자동으로 인식하지 못했습니다. 파일 형식을 확인한 뒤 다시 업로드해주세요.',
        );
        return;
      }
      await finishOutcome(data.outcomeDataId);
    } catch (e) {
      setSubmitError(getApiErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return <RealResultView businessId={businessId} result={result} />;
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold">최신 사업 데이터를 불러와 비교합니다</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          실제 진행 이후의 사업 데이터를 불러와 목표치와 비교합니다.
        </p>
      </div>

      <div className="space-y-4">
        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
          현재 사업 데이터를 어떻게 불러올까요?
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {DATA_SOURCE_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            const isSelected = dataMode === opt.id;
            return (
              <button
                key={opt.id}
                onClick={() => setDataMode(opt.id)}
                className={`space-y-3 rounded border p-5 text-left transition-colors ${
                  isSelected
                    ? 'border-foreground bg-foreground/5'
                    : 'border-border hover:border-foreground/30'
                }`}
              >
                <Icon className="h-4 w-4 text-muted-foreground" />
                <p className="text-sm font-medium">{opt.title}</p>
                <p className="text-xs leading-relaxed text-muted-foreground">{opt.desc}</p>
              </button>
            );
          })}
        </div>

        {dataMode === 'mock' && (
          <div className="space-y-3 rounded border border-dashed border-border px-5 py-4">
            <p className="text-xs text-muted-foreground">
              3개월 후 가상 데이터를 자동 생성해 비교합니다. 실제 사업 성과와 다를 수 있습니다.
            </p>
            <Button onClick={handleLoadMock} disabled={submitting} className="px-4 py-2">
              {submitting ? '불러오는 중...' : 'Mock 데이터 불러오기'}{' '}
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        )}

        {dataMode === 'upload' && (
          <div className="flex flex-col items-center gap-3 rounded border border-dashed border-border px-5 py-6 text-center">
            <Upload className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              진행 후 기간의 매출·비용 파일을 업로드하세요
              <br />
              <span className="text-xs">.xlsx만 지원</span>
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                type="file"
                accept=".xlsx"
                onChange={(e) => setSalesFile(e.target.files?.[0] ?? null)}
                className="text-xs"
              />
              <input
                type="file"
                accept=".xlsx"
                onChange={(e) => setCostFile(e.target.files?.[0] ?? null)}
                className="text-xs"
              />
            </div>
            <Button
              variant="outline"
              onClick={handleSubmitUpload}
              disabled={submitting || !salesFile || !costFile}
              className="px-4 py-2"
            >
              {submitting ? '업로드 중...' : '파일 업로드'}
            </Button>
            {mappingNotice && <ErrorBanner message={mappingNotice} />}
          </div>
        )}

        {dataMode === 'manual' && (
          <div className="space-y-4 rounded border border-border p-5">
            <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
              진행 후 핵심 지표 입력
            </p>
            {MANUAL_FIELDS.map((f) => (
              <div key={f.key} className="grid grid-cols-2 items-center gap-4">
                <p className="text-sm text-muted-foreground">{f.label}</p>
                <input
                  placeholder={f.placeholder}
                  value={manualValues[f.key] ?? ''}
                  onChange={(e) =>
                    setManualValues((prev) => ({ ...prev, [f.key]: e.target.value }))
                  }
                  className="rounded border border-border bg-background px-3 py-2 font-mono text-sm focus:border-foreground focus:outline-none"
                />
              </div>
            ))}
            <Button onClick={handleSubmitManual} disabled={submitting} className="w-full py-2.5">
              {submitting ? '저장 중...' : '저장하고 비교'} <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        )}

        {submitError && <ErrorBanner message={submitError} />}
      </div>

      <div className="flex items-center justify-between">
        <button
          onClick={onPrev}
          className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
          이전
        </button>
      </div>
    </div>
  );
};

const NeedsExecutionView = ({ onPrev }: { onPrev: () => void }) => (
  <div className="space-y-6">
    <h2 className="text-xl font-semibold">최신 사업 데이터를 불러와 비교합니다</h2>
    <div className="space-y-3 rounded border border-border px-5 py-14 text-center">
      <p className="text-sm text-muted-foreground">먼저 실제 진행 내역을 등록해주세요.</p>
      <Button variant="outline" onClick={onPrev} className="mx-auto px-4 py-2">
        <ChevronLeft className="h-3.5 w-3.5" /> 이전 단계로
      </Button>
    </div>
  </div>
);

export const ResultCompareStep = ({
  businessId,
  simulationId,
  executionId,
  onPrev,
}: ResultCompareStepProps) => {
  const navigate = useNavigate();
  const [dataMode, setDataMode] = useState<DataMode | null>(null);
  const [dataLoaded, setDataLoaded] = useState(false);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  if (simulationId != null) {
    if (executionId == null) return <NeedsExecutionView onPrev={onPrev} />;
    return (
      <RealResultCompare
        businessId={businessId}
        simulationId={simulationId}
        executionId={executionId}
        onPrev={onPrev}
      />
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold">최신 사업 데이터를 불러와 비교합니다</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          진행 전 기준 기간(2025.07~09)과 진행 후(2025.11~01)를 비교합니다.
          <br />
          단순 진행 전·후 비교가 아닌, 같은 기간 외부 변화도 함께 확인합니다.
        </p>
      </div>

      {!dataLoaded && (
        <div className="space-y-4">
          <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
            현재 사업 데이터를 어떻게 불러올까요?
          </p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {DATA_SOURCE_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              const isSelected = dataMode === opt.id;
              return (
                <button
                  key={opt.id}
                  onClick={() => setDataMode(opt.id)}
                  className={`space-y-3 rounded border p-5 text-left transition-colors ${
                    isSelected
                      ? 'border-foreground bg-foreground/5'
                      : 'border-border hover:border-foreground/30'
                  }`}
                >
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  <p className="text-sm font-medium">{opt.title}</p>
                  <p className="text-xs leading-relaxed text-muted-foreground">{opt.desc}</p>
                </button>
              );
            })}
          </div>

          {dataMode === 'mock' && (
            <div className="space-y-3 rounded border border-dashed border-border px-5 py-4">
              <div className="flex items-center gap-2">
                <span className="rounded bg-foreground px-1.5 py-0.5 font-mono text-xs text-background">
                  가상 데이터
                </span>
                <p className="text-xs text-muted-foreground">
                  샘플 데이터 기반 시뮬레이션입니다. 실제 사업 성과와 다를 수 있습니다.
                </p>
              </div>
              <p className="font-mono text-xs text-muted-foreground">
                기간: 2026.01~03 (진행 후 3개월)
              </p>
              <Button onClick={() => setDataLoaded(true)} className="px-4 py-2">
                Mock 데이터 불러오기 <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          )}

          {dataMode === 'upload' && (
            <div className="flex flex-col items-center gap-3 rounded border border-dashed border-border px-5 py-6 text-center">
              <Upload className="h-6 w-6 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                진행 후 기간의 매출·비용 파일을 업로드하세요
                <br />
                <span className="text-xs">.csv, .xlsx 지원</span>
              </p>
              <Button variant="outline" onClick={() => setDataLoaded(true)} className="px-4 py-2">
                파일 선택 (실습: Mock으로 대체)
              </Button>
            </div>
          )}

          {dataMode === 'manual' && (
            <div className="space-y-4 rounded border border-border p-5">
              <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                진행 후 핵심 지표 입력
              </p>
              {MANUAL_FIELDS.map((f) => (
                <div key={f.key} className="grid grid-cols-2 items-center gap-4">
                  <p className="text-sm text-muted-foreground">{f.label}</p>
                  <input
                    placeholder={f.placeholder}
                    className="rounded border border-border bg-background px-3 py-2 font-mono text-sm focus:border-foreground focus:outline-none"
                  />
                </div>
              ))}
              <Button onClick={() => setDataLoaded(true)} className="w-full py-2.5">
                저장하고 비교 <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      )}

      {!dataLoaded && (
        <div className="flex items-center justify-between">
          <button
            onClick={onPrev}
            className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ChevronLeft className="h-4 w-4" />
            이전
          </button>
        </div>
      )}

      {dataLoaded && (
        <div className="space-y-8">
          <div className="flex items-center gap-2">
            <span className="rounded bg-foreground px-1.5 py-0.5 font-mono text-xs text-background">
              가상 데이터
            </span>
            <p className="text-xs text-muted-foreground">샘플 데이터 기반 시뮬레이션입니다</p>
            <button
              onClick={() => setDataLoaded(false)}
              className="ml-auto text-xs text-muted-foreground underline hover:text-foreground"
            >
              데이터 다시 불러오기
            </button>
          </div>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            <div className="space-y-3 rounded border border-border p-5">
              <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                월 매출 추이 (만원)
              </p>
              <ResponsiveContainer width="100%" height={150}>
                <LineChart data={TREND_DATA} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="month" tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }} />
                  <YAxis
                    tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }}
                    domain={[2900, 3400]}
                  />
                  <Tooltip
                    contentStyle={{
                      fontSize: 11,
                      borderRadius: 6,
                      border: '1px solid var(--border)',
                    }}
                  />
                  <ReferenceLine y={3150} strokeDasharray="4 2" stroke="var(--muted-foreground)" />
                  <ReferenceLine y={3300} strokeDasharray="4 2" stroke="var(--muted-foreground)" />
                  <Line
                    type="monotone"
                    dataKey="revenue"
                    stroke="var(--foreground)"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    name="실제 매출"
                  />
                </LineChart>
              </ResponsiveContainer>
              <p className="text-xs text-muted-foreground">점선: 실제 진행 기준 재계산 예측 범위</p>
            </div>
            <div className="space-y-3 rounded border border-border p-5">
              <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                온라인 주문 비중 (%)
              </p>
              <ResponsiveContainer width="100%" height={150}>
                <BarChart data={TREND_DATA} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="month" tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }} />
                  <YAxis
                    tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }}
                    domain={[0, 25]}
                  />
                  <Tooltip
                    contentStyle={{
                      fontSize: 11,
                      borderRadius: 6,
                      border: '1px solid var(--border)',
                    }}
                  />
                  <ReferenceLine y={12} strokeDasharray="4 2" stroke="var(--muted-foreground)" />
                  <ReferenceLine y={16} strokeDasharray="4 2" stroke="var(--muted-foreground)" />
                  <Bar
                    dataKey="online"
                    fill="var(--foreground)"
                    opacity={0.6}
                    name="온라인 비중 %"
                    radius={[2, 2, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
              <p className="text-xs text-muted-foreground">점선: 재계산 예측 범위 12~16%</p>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                실제 진행 기준 예상값 vs 실제
              </p>
            </div>
            <p className="text-xs text-muted-foreground">
              실제 진행 내역을 기준으로 예상값을 재계산한 뒤 현재 성과와 비교합니다. SCB 점수를 직접
              계산하지 않습니다.
            </p>
            <div className="overflow-hidden rounded border border-border">
              <div className="grid grid-cols-12 border-b border-border bg-muted/30 px-5 py-2.5">
                {[
                  { label: '지표 / SCB 영역', span: 'col-span-3' },
                  { label: '재계산 예측', span: 'col-span-2' },
                  { label: '3개월 실제', span: 'col-span-2' },
                  { label: '외부 요인', span: 'col-span-2' },
                  { label: '상태', span: 'col-span-3' },
                ].map((h) => (
                  <p key={h.label} className={`font-mono text-xs text-muted-foreground ${h.span}`}>
                    {h.label}
                  </p>
                ))}
              </div>
              {COMPARE_ROWS.map((row) => {
                const cfg = statusCfg[row.status];
                const isOpen = expandedRow === row.label;
                return (
                  <div key={row.label} className="border-b border-border last:border-0">
                    <div className="grid grid-cols-12 items-start px-5 py-3.5">
                      <div className="col-span-3">
                        <p className="text-sm font-medium">{row.label}</p>
                        <p className="mt-0.5 font-mono text-xs text-muted-foreground/60">
                          {row.scbArea}
                        </p>
                      </div>
                      <p className="col-span-2 pt-0.5 font-mono text-sm text-muted-foreground">
                        {row.predicted}
                      </p>
                      <p className="col-span-2 pt-0.5 font-mono text-sm font-semibold">
                        {row.actual}
                      </p>
                      <p className="col-span-2 pt-0.5 font-mono text-xs leading-relaxed text-muted-foreground">
                        {row.external}
                      </p>
                      <div className="col-span-3 flex flex-wrap items-center gap-1.5 pt-0.5">
                        <span
                          className={`rounded border px-1.5 py-0.5 font-mono text-xs ${cfg.badge}`}
                        >
                          {row.note}
                        </span>
                        <button
                          onClick={() => setExpandedRow(isOpen ? null : row.label)}
                          className="ml-auto text-xs text-muted-foreground underline hover:text-foreground"
                        >
                          {isOpen ? '닫기' : '설명'}
                        </button>
                      </div>
                    </div>
                    {isOpen && (
                      <div className="px-5 pb-4">
                        <div className="rounded bg-muted/30 px-4 py-3">
                          <p className="mb-1 font-mono text-xs tracking-widest text-muted-foreground uppercase">
                            분석
                          </p>
                          <p className="text-xs leading-relaxed text-muted-foreground">
                            {row.desc}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <p className="text-xs text-muted-foreground">
              지표 변화와 자금 지표 사이의 인과관계를 단정하지 않습니다. 외부 환경 변화가 결과에
              영향을 미쳤을 수 있습니다.
            </p>
          </div>

          <div className="space-y-6 border-t border-border pt-8">
            <div>
              <p className="mb-1 font-mono text-xs tracking-widest text-muted-foreground uppercase">
                사업 상태 재평가
              </p>
              <p className="text-sm text-muted-foreground">
                이번 회차 결과를 반영해 초기 조건을 갱신합니다. 갱신된 조건은 다음 시뮬레이션의
                출발점이 됩니다.
              </p>
            </div>

            <div className="overflow-hidden rounded border border-border">
              <div className="grid grid-cols-3 border-b border-border bg-muted/30 px-5 py-2.5">
                {['지표', '진행 전', '진행 후 (갱신)'].map((h) => (
                  <p key={h} className="font-mono text-xs text-muted-foreground">
                    {h}
                  </p>
                ))}
              </div>
              {REEVAL_METRICS.map((m) => (
                <div
                  key={m.label}
                  className="grid grid-cols-3 items-center border-b border-border px-5 py-3.5 last:border-0"
                >
                  <p className="text-sm">{m.label}</p>
                  <p className="font-mono text-sm text-muted-foreground">{m.before}</p>
                  <div className="flex items-center gap-2">
                    <p className="font-mono text-sm font-semibold">{m.after}</p>
                    {m.before !== '–' &&
                      (m.up ? (
                        <TrendingUp className="h-3 w-3 text-green-600" />
                      ) : (
                        <TrendingDown className="h-3 w-3 text-amber-600" />
                      ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                  개선된 병목
                </p>
                {RESOLVED.map((b) => (
                  <div
                    key={b.label}
                    className="flex items-start gap-2 rounded border border-green-200 bg-green-50 px-4 py-3"
                  >
                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-500" />
                    <div>
                      <p className="text-sm font-medium text-green-800">{b.label}</p>
                      <p className="mt-0.5 text-xs text-green-700">{b.result}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="space-y-2">
                <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                  새로운 병목 후보
                </p>
                {NEW_BOTTLENECKS.map((b) => (
                  <div
                    key={b.label}
                    className="flex items-start gap-2 rounded border border-red-200 bg-red-50 px-4 py-3"
                  >
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" />
                    <div>
                      <p className="text-sm font-medium text-red-800">{b.label}</p>
                      <p className="mt-0.5 text-xs text-red-700">{b.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <Button
                onClick={() => navigate(`${ROUTES.simulation}?sample=true`)}
                className="px-5 py-3"
              >
                <RefreshCw className="h-4 w-4" />새 시뮬레이션 시작
              </Button>
              <Button
                variant="outline"
                onClick={() => navigate(ROUTES.dashboard)}
                className="px-5 py-3"
              >
                <BarChart2 className="h-4 w-4" />
                전체 대시보드
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
