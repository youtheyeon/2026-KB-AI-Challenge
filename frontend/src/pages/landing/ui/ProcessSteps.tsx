import { CheckCircle2 } from 'lucide-react';

import { PROCESS_STEPS } from '@/pages/landing/model/mock';

export const ProcessSteps = () => {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-5xl space-y-10 px-6 py-16">
        <div>
          <p className="mb-2 font-mono text-xs tracking-widest text-muted-foreground uppercase">
            핵심 진행 구조
          </p>
          <p className="text-xl font-semibold">
            자금 배분 시뮬레이션과 결과 검증 사이에는 실제 자금 집행 기간이 있습니다
          </p>
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {PROCESS_STEPS.map((step) => (
            <div
              key={step.num}
              className={`relative space-y-3 rounded border p-5 ${
                step.muted ? 'border-dashed border-border bg-muted/10' : 'border-border'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-muted-foreground">{step.num}</span>
              </div>
              <p className={`text-sm font-semibold ${step.muted ? 'text-muted-foreground' : ''}`}>
                {step.label}
              </p>
              <p className="text-xs leading-relaxed text-muted-foreground">{step.desc}</p>
            </div>
          ))}
        </div>
        <div className="flex items-start gap-2 rounded border border-border bg-muted/20 px-4 py-3">
          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <p className="text-xs text-muted-foreground">
            저장된 시뮬레이션은 언제든 다시 불러올 수 있습니다. 실행 결과가 축적될수록 사업자의 실제
            변화 이력을 바탕으로 다음 자금 계획을 더욱 구체적으로 검토할 수 있습니다.
          </p>
        </div>
      </div>
    </section>
  );
};
