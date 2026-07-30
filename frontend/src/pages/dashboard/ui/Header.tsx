import { ChevronLeft, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router';

import { ROUTES } from '@/shared/config/routes';

export const Header = () => {
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background">
      <div className="mx-auto flex h-14 max-w-4xl items-center justify-between px-6">
        <button
          onClick={() => navigate(ROUTES.home)}
          className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
          홈으로
        </button>
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-sm bg-primary">
            <span className="font-mono text-xs leading-none font-bold text-primary-foreground">
              KB
            </span>
          </div>
          <span className="text-sm font-semibold tracking-tight">선순환 대시보드</span>
        </div>
        <button
          onClick={() => navigate(`${ROUTES.simulation}?sample=true`)}
          className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <RefreshCw className="h-3.5 w-3.5" />새 시뮬레이션
        </button>
      </div>
    </header>
  );
};
