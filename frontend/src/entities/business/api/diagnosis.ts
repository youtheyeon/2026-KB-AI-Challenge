import { apiClient } from '@/shared/api';
import type { DiagnosisResultResponse, DiagnosisStartResponse } from '@/shared/api/schema';

export const startDiagnosis = (businessId: number, datasetId: number) =>
  apiClient
    .post<DiagnosisStartResponse>(`/api/businesses/${businessId}/diagnoses`, { datasetId })
    .then((res) => res.data);

export const getDiagnosis = (diagnosisId: number) =>
  apiClient.get<DiagnosisResultResponse>(`/api/diagnoses/${diagnosisId}`).then((res) => res.data);
