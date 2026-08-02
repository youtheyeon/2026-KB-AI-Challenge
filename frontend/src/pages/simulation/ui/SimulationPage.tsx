import { ChevronLeft } from 'lucide-react';
import { useState } from 'react';
import { useSearchParams } from 'react-router';

import { AnalysisStep } from '@/features/simulation-business-analysis';
import { DataConnectStep } from '@/features/simulation-data-connect';
import { BuildStep } from '@/features/simulation-fund-allocation';
import { LoanStep } from '@/features/simulation-loan-condition';
import { CompareStep } from '@/features/simulation-scenario-compare';
import { DEMO_RATE, STEPS, type LoanCond } from '@/entities/simulation';
import { useScrollToTop } from '@/shared/lib/useScrollToTop';
import { StepProgressBar } from '@/shared/ui';

import { Header } from './Header';
import { SimulationResult } from './SimulationResult';

export const SimulationPage = () => {
  const [searchParams] = useSearchParams();
  const isSample = searchParams.get('sample') === 'true';
  const [step, setStep] = useState(0);
  const [businessId, setBusinessId] = useState<number | null>(null);
  const [datasetId, setDatasetId] = useState<number | null>(null);
  const [cond, setCond] = useState<LoanCond>({
    loanAmount: 3000,
    rateMode: 'demo',
    rate: DEMO_RATE,
    period: 3,
    grace: 0,
    method: 'equal-payment',
    existingMonthly: 0,
  });
  const [saved, setSaved] = useState(false);

  useScrollToTop(step, saved);

  const next = () => {
    if (step === STEPS.length - 1) {
      setSaved(true);
      return;
    }
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  };
  const prev = () => setStep((s) => Math.max(s - 1, 0));

  if (saved) {
    return <SimulationResult cond={cond} />;
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />
      <StepProgressBar steps={STEPS} step={step} />

      <main className="mx-auto max-w-3xl px-6 py-8">
        {step === 0 && (
          <DataConnectStep
            isSample={isSample}
            businessId={businessId}
            onNext={next}
            onBusinessRegistered={setBusinessId}
            onDatasetUploaded={setDatasetId}
          />
        )}
        {step === 1 && <AnalysisStep businessId={businessId} datasetId={datasetId} onNext={next} />}
        {step === 2 && <LoanStep cond={cond} setCond={setCond} onNext={next} />}
        {step === 3 && <BuildStep cond={cond} onNext={next} />}
        {step === 4 && <CompareStep cond={cond} onNext={next} />}

        {step > 0 && (
          <button
            onClick={prev}
            className="mt-8 flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ChevronLeft className="h-4 w-4" />
            이전 단계
          </button>
        )}
      </main>
    </div>
  );
};
