import { ArrowRight, CheckCircle2 } from 'lucide-react';
import { useNavigate } from 'react-router';

import type { LoanCond } from '@/entities/simulation';
import { ROUTES } from '@/shared/config/routes';
import { Button } from '@/shared/ui';

import { Header } from './Header';

interface SimulationResultProps {
  cond: LoanCond;
  businessId: number | null;
  simulationId: number | null;
}

export const SimulationResult = ({ cond, businessId }: SimulationResultProps) => {
  const navigate = useNavigate();
  const verifyHref =
    businessId != null ? `${ROUTES.verify}?businessId=${businessId}` : ROUTES.verify;

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <Header showBack={false} />
      <main className="flex flex-1 items-center justify-center px-6 py-16">
        <div className="flex w-full max-w-md flex-col items-center gap-6 rounded border border-border px-8 py-10 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-foreground">
            <CheckCircle2 className="h-5 w-5 text-background" />
          </div>
          <div className="space-y-2">
            <p className="text-lg font-semibold">시뮬레이션 결과가 저장되었습니다</p>
            <p className="text-sm leading-relaxed text-muted-foreground">
              A·B·C의 비교 결과가 저장되었습니다.
              <br />
              실제로 대출금을 진행한 뒤, 이 화면에서
              <br />
              &quot;결과 확인하기&quot;를 통해 실제 성과와 비교하세요.
            </p>
          </div>
          <div className="w-full space-y-2 rounded border border-border bg-muted/10 px-5 py-4 text-left">
            <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
              저장된 시뮬레이션
            </p>
            <p className="font-mono text-sm">
              {new Date().toLocaleDateString('ko-KR', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
              })}{' '}
              · 대출금 {cond.loanAmount.toLocaleString()}만원
            </p>
            <p className="text-xs text-muted-foreground">
              비교안: A · B · C&nbsp;|&nbsp;실제 진행: 아직 등록하지 않음
            </p>
          </div>
          <div className="flex w-full flex-col gap-2">
            <Button onClick={() => navigate(ROUTES.home)} className="py-3">
              홈으로 돌아가기 <ArrowRight className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              onClick={() => navigate(verifyHref)}
              className="py-3 text-muted-foreground"
            >
              바로 결과 검증 시작하기
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
};
