import { STEPS } from '@/entities/simulation';

interface ProgressBarProps {
  step: number;
}

export const ProgressBar = ({ step }: ProgressBarProps) => {
  return (
    <div className="border-b border-border bg-background">
      <div className="mx-auto max-w-3xl px-6 py-3">
        <div className="hidden items-center gap-1 overflow-x-auto pb-1 sm:flex">
          {STEPS.map((label, i) => (
            <div key={label} className="flex shrink-0 items-center gap-1">
              <div
                className={`rounded px-2.5 py-1 font-mono text-xs transition-colors ${
                  i === step
                    ? 'bg-foreground text-background'
                    : i < step
                      ? 'bg-muted text-muted-foreground'
                      : 'text-muted-foreground/40'
                }`}
              >
                {i + 1}. {label}
              </div>
              {i < STEPS.length - 1 && (
                <div className={`h-px w-3 ${i < step ? 'bg-foreground/30' : 'bg-border'}`} />
              )}
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between text-xs sm:hidden">
          <span className="font-mono text-muted-foreground">
            {step + 1} / {STEPS.length}
          </span>
          <span className="font-medium">{STEPS[step]}</span>
        </div>
        <div className="mt-2 h-0.5 overflow-hidden rounded bg-border">
          <div
            className="h-full bg-foreground transition-all duration-300"
            style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
};
