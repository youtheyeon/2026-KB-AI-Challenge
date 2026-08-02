import { ChevronRight } from 'lucide-react';

import { Button, ErrorBanner } from '@/shared/ui';

import type {
  DataConnectFormState,
  DataConnectRegistrationState,
} from '../model/useDataConnectStep';

const CHANNELS = ['홀 판매', '배달 플랫폼', '포장', '온라인 판매', '기타'];
const BIZ_TYPES = ['외식업', '카페·베이커리', '소매업', '미용·생활서비스', '숙박업', '기타'];

interface BusinessInfoFormProps {
  form: DataConnectFormState;
  registration: DataConnectRegistrationState;
}

export const BusinessInfoForm = ({ form, registration }: BusinessInfoFormProps) => {
  const canGoToUpload = Boolean(form.name && form.bizType && form.region);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {[
          { label: '사업장명 *', val: form.name, setter: form.setName, ph: '예: 마포떡볶이' },
          { label: '사업 지역 *', val: form.region, setter: form.setRegion, ph: '예: 서울 마포구' },
        ].map((f) => (
          <div key={f.label} className="space-y-1.5">
            <label className="font-mono text-xs text-muted-foreground">{f.label}</label>
            <input
              value={f.val}
              onChange={(e) => f.setter(e.target.value)}
              placeholder={f.ph}
              className="w-full rounded border border-border bg-input-background px-3 py-2 text-sm focus:border-foreground focus:outline-none"
            />
          </div>
        ))}
        <div className="space-y-1.5">
          <label className="font-mono text-xs text-muted-foreground">업종 *</label>
          <select
            value={form.bizType}
            onChange={(e) => form.setBizType(e.target.value)}
            className="w-full rounded border border-border bg-input-background px-3 py-2 text-sm focus:border-foreground focus:outline-none"
          >
            <option value="">선택하세요</option>
            {BIZ_TYPES.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="font-mono text-xs text-muted-foreground">직원 수</label>
          <input
            type="number"
            min={0}
            value={form.employees}
            onChange={(e) => form.setEmployees(e.target.value)}
            placeholder="예: 2"
            className="w-full rounded border border-border bg-input-background px-3 py-2 text-sm focus:border-foreground focus:outline-none"
          />
        </div>
      </div>

      <div className="space-y-2">
        <label className="font-mono text-xs text-muted-foreground">주요 판매 채널</label>
        <div className="flex flex-wrap gap-2">
          {CHANNELS.map((c) => (
            <button
              key={c}
              onClick={() => form.toggleChannel(c)}
              className={`rounded border px-3 py-1.5 text-xs font-medium transition-colors ${
                form.channels.includes(c)
                  ? 'border-foreground bg-foreground text-background'
                  : 'border-border text-muted-foreground hover:border-foreground/40'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {registration.registerError && <ErrorBanner message={registration.registerError} />}

      <div className="flex justify-end">
        <Button
          variant="outline"
          onClick={registration.handleGoToUpload}
          disabled={!canGoToUpload || registration.registering}
          className="px-4 py-2 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {registration.registering ? '등록 중...' : '데이터 업로드'}{' '}
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};
