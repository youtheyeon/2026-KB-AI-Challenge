import { apiClient } from '@/shared/api';
import type {
  ScenarioSelectionResponse,
  SimulationComparisonResponse,
  SimulationCreatedResponse,
  SimulationCreationRequest,
  SimulationResponse,
} from '@/shared/api/schema';

export const createSimulation = (businessId: number, payload: SimulationCreationRequest) =>
  apiClient
    .post<SimulationCreatedResponse>(`/api/businesses/${businessId}/simulations`, payload)
    .then((res) => res.data);

export const getSimulation = (simulationId: number) =>
  apiClient.get<SimulationResponse>(`/api/simulations/${simulationId}`).then((res) => res.data);

export const getSimulationComparison = (simulationId: number) =>
  apiClient
    .get<SimulationComparisonResponse>(`/api/simulations/${simulationId}/comparison`)
    .then((res) => res.data);

export const selectScenario = (simulationId: number, scenarioId: number) =>
  apiClient
    .post<ScenarioSelectionResponse>(`/api/simulations/${simulationId}/selection`, {
      scenarioId,
    })
    .then((res) => res.data);
