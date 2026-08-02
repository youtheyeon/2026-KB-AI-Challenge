import { wonToManwon } from '@/entities/simulation';
import { LOAN_STATUS } from '@/entities/verify';
import type { LoanStatusResponse } from '@/shared/api/schema';
import { SectionLabel } from '@/shared/ui';

const REPAYMENT_TYPE_LABEL: Record<string, string> = {
  EQUAL_PAYMENT: '원리금균등',
  EQUAL_PRINCIPAL: '원금균등',
  BULLET_PAYMENT: '만기일시',
};

interface LoanStatusSectionProps {
  isRealMode: boolean;
  loanStatus: LoanStatusResponse | null;
}

export const LoanStatusSection = ({ isRealMode, loanStatus }: LoanStatusSectionProps) => {
  if (isRealMode) {
    if (!loanStatus) {
      return (
        <section className="space-y-4">
          <SectionLabel>대출 상환 현황</SectionLabel>
          <div className="rounded border border-border px-5 py-8 text-center text-sm text-muted-foreground">
            아직 등록된 실행 내역이 없습니다.
          </div>
        </section>
      );
    }

    const stats = [
      { label: '대출금', value: `${wonToManwon(loanStatus.loanAmount).toLocaleString()}만원` },
      {
        label: '월 상환액',
        value: `${wonToManwon(loanStatus.monthlyRepaymentAmount).toLocaleString()}만원`,
      },
      { label: '상환 진행률', value: `${Math.round(loanStatus.progressRate * 100)}%` },
      {
        label: '잔여 원금',
        value: `${wonToManwon(loanStatus.estimatedRemainingPrincipal).toLocaleString()}만원`,
      },
    ];

    return (
      <section className="space-y-4">
        <SectionLabel>대출 상환 현황</SectionLabel>
        <div className="overflow-hidden rounded border border-border">
          <div className="grid grid-cols-2 divide-x divide-border sm:grid-cols-4">
            {stats.map((s) => (
              <div key={s.label} className="px-5 py-4">
                <p className="text-xs text-muted-foreground">{s.label}</p>
                <p className="mt-1 font-mono text-lg font-semibold tabular-nums">{s.value}</p>
              </div>
            ))}
          </div>
          <p className="border-t border-border px-5 py-3 text-xs text-muted-foreground">
            누적 납부액 {wonToManwon(loanStatus.paidAmount).toLocaleString()}만원 ·{' '}
            {loanStatus.repaymentDataType === 'ESTIMATED' ? '추정치' : '실제값'} 기준입니다.
          </p>
        </div>
      </section>
    );
  }

  const { condition, monthlyLoanPayment, snapshotMonth } = LOAN_STATUS;

  const stats = [
    { label: '대출금', value: `${condition.amount.toLocaleString()}만원` },
    { label: '월 상환액', value: `${monthlyLoanPayment}만원` },
    { label: '상환기간', value: `${condition.termMonths}개월` },
    { label: '상환 방식', value: REPAYMENT_TYPE_LABEL[condition.repaymentType] },
  ];

  return (
    <section className="space-y-4">
      <SectionLabel>대출 상환 현황</SectionLabel>
      <div className="overflow-hidden rounded border border-border">
        <div className="grid grid-cols-2 divide-x divide-border sm:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="px-5 py-4">
              <p className="text-xs text-muted-foreground">{s.label}</p>
              <p className="mt-1 font-mono text-lg font-semibold tabular-nums">{s.value}</p>
            </div>
          ))}
        </div>
        <p className="border-t border-border px-5 py-3 text-xs text-muted-foreground">
          집행 후 {snapshotMonth}개월 시점 데이터입니다. 실시간 상환 진행률과 잔여 잔액은 추적하지
          않습니다.
        </p>
      </div>
    </section>
  );
};
