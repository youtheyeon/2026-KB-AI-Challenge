import { apiClient } from '@/shared/api';
import type {
  BusinessRegistrationRequest,
  BusinessRegistrationResponse,
} from '@/shared/api/schema';

export const registerBusiness = (payload: BusinessRegistrationRequest) =>
  apiClient.post<BusinessRegistrationResponse>('/api/businesses', payload).then((res) => res.data);
