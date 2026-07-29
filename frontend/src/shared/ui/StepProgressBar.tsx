interface StepProgressBarProps {
  steps: string[];
  step: number;
}

export const StepProgressBar = ({ steps, step }: StepProgressBarProps) => {
  return (
    <div className="border-b border-border bg-background">
      <div className="mx-auto max-w-3xl px-6 py-3">
        <div className="hidden items-center gap-1 overflow-x-auto pb-1 sm:flex">
          {steps.map((label, i) => (
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
              {i < steps.length - 1 && (
                <div className={`h-px w-3 ${i < step ? 'bg-foreground/30' : 'bg-border'}`} />
              )}
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between text-xs sm:hidden">
          <span className="font-mono text-muted-foreground">
            {step + 1} / {steps.length}
          </span>
          <span className="font-medium">{steps[step]}</span>
        </div>
        <div className="mt-2 h-0.5 overflow-hidden rounded bg-border">
          <div
            className="h-full bg-foreground transition-all duration-300"
            style={{ width: `${((step + 1) / steps.length) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
};
