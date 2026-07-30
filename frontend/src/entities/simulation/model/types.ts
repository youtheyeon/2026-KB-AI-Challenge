import type { IconComponent } from '@/shared/lib/types';

export type SlotState = 'idle' | 'parsing' | 'done';

export interface UploadSlot {
  id: string;
  label: string;
  hint: string;
  formats: string;
  icon: IconComponent;
  badge: string;
  bc: string;
}

export type BottleneckSeverity = 'high' | 'medium' | 'low';

export interface Bottleneck {
  id: string;
  label: string;
  sev: BottleneckSeverity;
  desc: string;
  metric: string;
  conf: string;
}

export type AllocationCategory = 'MARKETING_ONLINE' | 'EQUIPMENT_INTERIOR' | 'LABOR' | 'INVENTORY';

export interface ScenarioAllocationItem {
  category: AllocationCategory;
  item: string;
  amount: number;
  type: string;
}

export interface Scenario {
  id: string;
  type: string;
  icon: IconComponent;
  title: string;
  desc: string;
  allocation: ScenarioAllocationItem[];
  revenueGrowthRange: [number, number];
  profitRange: [number, number];
  onlinePctRange: [number, number];
  employees: number;
  residualRange: [number, number];
  addFixed: number;
  riskLevel: RiskLevel;
  assumptions: string[];
  risks: string[];
  allocationRationale: string;
  scbGrowthPotential: string;
}

export type LoanRateMode = 'demo' | 'manual';

export interface LoanCond {
  loanAmount: number;
  rateMode: LoanRateMode;
  rate: number;
  period: number;
  grace: number;
  method: string;
  existingMonthly: number;
}

export type RiskLevel = '낮음' | '중간' | '높음';
