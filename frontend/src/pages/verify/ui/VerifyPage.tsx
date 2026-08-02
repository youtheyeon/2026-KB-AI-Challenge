import { useState } from 'react';
import { useSearchParams } from 'react-router';

import { STEPS } from '@/entities/verify';
import { LoadSimulationStep } from '@/features/verify-load-simulation';
import { RecordExecutionStep } from '@/features/verify-record-execution';
import { ResultCompareStep } from '@/features/verify-result-compare';
import { useScrollToTop } from '@/shared/lib/useScrollToTop';
import { StepProgressBar } from '@/shared/ui';

import { Header } from './Header';

export const VerifyPage = () => {
  const [searchParams] = useSearchParams();
  const rawBusinessId = searchParams.get('businessId');
  const businessId = rawBusinessId ? Number(rawBusinessId) : null;

  const [step, setStep] = useState(0);
  const [simulationId, setSimulationId] = useState<number | null>(null);
  const [executionId, setExecutionId] = useState<number | null>(null);

  useScrollToTop(step);

  const next = () => setStep((s) => Math.min(s + 1, STEPS.length - 1));
  const prev = () => setStep((s) => Math.max(s - 1, 0));

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header businessId={businessId} />
      <StepProgressBar steps={STEPS} step={step} />

      <main className="mx-auto max-w-3xl space-y-8 px-6 py-8">
        {step === 0 && (
          <LoadSimulationStep
            businessId={businessId}
            onNext={next}
            onSimulationSelected={setSimulationId}
          />
        )}
        {step === 1 && (
          <RecordExecutionStep
            simulationId={simulationId}
            onPrev={prev}
            onNext={next}
            onExecutionRegistered={setExecutionId}
          />
        )}
        {step === 2 && (
          <ResultCompareStep
            businessId={businessId}
            simulationId={simulationId}
            executionId={executionId}
            onPrev={prev}
          />
        )}
      </main>
    </div>
  );
};
