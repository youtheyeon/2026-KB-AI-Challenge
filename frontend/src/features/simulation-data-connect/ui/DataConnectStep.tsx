import { ChevronRight } from 'lucide-react';

import { Button } from '@/shared/ui';

import { useDataConnectStep } from '../model/useDataConnectStep';
import { BusinessInfoForm } from './BusinessInfoForm';
import { DataUploadPanel } from './DataUploadPanel';

interface DataConnectStepProps {
  isSample: boolean;
  businessId: number | null;
  onNext: () => void;
  onBusinessRegistered: (businessId: number) => void;
  onDatasetUploaded: (datasetId: number) => void;
}

export const DataConnectStep = (props: DataConnectStepProps) => {
  const {
    section,
    setSection,
    useSample,
    applySample,
    doneCount,
    canNext,
    form,
    registration,
    upload,
  } = useDataConnectStep(props);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">사업 데이터 연결</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            사업 기본정보를 입력하고 매출·비용 데이터를 연결하세요.
          </p>
        </div>
        <Button variant="outline" onClick={applySample} className="shrink-0 px-3 py-2">
          샘플로 체험
        </Button>
      </div>

      {useSample && (
        <div className="flex items-center gap-2 rounded border border-border bg-muted/40 px-4 py-2.5">
          <span className="rounded bg-foreground px-1.5 py-0.5 font-mono text-xs text-background">
            샘플 데이터 기반 시뮬레이션입니다
          </span>
          <p className="text-xs text-muted-foreground">실제 사업장 데이터를 사용하지 않습니다.</p>
        </div>
      )}

      <div className="flex border-b border-border">
        {(['info', 'upload'] as const).map((id) => (
          <button
            key={id}
            onClick={() => setSection(id)}
            className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
              section === id
                ? 'border-foreground text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {id === 'info' ? '1 · 기본정보' : '2 · 데이터 업로드'}
          </button>
        ))}
      </div>

      {section === 'info' && (
        <>
          <BusinessInfoForm form={form} registration={registration} />
          <div className="flex justify-end pt-2">
            <Button
              onClick={props.onNext}
              disabled={!canNext}
              className="px-5 py-2.5 disabled:cursor-not-allowed disabled:opacity-30"
            >
              분석 시작 <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </>
      )}

      {section === 'upload' && (
        <DataUploadPanel
          region={form.region}
          useSample={useSample}
          upload={upload}
          doneCount={doneCount}
          canNext={canNext}
          onBack={() => setSection('info')}
        />
      )}
    </div>
  );
};
