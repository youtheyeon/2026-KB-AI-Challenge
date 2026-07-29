import { Cta } from './Cta';
import { Features } from './Features';
import { Header } from './Header';
import { Hero } from './Hero';
import { ProcessSteps } from './ProcessSteps';
import { ResultCard } from './ResultCard';
import { SimulationCard } from './SimulationCard';

export const LandingPage = () => {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />
      <Hero />

      <section className="border-b border-border">
        <div className="mx-auto max-w-5xl px-6 py-12">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <SimulationCard />
            <ResultCard />
          </div>
        </div>
      </section>

      <ProcessSteps />
      <Features />
      <Cta />
    </div>
  );
};
