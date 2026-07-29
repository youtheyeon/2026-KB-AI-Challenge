import { FileSpreadsheet, FileText, Megaphone, Users, Wrench } from 'lucide-react';

import type { Bottleneck, RiskLevel, Scenario, UploadSlot } from './types';

export const STEPS = [
  '사업 데이터 연결',
  '사업 상태 분석',
  '대출 조건 입력',
  '자금 배분안 구성',
  '시나리오 비교',
];

export const SAMPLE = {
  name: '마포카페',
  bizType: '카페·베이커리',
  region: '서울 마포구',
  years: '4년',
  employees: '2명',
  channels: ['홀 판매', '포장'],
  monthly: 3000,
  profit: 330,
  profitRate: 11.0,
  materialCost: 40.0,
  laborCost: 28.0,
  fixedCost: 18.0,
  residual: 180,
  employees_n: 2,
  orderCount: 420,
  avgTicket: 7.1,
  rebuyRate: 34,
  onlinePct: 9,
  revenueGrowth: 2.1,
};

export const UPLOAD_SLOTS: UploadSlot[] = [
  {
    id: 'card',
    label: '카드·POS 매출',
    hint: '카드사 원장 또는 POS 매출 리포트',
    formats: 'xlsx · csv',
    icon: FileSpreadsheet,
    badge: '필수',
    bc: 'bg-red-50 text-red-600 border-red-200',
  },
  {
    id: 'cost',
    label: '비용 내역',
    hint: '재료비·인건비·임차료 등 지출 항목',
    formats: 'xlsx · csv',
    icon: FileText,
    badge: '필수',
    bc: 'bg-red-50 text-red-600 border-red-200',
  },
  {
    id: 'online',
    label: '온라인·플랫폼 데이터',
    hint: '배달 플랫폼 주문·방문·재방문 현황',
    formats: 'xlsx · csv',
    icon: FileSpreadsheet,
    badge: '권장',
    bc: 'bg-amber-50 text-amber-700 border-amber-200',
  },
  {
    id: 'district',
    label: '상권 데이터',
    hint: '인근 인구·경쟁점 상권 분석 리포트',
    formats: 'xlsx · pdf',
    icon: FileText,
    badge: '선택',
    bc: 'bg-secondary text-muted-foreground border-border',
  },
];

export const BOTTLENECKS: Bottleneck[] = [
  {
    id: 'channel',
    label: '판매 채널 편중',
    sev: 'high',
    desc: '오프라인 매출 비중 91%로 온라인 주문 증가율이 비교군 대비 낮음. 특정 시간대 주문 집중.',
    metric: '온라인 주문 비중 9% · 비교군 28%',
    conf: '보통',
  },
  {
    id: 'customer',
    label: '고객 유지 부족',
    sev: 'high',
    desc: '재구매율 34%로 업종 평균 48% 대비 낮음. 신규 고객 유입 채널 다변화 필요.',
    metric: '재구매율 34% · 업종 평균 48%',
    conf: '높음',
  },
  {
    id: 'cost',
    label: '원가율 상승',
    sev: 'medium',
    desc: '재료비 원가율 40%가 업종 평균 35% 대비 5%p 초과. 원자재 가격 변동에 취약.',
    metric: '재료비율 40% · 업종 평균 35%',
    conf: '보통',
  },
  {
    id: 'capacity',
    label: '처리 용량 한계',
    sev: 'low',
    desc: '주말 피크 시간대 주문 처리 지연 신호. 직원 1인당 처리량 상한 근접.',
    metric: '직원당 주문 처리 210건/월',
    conf: '낮음',
  },
];

export const DEMO_RATE = 4.5;

