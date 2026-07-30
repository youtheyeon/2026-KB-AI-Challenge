import { FileSpreadsheet, FileText, Megaphone, Users, Wrench } from 'lucide-react';

import type { AllocationCategory, Bottleneck, RiskLevel, Scenario, UploadSlot } from './types';

export const STEPS = [
  '사업 데이터 연결',
  '사업 상태 분석',
  '대출 조건 입력',
  '자금 배분안 구성',
  '시나리오 비교',
];

export const SAMPLE = {
  name: '연희동 Y카페',
  bizType: '카페·베이커리',
  region: '서울특별시 서대문구 연희동',
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
    id: 'sales',
    label: '매출자료 (이지포스형)',
    hint: '매출요약·판매내역·반품내역',
    formats: 'xlsx',
    icon: FileSpreadsheet,
    badge: '필수',
    bc: 'bg-red-50 text-red-600 border-red-200',
  },
  {
    id: 'expense',
    label: '비용장부 (이지샵형)',
    hint: '거래처·비용항목·공급가액·부가세 등 비용 내역',
    formats: 'xlsx',
    icon: FileText,
    badge: '필수',
    bc: 'bg-red-50 text-red-600 border-red-200',
  },
  {
    id: 'onlineSales',
    label: '온라인매출 자료 (이지샵형)',
    hint: '배달플랫폼·PG·오픈마켓 주문 및 정산 내역',
    formats: 'xlsx',
    icon: FileSpreadsheet,
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
    evidenceSourceType: '공공데이터 벤치마크',
    evidenceDescription: '서울시 카페 업종 시간대별 추정 매출 벤치마크',
    relatedCategories: ['MARKETING_ONLINE'],
  },
  {
    id: 'customer',
    label: '고객 유지 부족',
    sev: 'high',
    desc: '재구매율 34%로 업종 평균 48% 대비 낮음. 신규 고객 유입 채널 다변화 필요.',
    metric: '재구매율 34% · 업종 평균 48%',
    conf: '높음',
    evidenceSourceType: '업계 가정치',
    evidenceDescription: '카페·베이커리 업종 평균 재구매율 가정치',
    relatedCategories: ['MARKETING_ONLINE'],
  },
  {
    id: 'cost',
    label: '원가율 상승',
    sev: 'medium',
    desc: '재료비 원가율 40%가 업종 평균 35% 대비 5%p 초과. 원자재 가격 변동에 취약.',
    metric: '재료비율 40% · 업종 평균 35%',
    conf: '보통',
    evidenceSourceType: '시연용 합성 비용 데이터',
    evidenceDescription: '이지샵형 비용장부 합성 데이터 기준 원가율',
    relatedCategories: ['INVENTORY', 'EQUIPMENT_INTERIOR'],
  },
  {
    id: 'capacity',
    label: '처리 용량 한계',
    sev: 'low',
    desc: '주말 피크 시간대 주문 처리 지연 신호. 직원 1인당 처리량 상한 근접.',
    metric: '직원당 주문 처리 210건/월',
    conf: '낮음',
    evidenceSourceType: '시연용 합성 매출 데이터',
    evidenceDescription: '이지포스형 매출자료 합성 데이터 기준 시간대별 처리량',
    relatedCategories: ['LABOR', 'EQUIPMENT_INTERIOR'],
  },
];

export const DEMO_RATE = 4.5;

export const CATEGORY_LABELS: Record<AllocationCategory, string> = {
  MARKETING_ONLINE: '마케팅·온라인',
  EQUIPMENT_INTERIOR: '설비·인테리어',
  LABOR: '인력',
  INVENTORY: '재고',
};

