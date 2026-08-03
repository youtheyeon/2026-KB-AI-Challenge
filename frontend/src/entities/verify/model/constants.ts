import { AlertTriangle, CheckCircle2 } from 'lucide-react';

import { calcMonthly } from '@/entities/simulation';

import type {
  LoanCondition,
  LoanStatus,
  NewBottleneck,
  OutcomeConfig,
  ResolvedBottleneck,
  ReevalMetric,
  SimulationHistoryEntry,
  SimulationOutcome,
  TrendPoint,
} from './types';

export const STEPS = ['시뮬레이션 불러오기', '실제 진행 등록', '결과 비교'];

const HISTORY_LOAN_CONDITION: LoanCondition = {
  amount: 3000,
  annualInterestRate: 0.045,
  termMonths: 36,
  graceMonths: 0,
  repaymentType: 'EQUAL_PAYMENT',
};

const HISTORY_MONTHLY_LOAN_PAYMENT = calcMonthly(
  HISTORY_LOAN_CONDITION.amount,
  HISTORY_LOAN_CONDITION.annualInterestRate * 100,
  HISTORY_LOAN_CONDITION.termMonths / 12,
  HISTORY_LOAN_CONDITION.graceMonths / 12,
  'equal-payment',
);

export const TREND_DATA: TrendPoint[] = [
  { month: '진행 전', revenue: 3000, profit: 330, online: 9 },
  { month: '1개월', revenue: 3020, profit: 318, online: 10 },
  { month: '2개월', revenue: 3110, profit: 340, online: 12 },
  { month: '3개월', revenue: 3210, profit: 352, online: 13 },
];

export const REEVAL_METRICS: ReevalMetric[] = [
  { label: '기준 월 매출', before: '3,000만원', after: '3,210만원', up: true },
  { label: '기준 영업이익', before: '330만원', after: '352만원', up: true },
  { label: '상환 후 여유현금', before: '180만원', after: '198만원', up: true },
  { label: '온라인 주문 비중', before: '9%', after: '13%', up: true },
  { label: '월 상환액', before: '–', after: `${HISTORY_MONTHLY_LOAN_PAYMENT}만원`, up: true },
];

export const RESOLVED: ResolvedBottleneck[] = [
  { label: '온라인 판매채널 편중', result: '일부 개선 (9%→13%)' },
];

export const NEW_BOTTLENECKS: NewBottleneck[] = [
  {
    label: '원가율 상승',
    priority: 'high',
    desc: '원재료 가격 상승으로 원가율 목표 미달. 재협상 또는 대체 원가 관리가 필요합니다.',
  },
  {
    label: '재구매율 여전히 낮음',
    priority: 'high',
    desc: '재구매율 35%가 업종 평균 48% 대비 여전히 낮습니다.',
  },
  {
    label: '온라인 주문 비중 목표 미달',
    priority: 'medium',
    desc: '온라인 주문 비중이 13%로 목표치 15%에 도달하지 못했습니다.',
  },
];

export const LOAN_STATUS: LoanStatus = {
  condition: HISTORY_LOAN_CONDITION,
  monthlyLoanPayment: HISTORY_MONTHLY_LOAN_PAYMENT,
  snapshotMonth: 3,
};

export const SIMULATION_HISTORY: SimulationHistoryEntry[] = [
  {
    id: 'round-1',
    round: 1,
    scenarioCode: 'B',
    planLabel: 'B · 설비 교체 + 업무 자동화',
    loanAmount: 3000,
    period: '2026.01~03',
    outcome: 'partial',
    revenue: { plan: '3,150~3,300만원', actual: '3,210만원' },
    profit: { plan: '370~430만원', actual: '352만원' },
    residual: { plan: '220~270만원', actual: '198만원' },
    bottleneckResolved: RESOLVED.map((b) => `${b.label} ${b.result}`),
    bottleneckRemaining: NEW_BOTTLENECKS.filter((b) => b.priority !== 'medium').map((b) => b.label),
  },
];

export const outcomeCfg: Record<SimulationOutcome, OutcomeConfig> = {
  achieved: {
    badge: 'bg-green-50 border-green-200 text-green-600',
    icon: CheckCircle2,
    label: '달성',
  },
  partial: {
    badge: 'bg-amber-50 border-amber-200 text-amber-700',
    icon: AlertTriangle,
    label: '부분 달성',
  },
  missed: {
    badge: 'bg-red-50 border-red-200 text-red-600',
    icon: AlertTriangle,
    label: '미달',
  },
};