export const SCENARIOS: Scenario[] = [
  {
    id: 'A',
    type: '고객 유입 활성화',
    icon: Megaphone,
    title: '광고·마케팅 + 온라인 채널 구축',
    desc: 'SNS 광고와 온라인 채널 확장으로 신규 고객 유입과 온라인 주문 비중을 늘립니다.',
    allocation: [
      { item: 'SNS·온라인 광고', amount: 1200, type: '반복' },
      { item: '온라인 채널 구축', amount: 1000, type: '일회성' },
      { item: '여유자금', amount: 800, type: '여유' },
    ],
    revenueGrowthRange: [4, 8],
    profitRange: [1, 4],
    onlinePctRange: [17, 22],
    employees: 2,
    residualRange: [190, 250],
    addFixed: 80,
    riskLevel: '중간',
    assumptions: [
      'SNS 광고 전환율 2~4% 가정',
      '온라인 채널 구축 3개월 내 정착',
      '광고비 월 80만원 지출',
    ],
    risks: ['광고 효율이 낮으면 비용 대비 효과 미흡', '할인 프로모션이 마진을 잠식할 우려'],
    allocationRationale:
      '온라인 주문 비중이 9%로 비교군 평균 28% 대비 크게 낮게 나타났습니다. 이는 오프라인 매출에 편중된 판매 구조로 인해 온라인 채널을 통한 잠재 고객 상당수를 놓치고 있을 가능성을 시사합니다. SNS·온라인 광고와 온라인 채널 구축은 이 채널 격차를 직접 겨냥하는 성격의 지출이라, 전체 대출금의 73%(2,200만원)를 두 항목에 배정했습니다.',
    scbGrowthPotential:
      "SNS 광고와 온라인 채널 확장이 자리 잡으면 온라인 주문 비중과 신규 고객 유입이 늘어나는 효과로 이어질 수 있습니다. 이는 SCB의 '매출 심사분석' 지표 개선으로 연결될 수 있는 경로입니다. 또한 온라인 채널 노출이 확대되면 온라인 주문 비중 자체가 늘어나는 효과가 있어, SCB의 '유통플랫폼 성장지수'와 '고객 인지도·유입' 항목에서도 긍정적으로 반영될 가능성이 있습니다.",
  },
  {
    id: 'B',
    type: '운영 효율 개선',
    icon: Wrench,
    title: '설비 교체 + 업무 자동화',
    desc: '주방 설비 교체와 주문관리 자동화로 원가율을 낮추고 운영 효율을 개선합니다.',
    allocation: [
      { item: '주방 설비 교체', amount: 1800, type: '일회성' },
      { item: '업무 자동화 시스템', amount: 700, type: '일회성' },
      { item: '여유자금', amount: 500, type: '여유' },
    ],
    revenueGrowthRange: [3, 6],
    profitRange: [4, 8],
    onlinePctRange: [12, 16],
    employees: 2,
    residualRange: [220, 270],
    addFixed: 30,
    riskLevel: '낮음',
    assumptions: ['설비 교체로 원가율 개선 달성', '자동화로 피크 처리량 +25%', '설비 감가상각 5년'],
    risks: ['초기 1~2개월 적응 기간 발생', '실제 절감 성과가 추정보다 작을 수 있음'],
    allocationRationale:
      '재료비 원가율이 40.0%로 업종 평균 35% 대비 5%p 높게 나타났습니다. 이는 노후 설비로 인한 재료 손실이나 수작업 공정에서의 비효율이 원가에 반영되고 있을 가능성을 시사합니다. 주방 설비 교체와 업무 자동화는 이 원가 구조를 직접 개선하는 성격의 지출이라, 전체 대출금의 83%(2,500만원)를 두 항목에 배정했습니다.',
    scbGrowthPotential:
      "설비 교체와 자동화가 자리 잡으면 원가율이 낮아지고 피크 시간대 처리량이 늘어나는 효과로 이어질 수 있습니다. 이는 SCB의 '매출 심사분석(수익성)' 지표 개선으로 연결될 수 있는 경로입니다. 또한 안정적인 현금흐름 유지가 SCB의 '재무 지속성' 평가에도 긍정적으로 반영될 가능성이 있습니다.",
  },
  {
    id: 'C',
    type: '처리 역량 확대',
    icon: Users,
    title: '직원 채용 + 처리 용량 확대',
    desc: '추가 인력 채용과 판매 역량 확대로 매출 상한을 높이는 방향입니다.',
    allocation: [
      { item: '직원 채용·교육', amount: 1200, type: '반복' },
      { item: '처리 역량 인프라', amount: 1200, type: '일회성' },
      { item: '여유자금', amount: 600, type: '여유' },
    ],
    revenueGrowthRange: [5, 9],
    profitRange: [1, 3],
    onlinePctRange: [10, 14],
    employees: 3,
    residualRange: [110, 210],
    addFixed: 180,
    riskLevel: '높음',
    assumptions: [
      '추가 인력 2개월 내 채용 완료',
      '매출 증가가 고정비 증가 대비 필요',
      '배달 성능 개선 3개월 내 안착',
    ],
    risks: ['추가 인건비 고정으로 매출 부진 시 손익 악화', '예상보다 마진이 낮아질 수 있음'],
    allocationRationale:
      '직원당 주문 처리량이 210건/월로 상한에 근접해 있고, 주말 피크 시간대 주문 처리 지연 신호가 관찰되었습니다. 이는 현재 인력 규모로는 늘어나는 주문을 처리할 여력이 부족할 가능성을 시사합니다. 직원 채용·교육과 처리 역량 인프라는 이 처리 용량 한계를 직접 해소하는 성격의 지출이라, 전체 대출금의 80%(2,400만원)를 두 항목에 배정했습니다.',
    scbGrowthPotential:
      "추가 인력과 처리 인프라가 자리 잡으면 매출 상한이 높아지고 배달 처리 성능이 개선되는 효과로 이어질 수 있습니다. 직원 수 증가는 SCB의 '근로자 수' 항목에 직접 반영되며, 처리 용량 확대로 인한 매출 증가 가능성은 '매출 심사분석'에도 영향을 미칠 수 있습니다. 다만 고정비 증가로 수익성 지표가 단기적으로 하락할 수 있어 SCB 평가에 복합적으로 반영될 수 있습니다.",
  },
];

export const riskColor: Record<RiskLevel, string> = {
  낮음: 'text-green-600',
  중간: 'text-amber-600',
  높음: 'text-red-500',
};

export const sevCfg = {
  high: { dot: 'bg-red-500', badge: 'bg-red-50 border-red-200 text-red-600', label: '우선 확인' },
  medium: {
    dot: 'bg-amber-400',
    badge: 'bg-amber-50 border-amber-200 text-amber-700',
    label: '확인 필요',
  },
  low: {
    dot: 'bg-muted-foreground/30',
    badge: 'bg-secondary border-border text-muted-foreground',
    label: '참고',
  },
} as const;
