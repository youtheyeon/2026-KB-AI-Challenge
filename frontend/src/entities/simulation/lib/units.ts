import { RepaymentTypeRequest } from '@/shared/api/schema';

export const yearsToMonths = (years: number): number => Math.round(years * 12);

const METHOD_TO_REPAYMENT_TYPE: Record<string, RepaymentTypeRequest> = {
  'equal-payment': RepaymentTypeRequest.EQUAL_PAYMENT,
  'equal-principal': RepaymentTypeRequest.EQUAL_PRINCIPAL,
  bullet: RepaymentTypeRequest.BULLET_PAYMENT,
};

export const methodToRepaymentType = (method: string): RepaymentTypeRequest =>
  METHOD_TO_REPAYMENT_TYPE[method] ?? RepaymentTypeRequest.EQUAL_PAYMENT;

export const manwonToWon = (manwon: number): number => manwon * 10_000;

export const wonToManwon = (won: number): number => Math.round(won / 10_000);
