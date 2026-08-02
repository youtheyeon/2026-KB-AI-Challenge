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
import { SectionLabel } from '@/shared/ui';

export const MetricTrendSection = () => {
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
