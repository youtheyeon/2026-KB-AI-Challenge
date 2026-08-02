import { apiClient } from '@/shared/api';
import type {
  OutcomeCreatedResponse,
  OutcomeCreationRequest,
  OutcomeDataCreatedResponse,
  OutcomeResultResponse,
} from '@/shared/api/schema';

export interface ManualOutcomeMetricsRequest {
  monthlySalesAmount: number;
  operatingProfitAmount: number;
  onlineOrderRatio: number;
  cashAfterRepaymentAmount: number;
}

export type OutcomeDataRequest =
  | { sourceType: 'MOCK' }
  | { sourceType: 'MANUAL_INPUT'; metrics: ManualOutcomeMetricsRequest }
  | { sourceType: 'FILE_UPLOAD'; salesFile: File; costFile: File };

export const createOutcomeData = (simulationId: number, payload: OutcomeDataRequest) => {
  if (payload.sourceType === 'FILE_UPLOAD') {
    const formData = new FormData();
    formData.append('sourceType', payload.sourceType);
    formData.append('salesFile', payload.salesFile);
    formData.append('costFile', payload.costFile);
    return apiClient
      .post<OutcomeDataCreatedResponse>(`/api/simulations/${simulationId}/outcome-data`, formData)
      .then((res) => res.data);
  }
  return apiClient
    .post<OutcomeDataCreatedResponse>(`/api/simulations/${simulationId}/outcome-data`, payload)
    .then((res) => res.data);
};

export const createOutcome = (simulationId: number, payload: OutcomeCreationRequest) =>
  apiClient
    .post<OutcomeCreatedResponse>(`/api/simulations/${simulationId}/outcomes`, payload)
    .then((res) => res.data);

export const getOutcome = (simulationId: number) =>
  apiClient
    .get<OutcomeResultResponse>(`/api/simulations/${simulationId}/outcomes`)
    .then((res) => res.data);
