import { apiClient } from '@/shared/api';
import type {
  BodyUploadDatasetApiBusinessesBusinessIdDatasetsPost as DatasetUploadFiles,
  DatasetStatusResponse,
  DatasetUploadResponse,
} from '@/shared/api/schema';

export type { DatasetUploadFiles };

export const uploadDataset = (businessId: number, files: DatasetUploadFiles) => {
  const formData = new FormData();
  formData.append('salesFile', files.salesFile);
  formData.append('expenseFile', files.expenseFile);
  if (files.onlineSalesFile) {
    formData.append('onlineSalesFile', files.onlineSalesFile);
  }

  return apiClient
    .post<DatasetUploadResponse>(`/api/businesses/${businessId}/datasets`, formData)
    .then((res) => res.data);
};

export const getDatasetStatus = (datasetId: number) =>
  apiClient.get<DatasetStatusResponse>(`/api/datasets/${datasetId}`).then((res) => res.data);
