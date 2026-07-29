import { ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router';

import { DEMO_CREDENTIALS } from '@/features/login/model/mock';
import { ROUTES } from '@/shared/config/routes';
import { Button } from '@/shared/ui';

export const LoginForm = () => {
  const navigate = useNavigate();

  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">시작하기</h1>
        <p className="text-sm text-muted-foreground">사업자 인증 후 시뮬레이션을 시작합니다.</p>
      </div>

      <div className="space-y-3">
        <div className="space-y-1.5">
          <label className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
            사업자등록번호
          </label>
          <input
            type="text"
            placeholder="000-00-00000"
            defaultValue={DEMO_CREDENTIALS.businessNumber}
            className="w-full rounded border border-border bg-input-background px-3 py-2.5 font-mono text-sm transition-colors placeholder:text-muted-foreground/50 focus:border-foreground focus:outline-none"
          />
        </div>
        <div className="space-y-1.5">
          <label className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
            비밀번호
          </label>
          <input
            type="password"
            defaultValue={DEMO_CREDENTIALS.password}
            className="w-full rounded border border-border bg-input-background px-3 py-2.5 text-sm transition-colors focus:border-foreground focus:outline-none"
          />
        </div>
      </div>

      <Button onClick={() => navigate(ROUTES.simulation)} className="w-full py-3">
        로그인 <ArrowRight className="h-4 w-4" />
      </Button>

      <p className="text-center text-xs text-muted-foreground">
        데모용 계정이 이미 입력되어 있습니다.
      </p>
    </div>
  );
};
