import { ChevronRight } from 'lucide-react';
import { useEffect, useState } from 'react';

import { BOTTLENECKS, sevCfg } from '@/entities/simulation';

interface AnalysisStepProps {
  onNext: () => void;
}

interface MetricItem {
  label: string;
  value: string;
  src: string;
  highlight?: boolean;
  warn?: boolean;
}

const FIN: MetricItem[] = [
  { label: '월평균 매출', value: '3,000만원', src: '실제 데이터' },
  { label: '최근 매출 증가율', value: '+2.1%', src: '실제 데이터' },
  { label: '영업이익률', value: '11.0%', src: '계산값' },
  { label: '재료비 원가율', value: '40.0%', src: '실제 데이터', highlight: true },
  { label: '인건비율', value: '28.0%', src: '실제 데이터' },
  { label: '월 여유현금', value: '180만원', src: '계산값' },
];

const ACT: MetricItem[] = [
  { label: '월 주문 수', value: '420건', src: '실제 데이터' },
  { label: '객단가', value: '7.1만원', src: '계산값' },
  { label: '직원 수', value: '2명', src: '사용자 입력' },
  { label: '재구매율', value: '34%', src: '추정값', warn: true },
  { label: '온라인 판매 비중', value: '9%', src: '실제 데이터', warn: true },
  { label: '직원당 처리량', value: '210건/월', src: '계산값' },
];

const DISTRICT: MetricItem[] = [
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

export const AnalysisStep = ({ onNext }: AnalysisStepProps) => {
  const [loading, setLoading] = useState(true);
  const [showBasis, setShowBasis] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 1800);
    return () => clearTimeout(t);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-semibold">사업 상태 분석 중</h2>
        <div className="flex flex-col items-center gap-4 rounded border border-border p-14">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
          <p className="text-sm text-muted-foreground">매출·비용·상권 데이터 종합 분석 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold">현재 사업 상태 분석</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          자금 시뮬레이션에 앞서 현재 사업의 재무 상태와 성장 병목 후보를 확인하세요.
        </p>
      </div>

      <div className="space-y-2">
        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">재무</p>
        <div className="grid grid-cols-2 overflow-hidden rounded border border-border sm:grid-cols-3">
          {FIN.map((m, i) => (
            <div
              key={m.label}
              className={`px-4 py-4 ${i % 3 < 2 ? 'border-r border-border' : ''} ${
                i < 3 ? 'border-b border-border' : ''
              }`}
            >
              <p className="text-xs text-muted-foreground">{m.label}</p>
              <p
                className={`mt-1 font-mono text-lg font-semibold tabular-nums ${
                  m.highlight ? 'text-amber-600' : ''
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

      <div className="space-y-2">
        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
          사업 활동
        </p>
        <div className="grid grid-cols-2 overflow-hidden rounded border border-border sm:grid-cols-3">
          {ACT.map((m, i) => (
            <div
              key={m.label}
              className={`px-4 py-4 ${i % 3 < 2 ? 'border-r border-border' : ''} ${
                i < 3 ? 'border-b border-border' : ''
              }`}
            >
              <p className="text-xs text-muted-foreground">{m.label}</p>
              <p
                className={`mt-1 font-mono text-lg font-semibold tabular-nums ${
                  m.warn ? 'text-amber-600' : ''
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

      <div className="space-y-2">
        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">상권</p>
        <div className="grid grid-cols-2 overflow-hidden rounded border border-border sm:grid-cols-4">
          {DISTRICT.map((m, i) => (
            <div key={m.label} className={`px-4 py-4 ${i < 3 ? 'border-r border-border' : ''}`}>
              <p className="text-xs text-muted-foreground">{m.label}</p>
              <p
                className={`mt-1 font-mono text-base font-semibold tabular-nums ${
                  m.warn ? 'text-amber-600' : ''
                }`}
              >
                {m.value}
              </p>
              <p className={`mt-0.5 font-mono text-xs ${SRC_COLOR[m.src]}`}>{m.src}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
          확인이 필요한 병목 후보
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {BOTTLENECKS.map((b) => {
            const cfg = sevCfg[b.sev];
            return (
              <div key={b.id} className="space-y-2 rounded border border-border p-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
                    <p className="text-sm font-medium">{b.label}</p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={`rounded border px-1.5 py-0.5 font-mono text-xs ${cfg.badge}`}>
                      {cfg.label}
                    </span>
                    <span className="font-mono text-xs text-muted-foreground/60">
                      신뢰도 {b.conf}
                    </span>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">{b.desc}</p>
                <div className="flex items-center justify-between gap-2">
                  <p className="flex-1 rounded bg-muted/50 px-2.5 py-1.5 font-mono text-xs">
                    {b.metric}
                  </p>
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
                    <p className="text-xs leading-relaxed text-muted-foreground">{b.desc}</p>
                    <p className="font-mono text-xs text-muted-foreground">{b.metric}</p>
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
        <button
          onClick={onNext}
          className="flex items-center gap-2 rounded bg-foreground px-5 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-90"
        >
          대출 조건 입력 <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};
