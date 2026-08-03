import { ArrowRight, Cpu } from 'lucide-react';
import { useNavigate } from 'react-router';

import { SIMULATION_TAGS } from '@/pages/landing/model/mock';
import { ROUTES } from '@/shared/config/routes';
import { Button } from '@/shared/ui';

export const SimulationCard = () => {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col overflow-hidden rounded border border-border">
      <div className="flex-1 space-y-4 px-6 py-6">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded border border-border bg-muted/30">
            <Cpu className="h-3.5 w-3.5" />
          </div>
          <span className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
            자금 배분 시뮬레이션
          </span>
        </div>
        <div className="space-y-2">
          <p className="text-lg leading-snug font-semibold">
            대출자금, 어디에 쓸지
            <br />
            시나리오별로 비교해보기
          </p>
          <p className="text-sm leading-relaxed text-muted-foreground">
            사업 데이터를 연결하면 현재 사업의 병목을 진단하고, A·B·C 배분안의 자금 구성과 재무
            부담을 동일한 기준으로 비교합니다. AI는 특정 안을 최선으로 추천하지 않으며, 각 안의
            근거와 위험을 확인한 뒤 사용자가 직접 판단합니다.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {SIMULATION_TAGS.map((tag) => (
            <span
              key={tag}
              className="rounded bg-muted px-2 py-1 font-mono text-xs text-muted-foreground"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-4 border-t border-border px-6 py-4">
        <Button onClick={() => navigate(ROUTES.simulation)} className="px-5 py-2.5">
          시뮬레이션 시작 <ArrowRight className="h-4 w-4" />
        </Button>
        <button
          onClick={() => navigate(`${ROUTES.simulation}?sample=true`)}
          className="text-sm text-muted-foreground underline underline-offset-2 transition-colors hover:text-foreground"
        >
          샘플로 체험하기
        </button>
      </div>
    </div>
  );
};
