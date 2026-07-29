import type { LucideIcon } from 'lucide-react';
import { BarChart2, Cpu, RefreshCw, TrendingUp } from 'lucide-react';

export type Feature = {
  icon: LucideIcon;
  title: string;
  desc: string;
};

export const FEATURES: Feature[] = [
  {
    icon: Cpu,
    title: '사업 현황·병목 진단',
    desc: '매출·비용·자금 데이터를 분석해 현재 사업의 병목 후보를 파악합니다.',
  },
  {
    icon: BarChart2,
    title: 'A·B·C 배분안 중립 비교',
    desc: '서로 다른 세 가지 자금 배분안의 예상 효과와 위험을 동일한 기준으로 비교합니다. 특정 안을 추천하지 않습니다.',
  },
  {
    icon: TrendingUp,
    title: '재무 시뮬레이션',
    desc: '월 이자율·예상 매출·비용·예상이익·상환 후 잔여 현금을 계산 엔진으로 산출합니다.',
  },
  {
    icon: RefreshCw,
    title: '점진적 구조',
    desc: '진행 후 실제 성과를 추적하고 갱신된 사업 상태로 다시 시뮬레이션의 초기 조건을 자동 반영합니다.',
  },
];

export const SIMULATION_TAGS = ['병목 진단', '3가지 배분안 비교', '재무 시뮬레이션', '배분안 저장'];

export type ArchivedSimulation = {
  id: string;
  plan: string;
  daysAgo: number;
  loanAmount: string;
  monthlyRepay: string;
  bottleneck: string;
};

export const ARCHIVED: ArchivedSimulation = {
  id: '25.10.14',
  plan: 'B안 · 설비 교체 + 사무 자동화',
  daysAgo: 91,
  loanAmount: '3,000만원',
  monthlyRepay: '85만원',
  bottleneck: '판매채널 편중 (온라인 9%)',
};

export type ProcessStep = {
  num: string;
  label: string;
  desc: string;
  muted?: boolean;
};

export const PROCESS_STEPS: ProcessStep[] = [
  {
    num: '01',
    label: '자금 배분 시뮬레이션',
    desc: 'A·B·C 배분안 비교 후 원하는 안을 직접 선택해 저장합니다',
  },
  {
    num: '02',
    label: '실제 진행 (3개월)',
    desc: '저장된 계획대로 자금을 진행합니다.',
    muted: true,
  },
  {
    num: '03',
    label: '결과 확인',
    desc: '3개월 후 실제 지표를 저장된 예측값과 비교합니다',
  },
  {
    num: '04',
    label: '재평가·다음 회차',
    desc: '실제 결과가 다시 시뮬레이션의 초기 조건으로 자동 반영됩니다',
  },
];
