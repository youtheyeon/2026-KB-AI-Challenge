import { CheckCircle2, ChevronLeft, ChevronRight, Info, Upload } from 'lucide-react';
import { useState } from 'react';

import { COL_MAPS, SAMPLE, UPLOAD_SLOTS, type SlotState } from '@/entities/simulation';

const CHANNELS = ['홀 판매', '배달 플랫폼', '포장', '온라인 판매', '기타'];
const BIZ_TYPES = ['외식업', '카페·베이커리', '소매업', '미용·생활서비스', '숙박업', '기타'];

type Section = 'info' | 'upload' | 'mapping';

interface DataConnectStepProps {
  isSample: boolean;
  onNext: () => void;
}

export const DataConnectStep = ({ isSample, onNext }: DataConnectStepProps) => {
  const [name, setName] = useState(isSample ? SAMPLE.name : '');
  const [bizType, setBizType] = useState(isSample ? SAMPLE.bizType : '');
  const [region, setRegion] = useState(isSample ? SAMPLE.region : '');
  const [employees, setEmployees] = useState(isSample ? SAMPLE.employees : '');
  const [channels, setChannels] = useState<string[]>(isSample ? SAMPLE.channels : []);
  const [slots, setSlots] = useState<Record<string, SlotState>>(
    Object.fromEntries(UPLOAD_SLOTS.map((s) => [s.id, isSample ? 'done' : 'idle'])),
  );
  const [section, setSection] = useState<Section>('info');
  const [useSample, setUseSample] = useState(isSample);

  const trigger = (id: string) => {
    setSlots((p) => ({ ...p, [id]: 'parsing' }));
    setTimeout(() => setSlots((p) => ({ ...p, [id]: 'done' })), 1300);
  };

  const applySample = () => {
    setUseSample(true);
    setName(SAMPLE.name);
    setBizType(SAMPLE.bizType);
    setRegion(SAMPLE.region);
    setEmployees(SAMPLE.employees);
    setChannels(SAMPLE.channels);
    setSlots(Object.fromEntries(UPLOAD_SLOTS.map((s) => [s.id, 'done'])));
    setSection('upload');
  };

  const doneCount = Object.values(slots).filter((v) => v === 'done').length;
  const reqDone = ['card', 'cost'].every((id) => slots[id] === 'done');
  const canNext = Boolean(name && bizType && region && reqDone);

  const toggleChannel = (c: string) =>
    setChannels((p) => (p.includes(c) ? p.filter((x) => x !== c) : [...p, c]));

  const sectionTab = (id: Section, label: string) => (
    <button
      onClick={() => setSection(id)}
      className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
        section === id
          ? 'border-foreground text-foreground'
          : 'border-transparent text-muted-foreground hover:text-foreground'
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">사업 데이터 연결</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            사업 기본정보를 입력하고 매출·비용 데이터를 연결하세요.
          </p>
        </div>
        <button
          onClick={applySample}
          className="shrink-0 rounded border border-border px-3 py-2 text-sm transition-colors hover:bg-secondary"
        >
          샘플로 체험
        </button>
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
        {sectionTab('info', '1 · 기본정보')}
        {sectionTab('upload', '2 · 데이터 업로드')}
        {sectionTab('mapping', '3 · 컬럼 매핑 확인')}
      </div>

      {section === 'info' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {[
              { label: '사업장명 *', val: name, setter: setName, ph: '예: 마포떡볶이' },
              { label: '사업 지역 *', val: region, setter: setRegion, ph: '예: 서울 마포구' },
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
                value={bizType}
                onChange={(e) => setBizType(e.target.value)}
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
                value={employees}
                onChange={(e) => setEmployees(e.target.value)}
                placeholder="예: 2명"
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
                  onClick={() => toggleChannel(c)}
                  className={`rounded border px-3 py-1.5 text-xs font-medium transition-colors ${
                    channels.includes(c)
                      ? 'border-foreground bg-foreground text-background'
                      : 'border-border text-muted-foreground hover:border-foreground/40'
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>
          <div className="flex justify-end">
            <button
              onClick={() => setSection('upload')}
              className="flex items-center gap-2 rounded border border-border px-4 py-2 text-sm transition-colors hover:bg-secondary"
            >
              다음: 데이터 업로드 <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {section === 'upload' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {UPLOAD_SLOTS.map((slot) => {
              const Icon = slot.icon;
              const state = slots[slot.id];
              return (
                <div
                  key={slot.id}
                  className={`space-y-3 rounded border p-4 ${
                    state === 'done' ? 'border-foreground/30 bg-muted/10' : 'border-border'
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
                  {state === 'idle' && (
                    <div className="flex items-center gap-2">
                      <label className="flex flex-1 cursor-pointer items-center justify-center gap-2 rounded border border-dashed border-border px-3 py-2 text-xs text-muted-foreground transition-colors hover:border-foreground/40">
                        <Upload className="h-3.5 w-3.5" />
                        파일 선택 ({slot.formats})
                        <input type="file" className="hidden" />
                      </label>
                      <button
                        onClick={() => trigger(slot.id)}
                        className="text-xs whitespace-nowrap text-muted-foreground underline hover:text-foreground"
                      >
                        샘플
                      </button>
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
            })}
          </div>
          <div className="space-y-1.5 rounded border border-border bg-muted/10 px-5 py-4">
            <p className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
              분석 결과 요약
            </p>
            <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: '분석 기간', value: '2026.01~2026.06' },
                { label: '매출 거래', value: doneCount >= 1 ? '4,820건' : '–' },
                { label: '비용 거래', value: doneCount >= 2 ? '1,130건' : '–' },
                { label: '누락값', value: doneCount >= 1 ? '12건' : '–' },
              ].map((s) => (
                <div key={s.label}>
                  <p className="text-xs text-muted-foreground">{s.label}</p>
                  <p className="mt-0.5 font-mono text-sm">{s.value}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="flex justify-between">
            <button
              onClick={() => setSection('info')}
              className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <ChevronLeft className="h-4 w-4" />
              기본정보
            </button>
            <button
              onClick={() => setSection('mapping')}
              className="flex items-center gap-2 rounded border border-border px-4 py-2 text-sm transition-colors hover:bg-secondary"
            >
              컬럼 매핑 확인 <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {section === 'mapping' && (
        <div className="space-y-4">
          <div className="overflow-hidden rounded border border-border">
            <div className="grid grid-cols-12 border-b border-border bg-muted/30 px-5 py-2.5">
              {['원본 컬럼', '변환 컬럼', '신뢰도', ''].map((h, i) => (
                <p
                  key={h || i}
                  className={`font-mono text-xs text-muted-foreground ${
                    i === 0
                      ? 'col-span-3'
                      : i === 1
                        ? 'col-span-4'
                        : i === 2
                          ? 'col-span-2'
                          : 'col-span-3'
                  }`}
                >
                  {h}
                </p>
              ))}
            </div>
            {COL_MAPS.map((m) => (
              <div
                key={m.orig}
                className="grid grid-cols-12 items-center border-b border-border px-5 py-3 last:border-0"
              >
                <p className="col-span-3 font-mono text-sm">{m.orig}</p>
                <p className="col-span-4 font-mono text-sm text-muted-foreground">→ {m.mapped}</p>
                <p className={`col-span-2 font-mono text-xs ${m.cc}`}>{m.conf}</p>
                <button className="col-span-3 text-left text-xs text-muted-foreground underline hover:text-foreground">
                  수정
                </button>
              </div>
            ))}
          </div>
          <div className="flex items-start gap-2 rounded border border-border bg-muted/20 px-4 py-3">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <p className="text-xs text-muted-foreground">
              금액 단위는 원으로 통일되었습니다. 취소 거래는 매출에서 제외됩니다. 신뢰도
              &apos;보통&apos; 이하 항목은 직접 확인을 권장합니다.
            </p>
          </div>
          <div className="flex justify-between">
            <button
              onClick={() => setSection('upload')}
              className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <ChevronLeft className="h-4 w-4" />
              데이터 업로드
            </button>
            <button
              onClick={onNext}
              disabled={!canNext}
              className="flex items-center gap-2 rounded bg-foreground px-5 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-30"
            >
              사업 상태 분석하기 <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {section !== 'mapping' && (
        <div className="flex justify-end pt-2">
          <button
            onClick={onNext}
            disabled={!canNext}
            className="flex items-center gap-2 rounded bg-foreground px-5 py-2.5 text-sm font-medium text-background transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-30"
          >
            분석 시작 <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
};
