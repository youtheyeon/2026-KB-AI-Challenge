import { ChevronLeft } from 'lucide-react';
import { useNavigate } from 'react-router';

import { SERVICE_NAME } from '@/shared/config/constants';
import { ROUTES } from '@/shared/config/routes';

interface HeaderProps {
  showBack?: boolean;
}

export const Header = ({ showBack = true }: HeaderProps) => {
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background">
      <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-6">
        {showBack ? (
          <button
            onClick={() => navigate(ROUTES.home)}
            className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ChevronLeft className="h-4 w-4" />
            홈으로
          </button>
        ) : (
          <div className="w-12" />
        )}
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-sm bg-primary">
            <span className="font-mono text-xs leading-none font-bold text-primary-foreground">
              KB
            </span>
          </div>
          <span className="text-sm font-semibold tracking-tight">{SERVICE_NAME}</span>
        </div>
        <div className="w-12" />
      </div>
    </header>
  );
};
