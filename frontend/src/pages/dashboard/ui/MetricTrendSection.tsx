import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { TREND_DATA } from '@/entities/verify';
import type { DashboardMetricTrendResponse } from '@/shared/api/schema';
import { SectionLabel } from '@/shared/ui';

const METRIC_LABEL: Record<string, string> = {
  MONTHLY_SALES: '월 매출',
  OPERATING_PROFIT: '영업이익',
  ONLINE_ORDER_RATIO: '온라인 주문 비중',
  CASH_AFTER_REPAYMENT: '상환 후 잔여 현금',
};

const STATUS_LABEL: Record<string, string> = {
  ABOVE_EXPECTED: '예상 상단 초과',
  WITHIN_RANGE: '범위 내',
  BELOW_EXPECTED: '범위 미달',
  NOT_COMPARABLE: '비교 불가',
};

const formatMetricValue = (value: number | null, unit: string): string => {
  if (value === null) return '-';
  if (unit === 'RATIO') return `${(value * 100).toFixed(1)}%`;
  if (unit === 'KRW') return `${Math.round(value / 10_000).toLocaleString()}만원`;
  return value.toLocaleString();
};

interface MetricTrendSectionProps {
  isRealMode: boolean;
  metricTrends: DashboardMetricTrendResponse[] | null;
}

export const MetricTrendSection = ({ isRealMode, metricTrends }: MetricTrendSectionProps) => {
  if (isRealMode) {
    if (!metricTrends || metricTrends.length === 0) {
      return (
        <section className="space-y-4">
          <SectionLabel>핵심 지표 추이</SectionLabel>
          <div className="rounded border border-border px-5 py-8 text-center text-sm text-muted-foreground">
            아직 결과 검증이 완료된 지표가 없습니다.
          </div>
        </section>
      );
    }

    return (
      <section className="space-y-4">
        <SectionLabel>핵심 지표 추이</SectionLabel>
        <div className="overflow-hidden rounded border border-border">
          <div className="grid grid-cols-12 border-b border-border bg-muted/30 px-5 py-2.5">
            {[
              { label: '지표', span: 'col-span-4' },
              { label: '진행 전', span: 'col-span-2' },
              { label: '진행 후', span: 'col-span-2' },
              { label: '기록일', span: 'col-span-2' },
              { label: '상태', span: 'col-span-2' },
            ].map((h) => (
              <p key={h.label} className={`font-mono text-xs text-muted-foreground ${h.span}`}>
                {h.label}
              </p>
            ))}
          </div>
          {metricTrends.map((m, i) => (
            <div
              key={`${m.simulationId}-${m.metricCode}-${i}`}
              className="grid grid-cols-12 items-center border-b border-border px-5 py-3 last:border-0"
            >
              <p className="col-span-4 text-sm">{METRIC_LABEL[m.metricCode] ?? m.metricCode}</p>
              <p className="col-span-2 font-mono text-sm text-muted-foreground">
                {formatMetricValue(m.beforeValue, m.unit)}
              </p>
              <p className="col-span-2 font-mono text-sm font-semibold">
                {formatMetricValue(m.afterValue, m.unit)}
              </p>
              <p className="col-span-2 font-mono text-xs text-muted-foreground">
                {new Date(m.recordedAt).toLocaleDateString('ko-KR')}
              </p>
              <p className="col-span-2 font-mono text-xs text-muted-foreground">
                {STATUS_LABEL[m.status] ?? m.status}
              </p>
            </div>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <SectionLabel>핵심 지표 추이</SectionLabel>
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div className="space-y-3 rounded border border-border p-5">
          <p className="text-sm font-medium">매출·영업이익 (만원)</p>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={TREND_DATA} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 10, fill: 'var(--color-muted-foreground)' }}
              />
              <YAxis
                yAxisId="revenue"
                tick={{ fontSize: 10, fill: 'var(--color-muted-foreground)' }}
                domain={[2900, 3400]}
              />
              <YAxis
                yAxisId="profit"
                orientation="right"
                tick={{ fontSize: 10, fill: 'var(--color-muted-foreground)' }}
                domain={[300, 400]}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 11,
                  borderRadius: 6,
                  border: '1px solid var(--color-border)',
                }}
              />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              <Line
                yAxisId="revenue"
                type="monotone"
                dataKey="revenue"
                stroke="var(--color-foreground)"
                strokeWidth={2}
                dot={{ r: 3 }}
                name="매출"
              />
              <Line
                yAxisId="profit"
                type="monotone"
                dataKey="profit"
                stroke="#aaaaaa"
                strokeWidth={2}
                strokeDasharray="4 2"
                dot={{ r: 3 }}
                name="영업이익"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-3 rounded border border-border p-5">
          <p className="text-sm font-medium">온라인 주문 비중 (%)</p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={TREND_DATA} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 10, fill: 'var(--color-muted-foreground)' }}
              />
              <YAxis
                tick={{ fontSize: 10, fill: 'var(--color-muted-foreground)' }}
                domain={[0, 25]}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 11,
                  borderRadius: 6,
                  border: '1px solid var(--color-border)',
                }}
              />
              <ReferenceLine
                y={15}
                strokeDasharray="4 2"
                stroke="var(--color-muted-foreground)"
                label={{ value: '목표 15%', fill: 'var(--color-muted-foreground)', fontSize: 10 }}
              />
              <Bar
                dataKey="online"
                fill="var(--color-foreground)"
                opacity={0.6}
                name="온라인 비중 %"
                radius={[2, 2, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
};
