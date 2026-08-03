import { AlertTriangle, RotateCcw } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';

import { SAMPLE } from '@/entities/simulation';
import { getDashboard, LOAN_STATUS } from '@/entities/verify';
import { getApiErrorMessage } from '@/shared/api';
import type { DashboardResponse } from '@/shared/api/schema';
import { Button } from '@/shared/ui';

import { Header } from './Header';
import { LoanStatusSection } from './LoanStatusSection';
import { MetricTrendSection } from './MetricTrendSection';
import { NextSimulationSection } from './NextSimulationSection';
import { SimulationHistorySection } from './SimulationHistorySection';

const LoadingView = () => (
  <div className="mx-auto flex max-w-4xl flex-col items-center gap-4 px-6 py-24">
    <div className="h-8 w-8 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
    <p className="text-sm text-muted-foreground">대시보드를 불러오는 중...</p>
  </div>
);

const ErrorView = ({ message, onRetry }: { message: string; onRetry: () => void }) => (
  <div className="mx-auto flex max-w-4xl flex-col items-center gap-4 px-6 py-24">
    <AlertTriangle className="h-8 w-8 text-red-500" />
    <p className="text-sm text-red-600">{message}</p>
    <Button variant="outline" onClick={onRetry} className="px-4 py-2">
      <RotateCcw className="h-3.5 w-3.5" /> 다시 불러오기
    </Button>
  </div>
);

export const DashboardPage = () => {
  const [searchParams] = useSearchParams();
  const rawBusinessId = searchParams.get('businessId');
  const businessId = rawBusinessId ? Number(rawBusinessId) : null;
  const isRealMode = businessId != null;

  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    if (!isRealMode || businessId === null) return;
    let cancelled = false;

    const run = async () => {
      setError(null);
      setDashboard(null);
      try {
        const result = await getDashboard(businessId);
        if (!cancelled) setDashboard(result);
      } catch (e) {
        if (!cancelled) setError(getApiErrorMessage(e));
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [isRealMode, businessId, retryToken]);

  if (isRealMode && error) {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <Header />
        <ErrorView message={error} onRetry={() => setRetryToken((t) => t + 1)} />
      </div>
    );
  }

  if (isRealMode && !dashboard) {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <Header />
        <LoadingView />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />

      <div className="border-b border-border bg-muted/20">
        <div className="mx-auto flex max-w-4xl items-center gap-3 px-6 py-4">
          {dashboard ? (
            <>
              <p className="text-sm font-medium">
                {dashboard.business.name} · {dashboard.business.region}
              </p>
              <p className="ml-auto font-mono text-xs text-muted-foreground">
                시뮬레이션 {dashboard.cycleHistories.length}회차
              </p>
            </>
          ) : (
            <>
              <p className="text-sm font-medium">
                {SAMPLE.name} · {SAMPLE.region}
              </p>
              <p className="ml-auto font-mono text-xs text-muted-foreground">
                시뮬레이션 1회차 · 진행 후 {LOAN_STATUS.snapshotMonth}개월
              </p>
            </>
          )}
        </div>
      </div>

      <main className="mx-auto max-w-4xl space-y-10 px-6 py-8">
        <LoanStatusSection isRealMode={isRealMode} loanStatus={dashboard?.loanStatus ?? null} />
        <MetricTrendSection
          isRealMode={isRealMode}
          metricTrends={dashboard?.metricTrends ?? null}
        />
        <SimulationHistorySection
          isRealMode={isRealMode}
          cycleHistories={dashboard?.cycleHistories ?? null}
        />
        <NextSimulationSection
          isRealMode={isRealMode}
          businessId={businessId}
          unresolvedBottlenecks={dashboard?.unresolvedBottlenecks ?? null}
          hasNextInitialConditions={dashboard?.nextInitialConditions != null}
        />
      </main>
    </div>
  );
};
