import { ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router';

import { ROUTES } from '@/shared/config/routes';
import { Button } from '@/shared/ui';

export const Cta = () => {
  const navigate = useNavigate();

  return (
    <section>
      <div className="mx-auto flex max-w-5xl flex-col items-start justify-between gap-6 px-6 py-16 sm:flex-row sm:items-center">
        <div>
          <p className="text-xl font-semibold">내 사업 데이터로 시작하기</p>
          <p className="mt-1 text-sm text-muted-foreground">
            카드 매출 또는 POS 파일 하나로 분석을 시작할 수 있습니다.
          </p>
        </div>
        <Button
          onClick={() => navigate(`${ROUTES.simulation}?sample=true`)}
          className="shrink-0 px-5 py-3"
        >
          샘플로 바로 시작 <ArrowRight className="w-4 h-4" />
        </Button>
      </div>
    </section>
  );
};
