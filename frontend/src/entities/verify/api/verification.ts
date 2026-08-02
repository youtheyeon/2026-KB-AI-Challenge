import { apiClient } from '@/shared/api';
import type { VerificationTargetsResponse } from '@/shared/api/schema';

export const getVerificationTargets = (businessId: number, includeCompleted = false) =>
  apiClient
    .get<VerificationTargetsResponse>(`/api/businesses/${businessId}/verification-targets`, {
      params: { includeCompleted },
    })
    .then((res) => res.data);
