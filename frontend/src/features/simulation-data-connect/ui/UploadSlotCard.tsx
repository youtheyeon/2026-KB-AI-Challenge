import { CheckCircle2, Upload } from 'lucide-react';

import type { SlotState, UploadSlot } from '@/entities/simulation';

interface UploadSlotCardProps {
  slot: UploadSlot;
  state: SlotState;
  useSample: boolean;
  selectedFile: File | undefined;
  fileError: string | undefined;
  slotIssue: string | undefined;
  onFileChange: (file: File | undefined) => void;
}

export const UploadSlotCard = ({
  slot,
  state,
  useSample,
  selectedFile,
  fileError,
  slotIssue,
  onFileChange,
}: UploadSlotCardProps) => {
  const Icon = slot.icon;

  return (
    <div
      className={`space-y-3 rounded border p-4 ${
        state === 'done'
          ? 'border-foreground/30 bg-muted/10'
          : state === 'error'
            ? 'border-red-200 bg-red-50/40'
            : 'border-border'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          <p className="text-sm font-medium">{slot.label}</p>
        </div>
        <span className={`rounded border px-1.5 py-0.5 font-mono text-xs ${slot.bc}`}>
          {slot.badge}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">{slot.hint}</p>

      {!useSample && (state === 'idle' || state === 'error') && (
        <div className="space-y-1.5">
          <label className="flex flex-1 cursor-pointer items-center justify-center gap-2 rounded border border-dashed border-border px-3 py-2 text-xs text-muted-foreground transition-colors hover:border-foreground/40">
            <Upload className="h-3.5 w-3.5" />
            {selectedFile ? selectedFile.name : `파일 선택 (${slot.formats})`}
            <input
              type="file"
              accept=".xlsx"
              className="hidden"
              onChange={(e) => onFileChange(e.target.files?.[0])}
            />
          </label>
          {fileError && <p className="text-xs text-red-600">{fileError}</p>}
          {state === 'error' && slotIssue && <p className="text-xs text-red-600">{slotIssue}</p>}
        </div>
      )}

      {useSample && state === 'idle' && (
        <div className="flex items-center gap-2">
          <label className="flex flex-1 cursor-pointer items-center justify-center gap-2 rounded border border-dashed border-border px-3 py-2 text-xs text-muted-foreground transition-colors hover:border-foreground/40">
            <Upload className="h-3.5 w-3.5" />
            파일 선택 ({slot.formats})
            <input type="file" className="hidden" disabled />
          </label>
        </div>
      )}

      {state === 'parsing' && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-foreground/30 border-t-foreground" />
          컬럼 분석 중...
        </div>
      )}

      {state === 'done' && (
        <div className="flex items-center gap-1.5 text-xs text-green-600">
          <CheckCircle2 className="h-3.5 w-3.5" />
          분석 완료 · {slot.formats.split('·')[0].trim()} 파일
        </div>
      )}
    </div>
  );
};
