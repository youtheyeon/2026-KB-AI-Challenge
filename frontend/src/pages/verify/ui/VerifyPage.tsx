import { useState } from 'react';

import { STEPS } from '@/entities/verify';
import { LoadSimulationStep } from '@/features/verify-load-simulation';
import { RecordExecutionStep } from '@/features/verify-record-execution';
import { ResultCompareStep } from '@/features/verify-result-compare';
import { useScrollToTop } from '@/shared/lib/useScrollToTop';
import { StepProgressBar } from '@/shared/ui';

import { Header } from './Header';

export const VerifyPage = () => {
  const [step, setStep] = useState(0);

  useScrollToTop(step);

  const next = () => setStep((s) => Math.min(s + 1, STEPS.length - 1));
  const prev = () => setStep((s) => Math.max(s - 1, 0));

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />
      <StepProgressBar steps={STEPS} step={step} />

      <main className="mx-auto max-w-3xl space-y-8 px-6 py-8">
        {step === 0 && <LoadSimulationStep onNext={next} />}
        {step === 1 && <RecordExecutionStep onPrev={prev} onNext={next} />}
        {step === 2 && <ResultCompareStep onPrev={prev} />}
      </main>
    </div>
  );
};