export const SCENARIOS: Scenario[] = [
  {
    id: 'A',
    type: '병목 집중형',
    icon: Megaphone,
    title: '광고·마케팅 + 온라인 채널 구축',
    desc: '가장 뚜렷한 병목인 온라인 채널 격차에 자금 대부분을 집중 배정합니다.',
    allocation: [
      {
        category: 'MARKETING_ONLINE',
        item: 'SNS·온라인 광고 및 채널 구축',
        amount: 1650,
        type: '반복',
      },
      { category: 'EQUIPMENT_INTERIOR', item: '설비·인테리어 개선', amount: 750, type: '일회성' },
      { category: 'LABOR', item: '인력 채용·교육', amount: 300, type: '반복' },
      { category: 'INVENTORY', item: '원재료·재고 확보', amount: 300, type: '반복' },
    ],
    revenueGrowthRange: [4, 8],
    profitRange: [1, 4],
    onlinePctRange: [17, 22],
    employees: 2,
    residualRange: [190, 250],
    addFixed: 80,
    breakEvenAdditionalRevenue: 350,
    requiredAdditionalOrders: 49,
    riskLevel: '중간',
    riskReasons: [
      '현재 상태 유지 시 월 잔여 현금은 양수이나 여유가 크지 않습니다.',
      '손익분기를 넘기려면 매월 약 350만원의 추가 매출이 필요합니다.',
    ],
    targetMetrics: ['온라인 주문 비중', '저녁 시간대 매출 비중', '신규 고객 유입 수'],
    assumptions: [
      'SNS 광고 전환율 2~4% 가정',
      '온라인 채널 구축 3개월 내 정착',
      '광고비 월 80만원 지출',
    ],
    risks: ['광고 효율이 낮으면 비용 대비 효과 미흡', '할인 프로모션이 마진을 잠식할 우려'],
    allocationRationale:
      '온라인 주문 비중이 9%로 비교군 평균 28% 대비 크게 낮게 나타났습니다. 이는 오프라인 매출에 편중된 판매 구조로 인해 온라인 채널을 통한 잠재 고객 상당수를 놓치고 있을 가능성을 시사합니다. 이 채널 격차에 가장 직접적으로 대응하는 SNS·온라인 광고 및 채널 구축에 전체 대출금의 55%(1,650만원)를 배정했습니다.',
    scbGrowthPotential:
      "SNS 광고와 온라인 채널 확장이 자리 잡으면 온라인 주문 비중과 신규 고객 유입이 늘어나는 효과로 이어질 수 있습니다. 이는 SCB의 '매출 심사분석' 지표 개선으로 연결될 수 있는 경로입니다. 또한 온라인 채널 노출이 확대되면 온라인 주문 비중 자체가 늘어나는 효과가 있어, SCB의 '유통플랫폼 성장지수'와 '고객 인지도·유입' 항목에서도 긍정적으로 반영될 가능성이 있습니다.",
  },
  {
    id: 'B',
    type: '진단 비례 대응형',
    icon: Wrench,
    title: '설비 교체 + 업무 자동화',
    desc: '발견된 여러 병목의 심각도에 비례해 자금을 분산 배정합니다.',
    allocation: [
      { category: 'EQUIPMENT_INTERIOR', item: '설비·인테리어 개선', amount: 1200, type: '일회성' },
      { category: 'LABOR', item: '인력 채용·교육', amount: 750, type: '반복' },
      {
        category: 'MARKETING_ONLINE',
        item: 'SNS·온라인 광고 및 채널 구축',
        amount: 600,
        type: '반복',
      },
      { category: 'INVENTORY', item: '원재료·재고 확보', amount: 450, type: '반복' },
    ],
    revenueGrowthRange: [3, 6],
    profitRange: [4, 8],
    onlinePctRange: [12, 16],
    employees: 2,
    residualRange: [220, 270],
    addFixed: 30,
    breakEvenAdditionalRevenue: 150,
    requiredAdditionalOrders: 21,
    riskLevel: '낮음',
    riskReasons: [
      '현재 상태 유지 시 월 잔여 현금이 안정적으로 양수입니다.',
      '월 추가 반복비용이 30만원으로 비교적 낮습니다.',
    ],
    targetMetrics: ['재료비 원가율', '피크 시간대 처리량', '월 잉여 현금'],
    assumptions: ['설비 교체로 원가율 개선 달성', '자동화로 피크 처리량 +25%', '설비 감가상각 5년'],
    risks: ['초기 1~2개월 적응 기간 발생', '실제 절감 성과가 추정보다 작을 수 있음'],
    allocationRationale:
      '재료비 원가율이 40.0%로 업종 평균 35% 대비 5%p 높게 나타났습니다. 이는 노후 설비로 인한 재료 손실이나 수작업 공정에서의 비효율이 원가에 반영되고 있을 가능성을 시사합니다. 발견된 병목들의 심각도에 비례해 자금을 배분해, 원가 구조를 직접 개선하는 설비·인테리어 개선에 40%(1,200만원)를 가장 크게 배정하고 나머지를 인력·마케팅·재고에 분산했습니다.',
    scbGrowthPotential:
      "설비 교체와 자동화가 자리 잡으면 원가율이 낮아지고 피크 시간대 처리량이 늘어나는 효과로 이어질 수 있습니다. 이는 SCB의 '매출 심사분석(수익성)' 지표 개선으로 연결될 수 있는 경로입니다. 또한 안정적인 현금흐름 유지가 SCB의 '재무 지속성' 평가에도 긍정적으로 반영될 가능성이 있습니다.",
  },
  {
    id: 'C',
    type: '균등 분산형',
    icon: Users,
    title: '전 영역 균등 투자',
    desc: '마케팅·설비·인력·재고 네 영역에 대출금을 동일한 비중으로 배분하는 비교 기준선입니다.',
    allocation: [
      {
        category: 'MARKETING_ONLINE',
        item: 'SNS·온라인 광고 및 채널 구축',
        amount: 750,
        type: '반복',
      },
      { category: 'EQUIPMENT_INTERIOR', item: '설비·인테리어 개선', amount: 750, type: '일회성' },
      { category: 'LABOR', item: '인력 채용·교육', amount: 750, type: '반복' },
      { category: 'INVENTORY', item: '원재료·재고 확보', amount: 750, type: '반복' },
    ],
    revenueGrowthRange: [5, 9],
    profitRange: [1, 3],
    onlinePctRange: [10, 14],
    employees: 3,
    residualRange: [110, 210],
    addFixed: 180,
    breakEvenAdditionalRevenue: 650,
    requiredAdditionalOrders: 92,
    riskLevel: '높음',
    riskReasons: [
      '월 추가 반복비용이 180만원으로 상대적으로 큽니다.',
      '손익분기를 넘기려면 매월 약 650만원의 추가 매출이 필요해 부담이 큽니다.',
    ],
    targetMetrics: ['온라인 주문 비중', '재료비 원가율', '직원당 처리량'],
    assumptions: [
      '네 영역 모두 3개월 내 집행 완료',
      '영역별 개선 효과는 점진적으로 발생',
      '특정 영역에 집중하지 않아 리스크가 분산됨',
    ],
    risks: [
      '특정 병목에 집중하지 않아 개선 속도가 느릴 수 있음',
      '영역별 투자 규모가 작아 개별 효과가 제한적일 수 있음',
    ],
    allocationRationale:
      '특정 병목에 집중하는 대신, 마케팅·설비·인력·재고 네 영역에 대출금을 동일한 비중(각 25%, 750만원)으로 배분한 비교 기준선입니다.',
    scbGrowthPotential:
      '네 영역에 고르게 투자하면 온라인 주문 비중, 원가 구조, 인력 규모 등 여러 지표가 동시에 소폭씩 개선될 수 있습니다. 이는 SCB의 여러 항목에 걸쳐 완만하지만 폭넓게 긍정적으로 반영될 가능성이 있는 경로입니다. 다만 각 영역의 개선 폭이 작아 특정 지표의 뚜렷한 개선을 기대하기는 어렵습니다.',
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
