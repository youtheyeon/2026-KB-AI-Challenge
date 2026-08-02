import { useState } from 'react';

import { getDatasetStatus, registerBusiness, uploadDataset } from '@/entities/business';
import { SAMPLE, UPLOAD_SLOTS, type SlotState } from '@/entities/simulation';
import { getApiErrorMessage } from '@/shared/api';
import { DatasetFileType, DatasetStatus, type DatasetStatusResponse } from '@/shared/api/schema';

export type Section = 'info' | 'upload';

const SLOT_FILE_TYPE: Record<string, DatasetFileType> = {
  sales: DatasetFileType.Sale,
  expense: DatasetFileType.Expense,
  onlineSales: DatasetFileType.OnlineSale,
};

export interface DataConnectFormState {
  name: string;
  setName: (value: string) => void;
  region: string;
  setRegion: (value: string) => void;
  bizType: string;
  setBizType: (value: string) => void;
  employees: string;
  setEmployees: (value: string) => void;
  channels: string[];
  toggleChannel: (channel: string) => void;
}

export interface DataConnectRegistrationState {
  registering: boolean;
  registerError: string | null;
  handleGoToUpload: () => void;
}

export interface DataConnectUploadState {
  slots: Record<string, SlotState>;
  files: Record<string, File | undefined>;
  fileErrors: Record<string, string>;
  slotIssues: Record<string, string>;
  datasetResult: DatasetStatusResponse | null;
  uploading: boolean;
  uploadError: string | null;
  handleFileChange: (slotId: string, file: File | undefined) => void;
  handleUploadAndAnalyze: () => void;
}

interface UseDataConnectStepParams {
  isSample: boolean;
  businessId: number | null;
  onNext: () => void;
  onBusinessRegistered: (businessId: number) => void;
  onDatasetUploaded: (datasetId: number) => void;
}

