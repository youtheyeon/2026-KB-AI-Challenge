import { ChevronLeft, ChevronRight, MapPin, CheckCircle2 } from 'lucide-react';

import { UPLOAD_SLOTS } from '@/entities/simulation';
import { Button, ErrorBanner } from '@/shared/ui';

import type { DataConnectUploadState } from '../model/useDataConnectStep';
import { UploadSlotCard } from './UploadSlotCard';
import { UploadSummary } from './UploadSummary';

interface DataUploadPanelProps {
  region: string;
  useSample: boolean;
  upload: DataConnectUploadState;
  doneCount: number;
  canNext: boolean;
  onBack: () => void;
}

export const DataUploadPanel = ({
  region,
  useSample,
  upload,
  doneCount,
  canNext,
  onBack,
}: DataUploadPanelProps) => (
  <div className="space-y-4">
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {UPLOAD_SLOTS.map((slot) => (
        <UploadSlotCard
          key={slot.id}
          slot={slot}
          state={upload.slots[slot.id]}
          useSample={useSample}
          selectedFile={upload.files[slot.id]}
          fileError={upload.fileErrors[slot.id]}
          slotIssue={upload.slotIssues[slot.id]}
          onFileChange={(file) => upload.handleFileChange(slot.id, file)}
        />
      ))}
    </div>

    <div className="flex items-center gap-2 rounded border border-border bg-muted/10 px-4 py-3">
      <MapPin className="h-4 w-4 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium">상권 데이터 자동 조회 완료</p>
        <p className="text-xs text-muted-foreground">
          {region || '등록된 사업 지역'} 기준으로 공공데이터를 자동 조회했습니다. 별도 업로드가
          필요하지 않습니다.
        </p>
      </div>
      <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />
    </div>

    {upload.uploadError && <ErrorBanner message={upload.uploadError} />}

    <UploadSummary
      useSample={useSample}
      doneCount={doneCount}
      datasetResult={upload.datasetResult}
    />

    <div className="flex justify-between">
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ChevronLeft className="h-4 w-4" />
        기본정보
      </button>
      <Button
        onClick={upload.handleUploadAndAnalyze}
        disabled={
          useSample ? !canNext : !upload.files.sales || !upload.files.expense || upload.uploading
        }
        className="px-5 py-2.5 disabled:cursor-not-allowed disabled:opacity-30"
      >
        {upload.uploading ? '업로드 및 분석 중...' : '사업 상태 분석하기'}{' '}
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  </div>
);
