import type { IconComponent } from '@/shared/lib/types';

export interface ArchivedSimulation {
  id: string;
  date: string;
  loanAmount: number;
  scenarios: string[];
  biz: string;
  status: string;
  daysAgo: number;
}

export interface ExecutionItem {
  id: string;
  name: string;
  amount: number;
}

export interface TrendPoint {
  month: string;
  revenue: number;
  profit: number;
  online: number;
}

export type CompareStatus = 'above' | 'in-range' | 'miss' | 'partial';

export interface CompareRow {
  label: string;
  scbArea: string;
  predicted: string;
  actual: string;
  status: CompareStatus;
  note: string;
  desc: string;
  external: string;
}

export interface CompareStatusConfig {
  badge: string;
}

export interface ReevalMetric {
  label: string;
  before: string;
  after: string;
  up: boolean;
}

export interface ResolvedBottleneck {
  label: string;
  result: string;
}

export type NewBottleneckPriority = 'high' | 'medium' | 'low';

export interface NewBottleneck {
  label: string;
  priority: NewBottleneckPriority;
  desc: string;
}

export type RepaymentType = 'EQUAL_PAYMENT' | 'EQUAL_PRINCIPAL' | 'BULLET_PAYMENT';

export interface LoanCondition {
  amount: number;
  annualInterestRate: number;
  termMonths: number;
  graceMonths: number;
  repaymentType: RepaymentType;
}

export interface LoanStatus {
  condition: LoanCondition;
  monthlyLoanPayment: number;
  snapshotMonth: number;
}

export type SimulationOutcome = 'achieved' | 'partial' | 'missed';

export interface SimulationHistoryMetric {
  plan: string;
  actual: string;
}

export interface SimulationHistoryEntry {
  id: string;
  round: number;
  scenarioCode: string;
  planLabel: string;
  loanAmount: number;
  period: string;
  outcome: SimulationOutcome;
  revenue: SimulationHistoryMetric;
  profit: SimulationHistoryMetric;
  residual: SimulationHistoryMetric;
  bottleneckResolved: string[];
  bottleneckRemaining: string[];
}

export interface OutcomeConfig {
  badge: string;
  icon: IconComponent;
  label: string;
}
