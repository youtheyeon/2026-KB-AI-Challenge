import { SAMPLE } from '@/entities/simulation';
import { LOAN_STATUS } from '@/entities/verify';

import { Header } from './Header';
import { LoanStatusSection } from './LoanStatusSection';
import { MetricTrendSection } from './MetricTrendSection';
import { NextSimulationSection } from './NextSimulationSection';
import { SimulationHistorySection } from './SimulationHistorySection';

export const DashboardPage = () => {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />

      <div className="border-b border-border bg-muted/20">
        <div className="mx-auto flex max-w-4xl items-center gap-3 px-6 py-4">
          <p className="text-sm font-medium">
            {SAMPLE.name} · {SAMPLE.region}
          </p>
          <p className="ml-auto font-mono text-xs text-muted-foreground">
            시뮬레이션 1회차 · 진행 후 {LOAN_STATUS.snapshotMonth}개월
          </p>
        </div>
      </div>

      <main className="mx-auto max-w-4xl space-y-10 px-6 py-8">
        <LoanStatusSection />
        <MetricTrendSection />
        <SimulationHistorySection />
        <NextSimulationSection />
      </main>
    </div>
  );
};
