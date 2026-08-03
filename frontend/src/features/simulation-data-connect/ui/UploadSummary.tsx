import { DatasetFileType, type DatasetStatusResponse } from '@/shared/api/schema';

interface UploadSummaryProps {
  useSample: boolean;
  doneCount: number;
  datasetResult: DatasetStatusResponse | null;
}

interface SummaryItem {
  label: string;
  value: string | number | undefined;
}

const SAMPLE_ITEMS = (doneCount: number): SummaryItem[] => [
  { label: '분석 기간', value: '2026.01~2026.06' },
  { label: '매출 거래', value: doneCount >= 1 ? '4,820건' : undefined },
  { label: '비용 거래', value: doneCount >= 2 ? '1,130건' : undefined },
  { label: '누락값', value: doneCount >= 1 ? '12건' : undefined },
];

const realItems = (datasetResult: DatasetStatusResponse | null): SummaryItem[] => [
  {
    label: '매출 거래',
    value: datasetResult?.files.find((f) => f.fileType === DatasetFileType.Sale)?.rowCount,
  },
  {
    label: '비용 거래',
    value: datasetResult?.files.find((f) => f.fileType === DatasetFileType.Expense)?.rowCount,
  },
  {
    label: '온라인 거래',
    value: datasetResult?.files.find((f) => f.fileType === DatasetFileType.OnlineSale)?.rowCount,
  },
  {
    label: '누락값',
    value: datasetResult?.files.reduce((sum, f) => sum + f.missingColumns.length, 0),
  },
];

const formatValue = (value: SummaryItem['value']) => {
  if (value === undefined) return '–';
  return typeof value === 'number' ? `${value.toLocaleString()}건` : value;
};

export const UploadSummary = ({ useSample, doneCount, datasetResult }: UploadSummaryProps) => {
  const items = useSample ? SAMPLE_ITEMS(doneCount) : realItems(datasetResult);

  return (
    <div className="space-y-1.5 rounded border border-border bg-muted/10 px-5 py-4">
      <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
        분석 결과 요약
      </p>
      <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {items.map((item) => (
          <div key={item.label}>
            <p className="text-xs text-muted-foreground">{item.label}</p>
            <p className="mt-0.5 font-mono text-sm">{formatValue(item.value)}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
