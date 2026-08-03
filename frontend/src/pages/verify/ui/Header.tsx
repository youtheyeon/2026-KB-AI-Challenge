import { ChevronLeft } from 'lucide-react';
import { useNavigate } from 'react-router';

import { ROUTES } from '@/shared/config/routes';

interface HeaderProps {
  businessId?: number | null;
}

export const Header = ({ businessId }: HeaderProps) => {
  const navigate = useNavigate();
  const dashboardHref =
    businessId != null ? `${ROUTES.dashboard}?businessId=${businessId}` : ROUTES.dashboard;

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background">
      <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-6">
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
          <span className="text-sm font-semibold tracking-tight">결과 검증</span>
        </div>
        <button
          onClick={() => navigate(dashboardHref)}
          className="text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          대시보드
        </button>
      </div>
    </header>
  );
};
