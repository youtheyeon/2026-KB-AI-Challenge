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
    desc: 'POS 매출, 비용, 온라인 정산 데이터를 분석하고 유사한 영업 특성의 비교군과 대조해 현재 사업의 병목 후보를 파악합니다.',
  },
  {
    icon: BarChart2,
    title: 'A·B·C 배분안 중립 비교',
    desc: '병목 집중형·진단 비례형·균등형 세 가지 자금 배분안을 구성하고 각 안의 배분 근거와 위험 요인을 동일한 기준으로 비교합니다. 특정 안을 추천하지 않습니다.',
  },
  {
    icon: TrendingUp,
    title: '재무 부담 계산',
    desc: '대출 조건과 자금 배분 내역을 기준으로 월 원리금, 추가 고정비, 상환 후 잔여현금과 손익분기 조건을 계산합니다.',
  },
  {
    icon: RefreshCw,
    title: '실행 결과 기반 재평가',
    desc: '실행 후 실제 매출·비용 데이터를 바탕으로 병목 개선 여부와 계획 대비 차이를 확인하고 다음 자금 계획에 반영합니다.',
  },
];

export const SIMULATION_TAGS = [
  '사업 현황·병목 진단',
  'A·B·C 배분안 구성',
  '재무 부담·위험 비교',
  '시뮬레이션 결과 저장',
];

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
  plan: 'A·B·C 자금 배분안 3개 저장',
  daysAgo: 91,
  loanAmount: '3,000만원',
  monthlyRepay: '85만원',
  bottleneck: '낮은 온라인 판매 비중',
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
    label: '병목 진단·배분안 비교',
    desc: '사업 데이터를 분석해 현재 병목을 진단하고, A·B·C 자금 배분안의 구성과 재무 부담을 비교합니다.',
  },
  {
    num: '02',
    label: '실제 자금 집행',
    desc: '비교 결과를 참고해 자금 사용 방식을 직접 결정하고 실제로 자금을 집행합니다.',
    muted: true,
  },
  {
    num: '03',
    label: '실행·성과 등록',
    desc: '90일이 지난 후 실제로 진행한 배분안과 실행 기간의 매출·비용 데이터를 등록합니다.',
  },
  {
    num: '04',
    label: '결과 검증·재평가',
    desc: '계획과 실제 결과의 차이, 병목 개선 여부와 새롭게 발생한 위험을 확인하고 최신 사업 상태를 다음 시뮬레이션에 반영합니다.',
  },
];
