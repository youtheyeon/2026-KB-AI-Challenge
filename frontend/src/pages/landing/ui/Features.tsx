import { FEATURES } from '@/pages/landing/model/mock';

export const Features = () => {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-5xl space-y-10 px-6 py-16">
        <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
          주요 기능
        </p>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          {FEATURES.map((feature) => {
            const Icon = feature.icon;
            return (
              <div key={feature.title} className="space-y-3 rounded border border-border p-6">
                <div className="flex h-8 w-8 items-center justify-center rounded border border-border bg-muted/30">
                  <Icon className="h-4 w-4 text-foreground" />
                </div>
                <p className="text-sm font-semibold">{feature.title}</p>
                <p className="text-xs leading-relaxed text-muted-foreground">{feature.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
