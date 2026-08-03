export const Hero = () => {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-5xl space-y-8 px-6 py-20">
        <div className="max-w-2xl space-y-4">
          <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
            KB국민은행 · 소상공인 금융 지원 에이전트
          </p>
          <h1 className="text-4xl leading-tight font-semibold tracking-tight">
            SCB 대출로 확보한 자금,
            <br />
            어디에 어떻게 배분할지 실행 전에 비교해보세요
          </h1>
          <p className="text-base leading-relaxed text-muted-foreground">
            SCB가 성장 가능성을 평가해 자금 조달의 기회를 더한다면,
            <br />
            우리는 매출·비용·상권 데이터로 병목을 진단해 A·B·C 배분안을 구성하고,
            <br />
            집행 후 성과를 추적해 다음 자금 계획에 반영합니다.
          </p>
        </div>
      </div>
    </section>
  );
};
