export function calcMonthly(
  loan: number,
  rate: number,
  years: number,
  grace: number,
  method: string,
): number {
  const p = loan * 10000;
  const r = rate / 100 / 12;
  const n = Math.max(1, (years - grace) * 12);
  if (method === 'bullet') return Math.round((p * rate) / 100 / 12 / 10000);
  if (!r) return Math.round(p / n / 10000);
  return Math.round((p * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1) / 10000);
}

export function calcPayback(investment: number, extraCashPerMonth: number): number {
  if (extraCashPerMonth <= 0) return 999;
  return Math.round(investment / extraCashPerMonth);
}
