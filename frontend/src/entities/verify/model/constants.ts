import { AlertTriangle, CheckCircle2, Minus, TrendingUp } from 'lucide-react';

import { calcMonthly } from '@/entities/simulation';

import type {
  ArchivedSimulation,
  CompareRow,
  CompareStatus,
  CompareStatusConfig,
  ExecutionItem,
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

export const ARCHIVED_SIMS: ArchivedSimulation[] = [
  {
    id: 'sim-1',
    date: '2025.10.14',
    loanAmount: 3000,
    scenarios: [
      'A. 광고·마케팅 + 온라인 채널 구축',
      'B. 설비 교체 + 업무 자동화',
      'C. 직원 채용 + 처리 용량 확대',
    ],
    biz: '마포카페 · 서울 마포구',
    status: '진행 미등록',
    daysAgo: 91,
  },
];

export const DEFAULT_ITEMS: ExecutionItem[] = [
  { id: '1', name: '주방 설비 교체', amount: 1700 },
  { id: '2', name: '업무 자동화 시스템', amount: 500 },
  { id: '3', name: '마케팅', amount: 500 },
  { id: '4', name: '여유자금', amount: 300 },
];

export const TREND_DATA: TrendPoint[] = [
  { month: '진행 전', revenue: 3000, profit: 330, online: 9 },
  { month: '1개월', revenue: 3020, profit: 318, online: 10 },
  { month: '2개월', revenue: 3110, profit: 340, online: 12 },
  { month: '3개월', revenue: 3210, profit: 352, online: 13 },
];

export const COMPARE_ROWS: CompareRow[] = [
  {
    label: '매출 성장률',
    scbArea: '매출 심사분석',
    predicted: '4~7%',
    actual: '+7.0%',
    status: 'above',
    note: '예상 상단 초과',
    desc: '실제 지표는 기준 예상 범위를 소폭 초과했습니다. 같은 기간 상권 내 유동인구는 4% 증가했으므로, 지표만의 단독 효과로 판단할 수 없습니다.',
    external: '상권 내 유동인구 +4%, 업종 평균 매출 +3%',
  },
  {
    label: '온라인 주문 비중',
    scbArea: '유통플랫폼 성장',
    predicted: '12~16%',
    actual: '13%',
    status: 'in-range',
    note: '범위 내',
    desc: '온라인 주문 비중이 예상 범위 내에서 증가했습니다.',
    external: '배달앱 업종 평균 비중 +1.2%p',
  },
  {
    label: '영업이익',
    scbArea: '매출 심사분석 (수익성)',
    predicted: '3~5% 증가',
    actual: '+6.7% (352만원)',
    status: 'above',
    note: '예상 상단 초과',
    desc: '영업이익이 예상보다 소폭 크게 늘었습니다. 단, 원재료비 상승이 완전히 반영되기까지 오차가 있을 수 있습니다.',
    external: '원재료비 +6% 상승',
  },
  {
    label: '상환 후 여유 현금',
    scbArea: '재무 지속성',
    predicted: '220~270만원',
    actual: '198만원',
    status: 'miss',
    note: '범위 미달',
    desc: '여유 현금이 예상보다 낮습니다. 원가율 상승이 주요 관찰 요인입니다.',
    external: '–',
  },
  {
    label: '직원 수',
    scbArea: '근로자 수',
    predicted: '2명',
    actual: '2명',
    status: 'in-range',
    note: '일치',
    desc: '이 진행안에서는 고용 변화를 목적으로 하지 않았습니다.',
    external: '–',
  },
];

export const statusCfg: Record<CompareStatus, CompareStatusConfig> = {
  above: {
    badge: 'bg-blue-50 border-blue-200 text-blue-600',
    icon: TrendingUp,
    iconColor: 'text-blue-500',
  },
  'in-range': {
    badge: 'bg-green-50 border-green-200 text-green-600',
    icon: CheckCircle2,
    iconColor: 'text-green-500',
  },
  miss: {
    badge: 'bg-red-50 border-red-200 text-red-600',
    icon: AlertTriangle,
    iconColor: 'text-red-500',
  },
  partial: {
    badge: 'bg-amber-50 border-amber-200 text-amber-700',
    icon: Minus,
    iconColor: 'text-amber-500',
  },
};

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
