import { AlertTriangle, ArrowRight, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router';

import { NEW_BOTTLENECKS, REEVAL_METRICS } from '@/entities/verify';
import { ROUTES } from '@/shared/config/routes';
import { Button, SectionLabel } from '@/shared/ui';

const PRIORITY_COLOR: Record<string, string> = {
  high: 'text-red-600 bg-red-50 border-red-200',
  medium: 'text-amber-600 bg-amber-50 border-amber-200',
  low: 'text-muted-foreground bg-secondary border-border',
};

export const NextSimulationSection = () => {
  const navigate = useNavigate();

  return (
    <section className="space-y-4">
      <SectionLabel>다음 시뮬레이션 준비</SectionLabel>
      <div className="space-y-5 rounded border border-border p-5">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <p className="font-mono text-xs text-muted-foreground">우선 확인 병목 후보</p>
            {NEW_BOTTLENECKS.map((b) => (
              <div
                key={b.label}
                className={`flex items-center gap-2 rounded border px-2.5 py-1.5 font-mono text-xs ${PRIORITY_COLOR[b.priority]}`}
              >
                <AlertTriangle className="h-3 w-3 shrink-0" />
                {b.label}
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <p className="font-mono text-xs text-muted-foreground">갱신된 초기 조건</p>
            {REEVAL_METRICS.map((m) => (
              <div
                key={m.label}
                className="flex justify-between border-b border-border pb-1 font-mono text-sm"
              >
                <span className="text-muted-foreground">{m.label}</span>
                <span>{m.after}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button
            onClick={() => navigate(`${ROUTES.simulation}?sample=true`)}
            className="px-5 py-2.5"
          >
            <RefreshCw className="h-4 w-4" />새 시뮬레이션 시작
          </Button>
          <Button variant="outline" onClick={() => navigate(ROUTES.verify)} className="px-4 py-2.5">
            성과 추적 상세 <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </section>
  );
};
