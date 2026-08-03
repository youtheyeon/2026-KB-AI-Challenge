import { apiClient } from '@/shared/api';
import type { DashboardResponse } from '@/shared/api/schema';

export const getDashboard = (businessId: number) =>
  apiClient
    .get<DashboardResponse>(`/api/businesses/${businessId}/dashboard`)
    .then((res) => res.data);