export const useDataConnectStep = ({
  isSample,
  businessId,
  onNext,
  onBusinessRegistered,
  onDatasetUploaded,
}: UseDataConnectStepParams) => {
  const [name, setName] = useState(isSample ? SAMPLE.name : '');
  const [bizType, setBizType] = useState(isSample ? SAMPLE.bizType : '');
  const [region, setRegion] = useState(isSample ? SAMPLE.region : '');
  const [employees, setEmployees] = useState(isSample ? '2' : '');
  const [channels, setChannels] = useState<string[]>(isSample ? SAMPLE.channels : []);
  const [slots, setSlots] = useState<Record<string, SlotState>>(
    Object.fromEntries(UPLOAD_SLOTS.map((s) => [s.id, isSample ? 'done' : 'idle'])),
  );
  const [files, setFiles] = useState<Record<string, File | undefined>>({});
  const [fileErrors, setFileErrors] = useState<Record<string, string>>({});
  const [slotIssues, setSlotIssues] = useState<Record<string, string>>({});
  const [section, setSection] = useState<Section>('info');
  const [useSample, setUseSample] = useState(isSample);

  const [registering, setRegistering] = useState(false);
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [datasetResult, setDatasetResult] = useState<DatasetStatusResponse | null>(null);

  const applySample = () => {
    setUseSample(true);
    setName(SAMPLE.name);
    setBizType(SAMPLE.bizType);
    setRegion(SAMPLE.region);
    setEmployees('2');
    setChannels(SAMPLE.channels);
    setSlots(Object.fromEntries(UPLOAD_SLOTS.map((s) => [s.id, 'done'])));
    setSection('upload');
  };

  const doneCount = Object.values(slots).filter((v) => v === 'done').length;
  const reqDone = useSample
    ? ['sales', 'expense'].every((id) => slots[id] === 'done')
    : Boolean(files.sales && files.expense && datasetResult?.status === DatasetStatus.Ready);
  const canNext = Boolean(name && bizType && region && reqDone);

  const toggleChannel = (c: string) =>
    setChannels((p) => (p.includes(c) ? p.filter((x) => x !== c) : [...p, c]));

  const handleGoToUpload = async () => {
    if (useSample || businessId) {
      setSection('upload');
      return;
    }
    setRegistering(true);
    setRegisterError(null);
    try {
      const business = await registerBusiness({
        name,
        region,
        industry: bizType,
        employeeCount: employees ? Number(employees) : 0,
        primarySalesChannels: channels,
      });
      onBusinessRegistered(business.businessId);
      setSection('upload');
    } catch (error) {
      setRegisterError(getApiErrorMessage(error));
    } finally {
      setRegistering(false);
    }
  };

  const handleFileChange = (slotId: string, file: File | undefined) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.xlsx')) {
      setFileErrors((p) => ({ ...p, [slotId]: '.xlsx 파일만 업로드할 수 있습니다.' }));
      return;
    }
    setFileErrors((p) => {
      const next = { ...p };
      delete next[slotId];
      return next;
    });
    setFiles((p) => ({ ...p, [slotId]: file }));
    setSlots((p) => ({ ...p, [slotId]: 'idle' }));
    setSlotIssues((p) => {
      const next = { ...p };
      delete next[slotId];
      return next;
    });
    setDatasetResult(null);
  };

  const handleUploadAndAnalyze = async () => {
    if (useSample) {
      onNext();
      return;
    }
    if (!businessId || !files.sales || !files.expense) return;

    setUploading(true);
    setUploadError(null);
    const attemptedSlotIds = UPLOAD_SLOTS.filter((s) => files[s.id]).map((s) => s.id);
    setSlots((p) => {
      const next = { ...p };
      attemptedSlotIds.forEach((id) => (next[id] = 'parsing'));
      return next;
    });

    try {
      const { datasetId } = await uploadDataset(businessId, {
        salesFile: files.sales,
        expenseFile: files.expense,
        onlineSalesFile: files.onlineSales,
      });
      const result = await getDatasetStatus(datasetId);
      setDatasetResult(result);

      if (result.status === DatasetStatus.Ready) {
        setSlots((p) => {
          const next = { ...p };
          attemptedSlotIds.forEach((id) => (next[id] = 'done'));
          return next;
        });
        setSlotIssues({});
        onDatasetUploaded(datasetId);
        onNext();
        return;
      }

      if (result.status === DatasetStatus.NeedsReupload) {
        const nextSlots: Record<string, SlotState> = { ...slots };
        const nextIssues: Record<string, string> = {};
        for (const slotId of attemptedSlotIds) {
          const fileType = SLOT_FILE_TYPE[slotId];
          const fileStatus = result.files.find((f) => f.fileType === fileType);
          if (fileStatus && fileStatus.missingColumns.length > 0) {
            nextSlots[slotId] = 'error';
            nextIssues[slotId] = `누락된 항목: ${fileStatus.missingColumns.join(', ')}`;
          } else {
            nextSlots[slotId] = 'done';
          }
        }
        setSlots(nextSlots);
        setSlotIssues(nextIssues);
        setUploadError(
          '일부 파일에 필수 항목이 누락되어 있습니다. 해당 파일을 다시 업로드해주세요.',
        );
        return;
      }

      setSlots((p) => {
        const next = { ...p };
        attemptedSlotIds.forEach((id) => (next[id] = 'error'));
        return next;
      });
      setUploadError('파일을 분석하지 못했습니다. 파일 형식을 확인한 뒤 다시 업로드해주세요.');
    } catch (error) {
      setSlots((p) => {
        const next = { ...p };
        attemptedSlotIds.forEach((id) => (next[id] = 'error'));
        return next;
      });
      setUploadError(getApiErrorMessage(error));
    } finally {
      setUploading(false);
    }
  };

  return {
    section,
    setSection,
    useSample,
    applySample,
    doneCount,
    canNext,
    form: {
      name,
      setName,
      region,
      setRegion,
      bizType,
      setBizType,
      employees,
      setEmployees,
      channels,
      toggleChannel,
    },
    registration: {
      registering,
      registerError,
      handleGoToUpload,
    },
    upload: {
      slots,
      files,
      fileErrors,
      slotIssues,
      datasetResult,
      uploading,
      uploadError,
      handleFileChange,
      handleUploadAndAnalyze,
    },
  };
};
