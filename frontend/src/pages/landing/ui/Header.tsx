import { useNavigate } from 'react-router';

import { SERVICE_NAME } from '@/shared/config/constants';
import { ROUTES } from '@/shared/config/routes';

export const Header = () => {
  const navigate = useNavigate();

  return (
    <header className="border-b border-border">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-sm bg-primary">
            <span className="font-mono text-xs leading-none font-bold text-primary-foreground">
              KB
            </span>
          </div>
          <span className="text-sm font-semibold tracking-tight">{SERVICE_NAME}</span>
        </div>
        <button
          onClick={() => navigate(ROUTES.login)}
          className="text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          로그인
        </button>
      </div>
    </header>
  );
};
