import { apiClient } from '@/shared/api';
import type { ExecutionCreatedResponse, ExecutionCreationRequest } from '@/shared/api/schema';

export const createExecution = (simulationId: number, payload: ExecutionCreationRequest) =>
  apiClient
    .post<ExecutionCreatedResponse>(`/api/simulations/${simulationId}/executions`, payload)
    .then((res) => res.data);
