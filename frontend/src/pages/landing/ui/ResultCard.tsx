import { AlertTriangle, ArrowRight, BarChart2, Clock } from 'lucide-react';
import { useNavigate } from 'react-router';

import { ARCHIVED } from '@/pages/landing/model/mock';
import { ROUTES } from '@/shared/config/routes';
import { Button } from '@/shared/ui';

export const ResultCard = () => {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col overflow-hidden rounded border border-border">
      <div className="flex-1 space-y-4 px-6 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded border border-border bg-muted/30">
              <BarChart2 className="h-3.5 w-3.5" />
            </div>
            <span className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
              실제 결과 확인
            </span>
          </div>
          <span className="rounded border border-amber-200 bg-amber-50 px-2 py-0.5 font-mono text-xs text-amber-700">
            1건 대기 중
          </span>
        </div>
        <div className="space-y-2">
          <p className="text-lg leading-snug font-semibold">
            3개월 후,
            <br />
            예상과 실제가 얼마나 달랐나요?
          </p>
          <p className="text-sm leading-relaxed text-muted-foreground">
            저장한 배분안과 3개월 후 실제 재무 지표를 비교합니다. 예측 오차와 병목을 파악해 다음
            자금 계획을 개선하세요.
          </p>
        </div>

        <div className="space-y-3 rounded border border-amber-200 bg-amber-50/50 px-4 py-4">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="shrink-0 rounded bg-foreground px-1.5 py-0.5 font-mono text-xs font-bold text-background">
                {ARCHIVED.id}
              </span>
              <p className="text-sm leading-snug font-medium">{ARCHIVED.plan}</p>
            </div>
            <div className="flex shrink-0 items-center gap-1 font-mono text-xs text-amber-700">
              <Clock className="h-3 w-3" />
              {ARCHIVED.daysAgo}일 경과
            </div>
          </div>
          <div className="flex gap-4 font-mono text-xs text-muted-foreground">
            <span>
              대출금 <span className="text-foreground">{ARCHIVED.loanAmount}</span>
            </span>
            <span>
              월 이자 <span className="text-foreground">{ARCHIVED.monthlyRepay}</span>
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <AlertTriangle className="h-3 w-3 shrink-0 text-amber-500" />
            <p className="text-xs text-muted-foreground">해결 목표: {ARCHIVED.bottleneck}</p>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 shrink-0 rounded-full bg-amber-400" />
            <p className="font-mono text-xs text-amber-700">실제 진행 미등록</p>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-4 border-t border-border px-6 py-4">
        <Button variant="outline" onClick={() => navigate(ROUTES.verify)} className="px-5 py-2.5">
          결과 확인하기 <ArrowRight className="h-4 w-4" />
        </Button>
        <button
          onClick={() => navigate(ROUTES.dashboard)}
          className="text-sm text-muted-foreground underline underline-offset-2 transition-colors hover:text-foreground"
        >
          전체 대시보드
        </button>
      </div>
    </div>
  );
};
